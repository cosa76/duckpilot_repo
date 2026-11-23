"""Point de passage unique vers l'API Claude.

Tout appel des cas d'usage (assistant SQL, rapport produit) passe par appeler(), qui :
  1. bloque l'envoi si le contenu contient un motif interdit (email, téléphone, IBAN, clé API)
     ou dépasse la taille maximale (config/securite.toml) ;
  2. bloque l'appel si le budget du jour (appels ou tokens) est atteint ;
  3. appelle le modèle avec sortie JSON contrainte et repli serveur en cas de refus ;
  4. journalise l'appel dans logs/api_calls.jsonl (sans le contenu envoyé ni reçu).

Les prompts sont des fichiers versionnés de prompts/ (en-tête version, usage).
"""

from __future__ import annotations

import json
import re
import time
import tomllib
from dataclasses import dataclass
from datetime import date, datetime
from string import Template

from common import CONFIG, ROOT

MODELE = "claude-opus-5-5"
JOURNAL_API = ROOT / "logs" / "api_calls.jsonl"
PROMPTS = ROOT / "prompts"


class EnvoiBloque(RuntimeError):
    """L'envoi a été bloqué avant de partir (contenu interdit, taille ou budget)."""


@dataclass
class Appel:
    modele: str
    request_id: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int

    @property
    def tokens_entree(self) -> int:
        return self.input_tokens + self.cache_read_tokens + self.cache_write_tokens


def config() -> dict:
    return tomllib.loads((CONFIG / "securite.toml").read_text(encoding="utf-8"))


def charger_prompt(nom: str, **variables) -> tuple[str, str]:
    """Lit prompts/<nom>.md, renvoie (version, texte avec variables substituées)."""
    brut = (PROMPTS / f"{nom}.md").read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", brut, re.S)
    if not m:
        raise ValueError(f"prompts/{nom}.md : en-tête --- manquant")
    entete = dict(ligne.split(":", 1) for ligne in m.group(1).splitlines() if ":" in ligne)
    version = entete.get("version", "").strip()
    if not version:
        raise ValueError(f"prompts/{nom}.md : version manquante")
    return version, Template(m.group(2)).substitute(**variables)


def _textes(systeme: str, messages: list) -> list[str]:
    out = [systeme]
    for msg in messages:
        if isinstance(msg.get("content"), str):
            out.append(msg["content"])
        elif isinstance(msg.get("content"), list):
            out += [b["text"] for b in msg["content"] if isinstance(b, dict) and "text" in b]
    return out


def controler_envoi(systeme: str, messages: list, cfg: dict | None = None) -> None:
    cfg = cfg or config()
    textes = _textes(systeme, messages)
    taille = sum(len(t) for t in textes)
    if taille > cfg["envoi"]["max_caracteres"]:
        raise EnvoiBloque(f"contenu trop long ({taille} caractères, maximum "
                          f"{cfg['envoi']['max_caracteres']})")
    for motif in cfg["envoi"]["motifs_interdits"]:
        if any(re.search(motif["regex"], t) for t in textes):
            raise EnvoiBloque(f"contenu interdit détecté ({motif['nom']}), rien n'a été envoyé")


def consommation_du_jour(journal=None) -> tuple[int, int]:
    journal = journal or JOURNAL_API
    if not journal.exists():
        return 0, 0
    aujourd_hui, appels, tokens = date.today().isoformat(), 0, 0
    for ligne in journal.read_text(encoding="utf-8").splitlines():
        e = json.loads(ligne)
        if e["horodatage"].startswith(aujourd_hui) and e["statut"] != "bloque":
            appels += 1
            tokens += (e.get("tokens_entree") or 0) + (e.get("output_tokens") or 0)
    return appels, tokens


def controler_budget(cfg: dict | None = None) -> None:
    cfg = cfg or config()
    appels, tokens = consommation_du_jour()
    if appels >= cfg["budget"]["max_appels_jour"]:
        raise EnvoiBloque(f"budget du jour atteint ({appels} appels)")
    if tokens >= cfg["budget"]["max_tokens_jour"]:
        raise EnvoiBloque(f"budget du jour atteint ({tokens} tokens)")


def journaliser(entree: dict) -> None:
    JOURNAL_API.parent.mkdir(parents=True, exist_ok=True)
    with open(JOURNAL_API, "a", encoding="utf-8") as f:
        f.write(json.dumps(entree, ensure_ascii=False, default=str) + "\n")


def appeler(client, *, usage: str, prompt_version: str, systeme: str, messages: list,
            schema: dict, effort: str = "medium", max_tokens: int = 16000):
    """Appelle Claude et renvoie (réponse brute, JSON décodé, Appel)."""
    entree = {"horodatage": datetime.now().isoformat(timespec="seconds"), "usage": usage,
              "prompt_version": prompt_version, "modele": MODELE, "effort": effort,
              "statut": "erreur", "erreur": None}
    t0 = time.perf_counter()
    try:
        cfg = config()
        try:
            controler_envoi(systeme, messages, cfg)
            controler_budget(cfg)
        except EnvoiBloque as e:
            entree.update(statut="bloque", erreur=str(e))
            raise
        reponse = client.beta.messages.create(
            model=MODELE,
            max_tokens=max_tokens,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
            system=[{"type": "text", "text": systeme, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        )
        u = reponse.usage
        appel = Appel(reponse.model, reponse._request_id or "", u.input_tokens or 0,
                      u.output_tokens or 0, u.cache_read_input_tokens or 0,
                      u.cache_creation_input_tokens or 0)
        entree.update(modele=appel.modele, request_id=appel.request_id,
                      tokens_entree=appel.tokens_entree, output_tokens=appel.output_tokens,
                      cache_read_tokens=appel.cache_read_tokens, stop_reason=reponse.stop_reason)
        if reponse.stop_reason == "refusal":
            raise RuntimeError("le modèle a refusé la demande")
        if reponse.stop_reason == "max_tokens":
            raise RuntimeError("réponse tronquée (max_tokens atteint)")
        textes = [b.text for b in reponse.content if b.type == "text"]
        if not textes:
            raise RuntimeError("réponse sans texte")
        data = json.loads(textes[-1])
        entree["statut"] = "ok"
        return reponse, data, appel
    except Exception as e:
        if entree["statut"] != "bloque":
            entree["erreur"] = f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}"
        raise
    finally:
        entree["duree_s"] = round(time.perf_counter() - t0, 2)
        journaliser(entree)
