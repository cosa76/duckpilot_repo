"""Contrôles de sécurité locaux, sans appel réseau.

  verrouiller_raw()   passe les fichiers de data/raw/ en lecture seule ;
  scanner_secrets()   cherche des secrets et des données sensibles dans les fichiers
                      que git pourrait versionner (non ignorés par .gitignore).

Usage :
  python scripts/securite.py              les deux contrôles, code retour 1 si un problème
  python scripts/securite.py --staged     scan des seuls fichiers indexés (hook pre-commit)
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
from pathlib import Path

from common import RAW, ROOT

MOTIFS = {
    "cle_api_anthropic": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    "cle_privee": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "affectation_secret": re.compile(
        r"(?i)\b(api[_-]?key|secret|password|mot_de_passe|token)\b\s*[:=]\s*['\"][^'\"\s]{12,}['\"]"),
}
EXTENSIONS_DONNEES = {".csv", ".xlsx", ".xls", ".parquet", ".jsonl", ".duckdb", ".db"}
EXCLUS = {"tests/test_securite.py"}  # contient des faux secrets pour les tests


def verrouiller_raw() -> int:
    n = 0
    for f in RAW.iterdir():
        if f.is_file() and f.name != ".gitkeep":
            os.chmod(f, stat.S_IREAD)
            n += 1
    return n


def fichiers_candidats(staged: bool) -> list[Path]:
    if staged:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
    else:
        cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
    return [ROOT / l for l in r.stdout.splitlines() if l.strip()]


def scanner(fichiers: list[Path]) -> list[str]:
    problemes = []
    for f in fichiers:
        rel = f.relative_to(ROOT).as_posix()
        if rel in EXCLUS or not f.is_file():
            continue
        if f.suffix.lower() in EXTENSIONS_DONNEES:
            problemes.append(f"{rel} : fichier de données, ne doit pas être versionné")
            continue
        try:
            texte = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for nom, motif in MOTIFS.items():
            if motif.search(texte):
                problemes.append(f"{rel} : {nom} détecté")
    return problemes


def main() -> int:
    staged = "--staged" in sys.argv
    if not staged:
        print(f"{verrouiller_raw()} fichier(s) de data/raw/ en lecture seule")
    problemes = scanner(fichiers_candidats(staged))
    for p in problemes:
        print(f"PROBLÈME {p}")
    print("Aucun secret ni fichier de données à versionner." if not problemes
          else f"{len(problemes)} problème(s) : commit à bloquer.")
    return 1 if problemes else 0


if __name__ == "__main__":
    sys.exit(main())
