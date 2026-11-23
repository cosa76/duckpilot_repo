"""Rapport produit hebdomadaire : indicateurs calculés en local, synthèse rédigée par Claude.

1. Les indicateurs sont calculés par les requêtes de sql/produit/ (lecture seule).
2. Seuls ces agrégats (aucun identifiant, aucune donnée personnelle) sont envoyés à Claude,
   via scripts/claude_client.py (contrôles d'envoi, budget, journal).
3. Claude rédige une synthèse, des constats et 3 hypothèses d'amélioration.
4. Chaque chiffre cité par Claude est vérifié contre les indicateurs. Un chiffre introuvable
   est signalé et le rapport est marqué « à relire ».

Sortie : reports/hebdo/rapport_produit_<lundi>.md

Usage :
  python scripts/rapport_produit.py                  dernière semaine complète
  python scripts/rapport_produit.py --semaine 2026-10-12
  python scripts/rapport_produit.py --sans-ia        indicateurs seuls, sans appel API
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta

import anthropic
import duckdb

import claude_client
from common import DB, REPORTS, ROOT, api_key, diagnostic_cle

SQL = ROOT / "sql" / "produit"
SORTIES = REPORTS / "hebdo"
EFFORT = "medium"
NOMBRES_TOLERES = {1, 2, 3, 4, 5, 7, 8, 28, 90, 100}

SCHEMA_REPONSE = {
    "type": "object",
    "properties": {
        "synthese": {"type": "string"},
        "constats": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "texte": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["texte", "sources"],
                "additionalProperties": False,
            },
        },
        "hypotheses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hypothese": {"type": "string"},
                    "indicateur_appui": {"type": "string"},
                    "donnees_a_verifier": {"type": "string"},
                    "action_a_tester": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["hypothese", "indicateur_appui", "donnees_a_verifier",
                             "action_a_tester", "sources"],
                "additionalProperties": False,
            },
        },
        "alertes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["synthese", "constats", "hypotheses", "alertes"],
    "additionalProperties": False,
}


# ---------- Indicateurs locaux ----------

# Définitions envoyées avec les indicateurs : sans elles, le modèle prend des écarts
# normaux (a_risque > actifs_semaine_precedente) pour des incohérences.
DEFINITIONS = {
    "utilisateurs_actifs": "utilisateurs distincts avec au moins un évènement hors logout dans la semaine",
    "moyenne_8_semaines": "moyenne des 8 semaines qui précèdent la semaine analysée",
    "retention.retenus": "actifs la semaine précédente ET la semaine analysée",
    "retention.a_risque": "actifs au moins une fois dans les 4 semaines précédentes, absents la semaine analysée",
    "retention.nouveaux": "utilisateurs dont le tout premier évènement historique tombe dans la semaine",
    "segments.payants": "clients avec au moins un achat dans les 90 jours avant la fin de semaine",
    "segments.payants_sans_usage": "clients payants sans aucun évènement dans la semaine",
    "support.delai_median_h": "délai médian des tickets résolus dans la semaine, en heures",
    "ventes.ca_ht": "chiffre d'affaires hors taxes en euros des ventes valides",
}

def derniere_semaine_complete(con) -> date:
    fin_donnees = con.execute("SELECT max(event_date) FROM staging_evenements").fetchall()[0][0]
    dimanche = fin_donnees - timedelta(days=(fin_donnees.weekday() + 1) % 7)
    return dimanche - timedelta(days=6)


def requete(con, nom: str) -> tuple[list[str], list[tuple]]:
    r = con.execute((SQL / nom).read_text(encoding="utf-8"))
    return [d[0] for d in r.description], r.fetchall()


def variation(a, b):
    if a is None or b in (None, 0):
        return None
    return round(100.0 * (a - b) / b, 1)


def comparatif(cols, lignes) -> dict:
    """Lignes k = 0..8 -> {indicateur: semaine, précédente, moyenne 8 semaines, variations}."""
    par_k = {r[0]: dict(zip(cols, r)) for r in lignes}
    out = {}
    for c in cols[1:]:
        s, p = par_k[0][c], par_k[1][c]
        hist = [par_k[k][c] for k in range(1, 9) if par_k[k][c] is not None]
        moy = round(sum(hist) / len(hist), 1) if hist else None
        out[c] = {"semaine": s, "semaine_precedente": p, "moyenne_8_semaines": moy,
                  "variation_vs_precedente_pct": variation(s, p),
                  "variation_vs_moyenne_pct": variation(s, moy)}
    return out


def lignes_dict(cols, lignes) -> list[dict]:
    return [{c: ("total" if v is None and i == 0 and c in ("segment", "priorite") else v)
             for i, (c, v) in enumerate(zip(cols, r))} for r in lignes]


def indicateurs(debut: date) -> dict:
    with duckdb.connect(str(DB), read_only=True) as con:
        q = lambda s: con.execute(s).fetchall()  # noqa: E731
        q(f"SET VARIABLE debut = DATE '{debut.isoformat()}'")
        ind = {"semaine": {"debut": debut.isoformat(),
                           "fin": (debut + timedelta(days=6)).isoformat()},
               "definitions": DEFINITIONS}
        ind["activite"] = comparatif(*requete(con, "01_activite.sql"))
        ind["ventes"] = comparatif(*requete(con, "07_ventes.sql"))
        ind["fonctionnalites"] = lignes_dict(*requete(con, "02_fonctionnalites.sql"))
        ind["erreurs_par_version"] = lignes_dict(*requete(con, "03_erreurs_version.sql"))
        cols, l = requete(con, "04_retention.sql")
        ind["retention"] = dict(zip(cols, l[0]))
        ind["segments"] = lignes_dict(*requete(con, "05_segments.sql"))
        ind["support"] = lignes_dict(*requete(con, "06_support.sql"))
    return ind


# ---------- Vérification des chiffres cités ----------

def valeurs_numeriques(obj) -> list[float]:
    if isinstance(obj, bool) or obj is None:
        return []
    if isinstance(obj, (int, float)):
        return [float(obj), abs(float(obj))]
    if isinstance(obj, dict):
        return [v for x in obj.values() for v in valeurs_numeriques(x)]
    if isinstance(obj, list):
        return [v for x in obj for v in valeurs_numeriques(x)]
    return []


NOMBRE = re.compile(r"(?<![\w.])\d{1,3}(?:[  ]\d{3})+(?:[.,]\d+)?|(?<![\w.])\d+(?:[.,]\d+)?")
A_IGNORER = re.compile(r"\b\d+\.\d+\.\d+\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b|\b[EJ]\d+\b")


def chiffres_cites(texte: str) -> list[tuple[str, float]]:
    texte = A_IGNORER.sub(" ", texte)
    out = []
    for m in NOMBRE.finditer(texte):
        brut = m.group(0)
        out.append((brut, float(re.sub(r"[  ]", "", brut).replace(",", "."))))
    return out


def verifie(v: float, connues: list[float]) -> bool:
    if v in NOMBRES_TOLERES:
        return True
    for x in connues:
        if abs(v - x) <= max(0.051, 0.005 * abs(x)) or round(x) == v:
            return True
        if x >= 1000 and (abs(v * 1000 - x) <= 0.01 * x or abs(v * 1e6 - x) <= 0.01 * x):
            return True  # chiffre exprimé en k€ ou M€
    return False


def textes_reponse(data: dict) -> list[str]:
    out = [data["synthese"], *data["alertes"]]
    out += [c["texte"] for c in data["constats"]]
    for h in data["hypotheses"]:
        out += [h["hypothese"], h["indicateur_appui"], h["donnees_a_verifier"], h["action_a_tester"]]
    return out


def verifier_reponse(data: dict, ind: dict) -> list[str]:
    """Renvoie la liste des problèmes : chiffres introuvables, sources inconnues, nombre d'hypothèses."""
    connues = valeurs_numeriques(ind)
    problemes = []
    for t in textes_reponse(data):
        for brut, v in chiffres_cites(t):
            if not verifie(v, connues):
                problemes.append(f"chiffre introuvable dans les indicateurs : {brut}")
    blocs = set(ind)
    for item in data["constats"] + data["hypotheses"]:
        for s in item["sources"]:
            if s not in blocs:
                problemes.append(f"source inconnue : {s}")
    if len(data["hypotheses"]) != 3:
        problemes.append(f"{len(data['hypotheses'])} hypothèses au lieu de 3")
    return sorted(set(problemes))


