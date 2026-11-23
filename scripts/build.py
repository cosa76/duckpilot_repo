"""Construit les couches staging et marts à partir des tables raw_*.

Exécute dans l'ordre les fichiers sql/staging/*.sql puis sql/marts/*.sql,
trace chaque exécution dans la table journal_transformations,
puis exporte les tables staging_* en Parquet dans data/staging/.

Les tables raw_* ne sont jamais modifiées.

Usage : python scripts/build.py
"""

from __future__ import annotations

import time
from datetime import datetime

import duckdb

from common import DB, ROOT, run_id

SQL = ROOT / "sql"
STAGING_DIR = ROOT / "data" / "staging"
LAYERS = ["staging", "marts"]


def run(con, sql: str):
    return con.execute(sql).fetchall()


def main() -> None:
    rid = run_id()
    with duckdb.connect(str(DB)) as con:
        run(con, """CREATE TABLE IF NOT EXISTS journal_transformations (
            execute_le TIMESTAMP, couche VARCHAR, fichier VARCHAR,
            statut VARCHAR, duree_s DOUBLE, erreur VARCHAR)""")
        run(con, "ALTER TABLE journal_transformations ADD COLUMN IF NOT EXISTS run_id VARCHAR")
        for layer in LAYERS:
            for f in sorted((SQL / layer).glob("*.sql")):
                debut, t0 = datetime.now(), time.perf_counter()
                try:
                    run(con, f.read_text(encoding="utf-8"))
                    statut, erreur = "ok", None
                except duckdb.Error as e:
                    statut, erreur = "erreur", str(e)
                duree = round(time.perf_counter() - t0, 3)
                con.execute("""INSERT INTO journal_transformations
                    (execute_le, couche, fichier, statut, duree_s, erreur, run_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    [debut, layer, f.name, statut, duree, erreur, rid]).fetchall()
                print(f"{statut:<6} {layer}/{f.name} ({duree} s)")
                if erreur:
                    raise SystemExit(f"Arrêt : {f.name}\n{erreur}")

        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        tables = [r[0] for r in run(con, """SELECT table_name FROM information_schema.tables
            WHERE table_name LIKE 'staging_%' ORDER BY 1""")]
        print()
        for t in tables:
            dest = (STAGING_DIR / f"{t}.parquet").as_posix()
            run(con, f"COPY {t} TO '{dest}' (FORMAT parquet)")
            n = run(con, f"SELECT count(*) FROM {t}")[0][0]
            print(f"{t:<20} {n:>7} lignes -> data/staging/{t}.parquet")
        for src, motif, n in run(con, """SELECT table_source, motif, count(*) FROM rejets
                GROUP BY ALL ORDER BY 1, 2"""):
            print(f"rejet  {src:<16} {motif:<32} {n:>5}")


if __name__ == "__main__":
    main()
