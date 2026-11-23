"""Fonctions partagées par les scripts du pipeline."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "analytics.duckdb"
RAW = ROOT / "data" / "raw"
CONFIG = ROOT / "config"
REPORTS = ROOT / "reports"


def run_id() -> str:
    """Identifiant d'exécution partagé par toutes les étapes d'un même lancement.

    run_pipeline.py le fixe dans la variable DUCKPILOT_RUN_ID.
    Un script lancé seul crée le sien.
    """
    rid = os.environ.get("DUCKPILOT_RUN_ID")
    if not rid:
        rid = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.environ["DUCKPILOT_RUN_ID"] = rid
    return rid


def q(con, sql: str, params: list | None = None) -> list[tuple]:
    """Exécute et lit tout le résultat (obligatoire avec duckdb 2.0 avant la requête suivante)."""
    return con.execute(sql, params or []).fetchall()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def cle_utilisateur_windows() -> str | None:
    """Valeur de ANTHROPIC_API_KEY enregistrée par setx (variable utilisateur Windows)."""
    if os.name != "nt":
        return None
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, "ANTHROPIC_API_KEY")[0] or None
    except OSError:
        return None


def api_key() -> str | None:
    """Clé API Claude : variable d'environnement du terminal, sinon variable
    utilisateur Windows (cas d'un terminal ouvert avant le setx). Jamais affichée."""
    return os.environ.get("ANTHROPIC_API_KEY") or cle_utilisateur_windows()


def diagnostic_cle() -> str:
    """Explique d'où vient la clé utilisée, sans jamais l'afficher."""
    terminal, windows = os.environ.get("ANTHROPIC_API_KEY"), cle_utilisateur_windows()
    if terminal and windows and terminal != windows:
        return ("la clé de ce terminal est différente de celle enregistrée dans Windows (setx). "
                "Ouvre un nouveau terminal, ou lance : "
                "$env:ANTHROPIC_API_KEY = [Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY','User')")
    if terminal:
        return "la clé vient de la variable ANTHROPIC_API_KEY de ce terminal : vérifie-la dans la console Anthropic"
    return "la clé vient de la variable utilisateur Windows (setx) : vérifie-la dans la console Anthropic"
