"""Relance toute la chaîne avec un identifiant d'exécution commun.

Étapes :
  1. sauvegarde de la base (db/backups/, 5 dernières conservées)
  2. sécurité              scripts/securite.py  (data/raw en lecture seule, scan des secrets)
  3. import raw            scripts/import_raw.py
  4. staging et marts      scripts/build.py
  5. contrôles qualité     scripts/quality.py   (arrêt si règle bloquante en échec)
  6. profil raw            scripts/profile_raw.py
  7. rapport d'analyse     scripts/report.py
  8. tableau de bord       scripts/dashboard.py
Le rapport produit hebdomadaire (appel API) se lance à part : scripts/rapport_produit.py.
Puis, dans tous les cas, rapport d'exécution dans reports/executions/.

Usage : python scripts/run_pipeline.py
Code retour 1 si une étape échoue.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime

from common import DB, ROOT

BACKUPS = DB.parent / "backups"
GARDER = 5
STEPS = ["securite.py", "import_raw.py", "build.py", "quality.py", "profile_raw.py", "report.py",
         "dashboard.py"]


def sauvegarder(rid: str) -> str:
    if not DB.exists():
        return "pas de base existante"
    BACKUPS.mkdir(parents=True, exist_ok=True)
    dest = BACKUPS / f"analytics_{rid}.duckdb"
    shutil.copy2(DB, dest)
    anciennes = sorted(BACKUPS.glob("analytics_*.duckdb"))[:-GARDER]
    for f in anciennes:
        f.unlink()
    return f"{dest.relative_to(ROOT)} ({len(anciennes)} ancienne(s) supprimée(s))"


def main() -> int:
    rid = datetime.now().strftime("%Y%m%d_%H%M%S")
    env = {**os.environ, "DUCKPILOT_RUN_ID": rid, "PYTHONIOENCODING": "utf-8"}
    print(f"Exécution {rid}")
    etapes: list[dict] = []

    t0 = time.perf_counter()
    try:
        detail = sauvegarder(rid)
        etapes.append({"etape": "sauvegarde", "statut": "ok", "detail": detail,
                       "duree_s": round(time.perf_counter() - t0, 2)})
    except OSError as e:
        etapes.append({"etape": "sauvegarde", "statut": "erreur", "detail": str(e),
                       "duree_s": round(time.perf_counter() - t0, 2)})

    if etapes[-1]["statut"] == "ok":
        for step in STEPS:
            print(f"\n=== {step} ===", flush=True)
            t0 = time.perf_counter()
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / step)], cwd=ROOT, env=env)
            etapes.append({"etape": step, "statut": "ok" if r.returncode == 0 else "erreur",
                           "duree_s": round(time.perf_counter() - t0, 2),
                           "detail": "" if r.returncode == 0 else f"code retour {r.returncode}"})
            if r.returncode != 0:
                break

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(etapes, f)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "execution_report.py"), rid,
                    "--etapes", f.name], cwd=ROOT, env=env)
    os.unlink(f.name)

    ok = all(e["statut"] == "ok" for e in etapes)
    print("\nPipeline terminé." if ok else "\nPipeline arrêté sur erreur.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