# ---------- Rapport ----------

def fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:,.2f}".replace(",", " ").replace(".", ",").removesuffix(",00")
    if isinstance(v, int):
        return f"{v:,}".replace(",", " ")
    return str(v)


def table(lignes: list[dict]) -> str:
    if not lignes:
        return "_Aucune donnée._"
    cols = list(lignes[0])
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(fmt(l[c]) for c in cols) + " |" for l in lignes]
    return "\n".join(out)


def table_comparatif(bloc: dict) -> str:
    return table([{"indicateur": k, **v} for k, v in bloc.items()])


def rediger(ind: dict, client=None):
    """Appelle Claude et renvoie (données, appel, version du prompt)."""
    version, systeme = claude_client.charger_prompt(
        "rapport_produit",
        contexte="données fictives d'un éditeur de logiciel B2B, simulées avec des comportements "
                 "réalistes (saisonnalité, croissance, churn, sorties de versions). Elles ne décrivent "
                 "aucune entreprise réelle.")
    if client is None:
        client = anthropic.Anthropic(api_key=api_key())
    messages = [{"role": "user", "content": "<indicateurs>\n"
                 + json.dumps(ind, ensure_ascii=False, default=str) + "\n</indicateurs>"}]
    _, data, appel = claude_client.appeler(
        client, usage="rapport_produit", prompt_version=version, systeme=systeme,
        messages=messages, schema=SCHEMA_REPONSE, effort=EFFORT)
    return data, appel, version


