"""Assistant SQL : une question en français, une requête DuckDB expliquée et exécutée.

Ce qui part vers l'API Claude : le catalogue des vues du schéma ia
(config/catalogue_ia.toml) et la question. Jamais de données.
Ce qui reste en local : l'exécution de la requête et ses résultats.

Garde-fous :
  - question refusée en local si elle contient un email ou un téléphone ;
  - requête validée par scripts/sql_guard.py (SELECT seul, vues ia seules,
    lecture seule, pas d'accès fichier, 200 lignes max, 30 s max) ;
  - une seule tentative de correction si la requête est refusée ou échoue ;
  - chaque appel est journalisé dans logs/assistant_sql.jsonl
    (horodatage, modèle, tokens, statut, erreur, identifiant de requête).

Usage :
  python scripts/ask.py "Quel est le CA HT par catégorie en 2026 ?"
  python scripts/ask.py --dry-run "..."     affiche le prompt sans appeler l'API
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import anthropic

import claude_client
import sql_guard
from common import CONFIG, DB, REPORTS, ROOT, api_key, diagnostic_cle

MODELE = claude_client.MODELE
EFFORT = "medium"
MAX_QUESTION = 1000
JOURNAL = ROOT / "logs" / "assistant_sql.jsonl"
SORTIES = REPORTS / "questions"
PII = re.compile(r"[^@\s]+@[^@\s]+\.[a-z]{2,}|(?:\+33|0)\s?[1-9](?:[ .-]?\d{2}){4}", re.I)

SCHEMA_REPONSE = {
    "type": "object",
    "properties": {
        "hors_perimetre": {
            "type": "boolean",
            "description": "true si le catalogue ne permet pas de répondre à la question",
        },
        "sql": {"type": "string", "description": "Une requête SELECT DuckDB, vide si hors périmètre"},
        "explication": {"type": "string", "description": "Ce que calcule la requête, en français simple"},
        "incertitudes": {
            "type": "array", "items": {"type": "string"},
            "description": "Hypothèses prises et limites de la réponse",
        },
    },
    "required": ["hors_perimetre", "sql", "explication", "incertitudes"],
    "additionalProperties": False,
}


@dataclass
class Trace:
    question: str
    horodatage: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    statut: str = "en_cours"
    modele: str | None = None
    prompt_version: str | None = None
    request_ids: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    tentatives: int = 0
    sql: str | None = None
    tables: list[str] = field(default_factory=list)
    nb_lignes: int | None = None
    erreur: str | None = None
    duree_s: float | None = None


def charger_catalogue() -> dict:
    return tomllib.loads((CONFIG / "catalogue_ia.toml").read_text(encoding="utf-8"))


def prompt_systeme(cat: dict) -> tuple[str, str]:
    """Renvoie (version, prompt système) à partir de prompts/assistant_sql.md."""
    lignes = []
    for t in cat["table"]:
        lignes.append(f"\nVue {t['nom']} : {t['description']}")
        lignes += [f"  - {c} : {d}" for c, d in t["colonnes"].items()]
    return claude_client.charger_prompt(
        "assistant_sql",
        contexte=cat["contexte"].rstrip(),
        catalogue="\n".join(lignes),
        jointures="\n".join(f"  - {j}" for j in cat["jointures"]["autorisees"]),
    )


def verifier_question(question: str) -> str | None:
    if not question.strip():
        return "question vide"
    if len(question) > MAX_QUESTION:
        return f"question trop longue (plus de {MAX_QUESTION} caractères)"
    if PII.search(question):
        return "la question contient un email ou un numéro de téléphone : retire-le avant d'envoyer"
    return None


def appeler(client, systeme: str, messages: list, trace: Trace):
    reponse, data, appel = claude_client.appeler(
        client, usage="assistant_sql", prompt_version=trace.prompt_version or "",
        systeme=systeme, messages=messages, schema=SCHEMA_REPONSE, effort=EFFORT)
    trace.tentatives += 1
    trace.modele = appel.modele
    trace.request_ids.append(appel.request_id)
    trace.input_tokens += appel.input_tokens
    trace.output_tokens += appel.output_tokens
    trace.cache_read_tokens += appel.cache_read_tokens
    trace.cache_write_tokens += appel.cache_write_tokens
    return reponse, data


def journaliser(trace: Trace) -> None:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(json.dumps(trace.__dict__, ensure_ascii=False, default=str) + "\n")


def tableau_md(res: sql_guard.Resultat) -> str:
    def cell(v):
        if v is None:
            return ""
        if isinstance(v, float):
            return f"{v:,.2f}".replace(",", " ").replace(".", ",")
        return str(v).replace("|", "\\|")
    out = ["| " + " | ".join(res.colonnes) + " |", "|" + "---|" * len(res.colonnes)]
    out += ["| " + " | ".join(cell(v) for v in r) + " |" for r in res.lignes]
    return "\n".join(out)


def repondre(question: str, client=None, db_path: str | None = None) -> tuple[Trace, str]:
    """Traite une question et renvoie la trace et la réponse en Markdown."""
    trace, t0 = Trace(question=question), time.perf_counter()
    try:
        probleme = verifier_question(question)
        if probleme:
            trace.statut, trace.erreur = "refus_local", probleme
            return trace, f"Question refusée : {probleme}."

        cat = charger_catalogue()
        autorisees = {t["nom"] for t in cat["table"]}
        trace.prompt_version, systeme = prompt_systeme(cat)
        if client is None:
            cle = api_key()
            if not cle:
                trace.statut, trace.erreur = "erreur_config", "ANTHROPIC_API_KEY absente"
                return trace, "La variable ANTHROPIC_API_KEY n'est pas définie."
            client = anthropic.Anthropic(api_key=cle)

        messages = [{"role": "user", "content": f"<question>{question}</question>"}]
        reponse, data = appeler(client, systeme, messages, trace)

        res, erreur_sql = None, None
        for essai in range(2):
            if data["hors_perimetre"]:
                trace.statut = "hors_perimetre"
                return trace, (f"**Hors périmètre.** {data['explication']}\n\n"
                               + "".join(f"- {i}\n" for i in data["incertitudes"]))
            trace.sql = data["sql"]
            con = sql_guard.connexion_lecture(db_path or str(DB))
            try:
                res = sql_guard.executer(con, data["sql"], autorisees)
                erreur_sql = None
                break
            except (sql_guard.RequeteRefusee, Exception) as e:  # noqa: BLE001
                erreur_sql = str(e).splitlines()[0]
            finally:
                con.close()
            if essai == 0:
                messages += [
                    {"role": "assistant", "content": reponse.content},
                    {"role": "user", "content": f"La requête a échoué : {erreur_sql}. "
                                                "Corrige-la en respectant les règles."},
                ]
                reponse, data = appeler(client, systeme, messages, trace)

        if erreur_sql:
            trace.statut, trace.erreur = "sql_refusee", erreur_sql
            return trace, f"Je n'ai pas obtenu de requête valide : {erreur_sql}\n\n```sql\n{trace.sql}\n```"

        trace.statut, trace.tables, trace.nb_lignes = "ok", res.tables, len(res.lignes)
        md = [f"## {question}", "", "### Requête", "", f"```sql\n{data['sql'].strip()}\n```", "",
              "### Résultat", "", tableau_md(res), ""]
        if res.tronque:
            md += [f"_Résultat tronqué à {len(res.lignes)} lignes._", ""]
        md += ["### Explication", "", data["explication"], ""]
        if data["incertitudes"]:
            md += ["### Limites et hypothèses", ""] + [f"- {i}" for i in data["incertitudes"]] + [""]
        md += [f"_Vues : {', '.join(res.tables)}. Modèle : {trace.modele}. "
               f"Prompt v{trace.prompt_version}. Tokens : {trace.input_tokens + trace.cache_read_tokens + trace.cache_write_tokens} en entrée "
               f"(dont {trace.cache_read_tokens} lus en cache), {trace.output_tokens} en sortie. "
               f"Données synthétiques : à vérifier avant diffusion._"]
        return trace, "\n".join(md)

    except claude_client.EnvoiBloque as e:
        trace.statut, trace.erreur = "envoi_bloque", str(e)
        return trace, f"Envoi bloqué avant l'API : {e}."
    except anthropic.AuthenticationError:
        trace.statut, trace.erreur = "erreur_api", "clé API invalide"
        return trace, f"Clé API refusée par l'API Claude : {diagnostic_cle()}."
    except anthropic.RateLimitError:
        trace.statut, trace.erreur = "erreur_api", "limite de débit atteinte"
        return trace, "Limite de débit atteinte, réessaie dans une minute."
    except anthropic.APIStatusError as e:
        trace.statut, trace.erreur = "erreur_api", f"HTTP {e.status_code}"
        return trace, f"Erreur de l'API Claude (HTTP {e.status_code})."
    except anthropic.APIConnectionError:
        trace.statut, trace.erreur = "erreur_api", "connexion impossible"
        return trace, "Impossible de joindre l'API Claude (réseau)."
    except (RuntimeError, json.JSONDecodeError, KeyError) as e:
        trace.statut, trace.erreur = "reponse_invalide", str(e)
        return trace, f"Réponse inexploitable : {e}"
    finally:
        trace.duree_s = round(time.perf_counter() - t0, 2)
        journaliser(trace)


def main() -> int:
    p = argparse.ArgumentParser(description="Question en français vers SQL DuckDB.")
    p.add_argument("question")
    p.add_argument("--dry-run", action="store_true", help="affiche le prompt sans appeler l'API")
    a = p.parse_args()

    if a.dry_run:
        version, texte = prompt_systeme(charger_catalogue())
        print(f"[prompt assistant_sql v{version}]\n{texte}")
        print(f"<question>{a.question}</question>")
        return 0

    trace, md = repondre(a.question)
    print(md)
    if trace.statut == "ok":
        SORTIES.mkdir(parents=True, exist_ok=True)
        dest = SORTIES / f"{datetime.now():%Y%m%d_%H%M%S}.md"
        dest.write_text(md + "\n", encoding="utf-8")
        print(f"\nRéponse enregistrée : {dest.relative_to(ROOT)}")
    return 0 if trace.statut in ("ok", "hors_perimetre") else 1


if __name__ == "__main__":
    sys.exit(main())