def construire(ind: dict, ia: dict | None, problemes: list[str], meta: str) -> str:
    s = ind["semaine"]
    md = [f"# Rapport produit, semaine du {s['debut']} au {s['fin']}", "",
          "_Données synthétiques. Indicateurs calculés en local par `sql/produit/`._", ""]
    if ia:
        statut = ("vérifiée : tous les chiffres cités se retrouvent dans les indicateurs"
                  if not problemes else "**à relire** : voir les points de vérification")
        md += ["## Synthèse (rédigée par Claude, " + statut + ")", "", ia["synthese"], ""]
        if ia["alertes"]:
            md += ["### Alertes", ""] + [f"- {a}" for a in ia["alertes"]] + [""]
        md += ["### Constats", ""]
        md += [f"- {c['texte']} _(sources : {', '.join(c['sources'])})_" for c in ia["constats"]]
        md += ["", "### Hypothèses d'amélioration", ""]
        for i, h in enumerate(ia["hypotheses"], 1):
            md += [f"**{i}. {h['hypothese']}**", "",
                   f"- Indicateur d'appui : {h['indicateur_appui']}",
                   f"- Données à vérifier : {h['donnees_a_verifier']}",
                   f"- Action à tester : {h['action_a_tester']}",
                   f"- Sources : {', '.join(h['sources'])}", ""]
        md += ["### Points de vérification", ""]
        md += [f"- {p}" for p in problemes] if problemes else ["- Aucun problème détecté."]
        md += ["", f"_{meta}_", ""]
    md += ["## Indicateurs", "",
           "### Activité (semaine, précédente, moyenne des 8 précédentes)", "",
           table_comparatif(ind["activite"]), "",
           "### Ventes", "", table_comparatif(ind["ventes"]), "",
           "### Fonctionnalités", "", table(ind["fonctionnalites"]), "",
           "### Erreurs par version", "", table(ind["erreurs_par_version"]), "",
           "### Rétention", "", table([ind["retention"]]), "",
           "### Segments", "", table(ind["segments"]), "",
           "### Support", "", table(ind["support"]), ""]
    return "\n".join(md)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--semaine", help="lundi de la semaine (AAAA-MM-JJ)")
    p.add_argument("--sans-ia", action="store_true")
    a = p.parse_args()

    if a.semaine:
        debut = date.fromisoformat(a.semaine)
        if debut.weekday() != 0:
            raise SystemExit("--semaine doit être un lundi")
    else:
        with duckdb.connect(str(DB), read_only=True) as con:
            debut = derniere_semaine_complete(con)

    ind = indicateurs(debut)
    ia, problemes, meta, code = None, [], "", 0
    if not a.sans_ia:
        try:
            ia, appel, version = rediger(ind)
            problemes = verifier_reponse(ia, ind)
            meta = (f"Modèle {appel.modele}, prompt rapport_produit v{version}, "
                    f"{appel.tokens_entree} tokens en entrée, {appel.output_tokens} en sortie, "
                    f"requête {appel.request_id}.")
        except claude_client.EnvoiBloque as e:
            print(f"Envoi bloqué : {e}. Rapport produit sans synthèse.")
            code = 1
        except anthropic.AuthenticationError:
            print(f"Clé API refusée : {diagnostic_cle()}. Rapport produit sans synthèse.")
            code = 1
        except (anthropic.APIError, RuntimeError, json.JSONDecodeError) as e:
            print(f"Synthèse indisponible ({type(e).__name__}). Rapport produit sans synthèse.")
            code = 1

    SORTIES.mkdir(parents=True, exist_ok=True)
    dest = SORTIES / f"rapport_produit_{debut.isoformat()}.md"
    dest.write_text(construire(ind, ia, problemes, meta), encoding="utf-8")
    print(f"Rapport écrit : {dest.relative_to(ROOT)}")
    if problemes:
        print(f"{len(problemes)} point(s) à relire : " + " ; ".join(problemes))
    return code


if __name__ == "__main__":
    sys.exit(main())
