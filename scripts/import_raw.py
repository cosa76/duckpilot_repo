"""Import générique des fichiers de data/raw/ vers les tables raw_* de db/analytics.duckdb.

Les sources sont décrites dans config/sources.toml (aucune source codée en dur).
Pour chaque source :
  1. empreinte SHA-256 du fichier avant lecture ;
  2. lecture dans une table temporaire ;
  3. contrôle du schéma (colonne manquante = échec, colonne en plus = alerte) ;
  4. remplacement de la table raw (l'ancienne reste intacte si une étape échoue) ;
  5. nouvelle empreinte : le fichier source ne doit pas avoir changé pendant l'import ;
  6. trace dans journal_imports, avec comparaison à l'empreinte du dernier import réussi.

Les fichiers sources ne sont jamais modifiés.

Usage : python scripts/import_raw.py
Code retour 1 si une source requise échoue.
"""

from __future__ import annotations

import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from common import CONFIG, DB, RAW, q, run_id, sha256

JOURNAL_DDL = """
CREATE TABLE IF NOT EXISTS journal_imports (
    run_id        VARCHAR,
    table_cible   VARCHAR,
    fichier       VARCHAR,
    format        VARCHAR,
    sha256        VARCHAR,
    taille_octets BIGINT,
    lignes        BIGINT,
    statut        VARCHAR,   -- ok | erreur | absent
    version       VARCHAR,   -- nouveau | inchange | modifie
    alertes       VARCHAR,
    erreur        VARCHAR,
    debut         TIMESTAMP,
    duree_s       DOUBLE
)
"""


def sql_value(v) -> str:
    """Convertit une valeur de configuration en littéral SQL DuckDB."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {sql_value(x)}" for k, x in v.items()) + "}"
    return "'" + str(v).replace("'", "''") + "'"


def reader_sql(fmt: str, path: Path, options: dict) -> str:
    p = path.as_posix().replace("'", "''")
    opts = "".join(f", {k} = {sql_value(v)}" for k, v in options.items())
    if fmt == "csv":
        return f"read_csv('{p}'{opts})"
    if fmt == "json":
        return f"read_json('{p}'{opts})"
    if fmt == "parquet":
        return f"read_parquet('{p}'{opts})"
    raise ValueError(f"format non géré par DuckDB : {fmt}")


def load_temp(con, src: dict, path: Path) -> None:
    con.execute("DROP TABLE IF EXISTS _import").fetchall()
    if src["format"] == "xlsx":
        # Lecture via pandas/openpyxl : évite d'installer l'extension excel de DuckDB.
        df = pd.read_excel(path, dtype=str, **src.get("options", {}))
        con.register("_import_df", df)
        q(con, "CREATE TEMP TABLE _import AS SELECT * FROM _import_df")
        con.unregister("_import_df")
    else:
        q(con, f"CREATE TEMP TABLE _import AS SELECT * FROM "
               f"{reader_sql(src['format'], path, src.get('options', {}))}")


def check_schema(con, attendues: list[str]) -> tuple[list[str], list[str]]:
    presentes = [r[0] for r in q(con, "DESCRIBE _import")]
    manquantes = [c for c in attendues if c not in presentes]
    en_plus = [c for c in presentes if c not in attendues]
    return manquantes, en_plus


def derniere_empreinte(con, table: str) -> str | None:
    r = q(con, """SELECT sha256 FROM journal_imports
                  WHERE table_cible = ? AND statut = 'ok'
                  ORDER BY debut DESC LIMIT 1""", [table])
    return r[0][0] if r else None


def import_source(con, src: dict, rid: str) -> dict:
    table, path = src["table"], RAW / src["fichier"]
    if not table.startswith("raw_"):
        raise ValueError(f"{table} : le nom de table doit commencer par raw_")
    debut, t0 = datetime.now(), time.perf_counter()
    entree = {"run_id": rid, "table_cible": table, "fichier": src["fichier"],
              "format": src["format"], "sha256": None, "taille_octets": None,
              "lignes": None, "statut": "ok", "version": None, "alertes": None,
              "erreur": None, "debut": debut}

    if not path.exists():
        entree["statut"] = "absent"
        entree["erreur"] = f"fichier introuvable : data/raw/{src['fichier']}"
    else:
        try:
            avant = sha256(path)
            entree["sha256"], entree["taille_octets"] = avant, path.stat().st_size
            precedente = derniere_empreinte(con, table)
            entree["version"] = ("nouveau" if precedente is None
                                 else "inchange" if precedente == avant else "modifie")

            load_temp(con, src, path)
            manquantes, en_plus = check_schema(con, src.get("colonnes", []))
            if manquantes:
                raise ValueError(f"colonnes manquantes : {', '.join(manquantes)}")
            if en_plus:
                entree["alertes"] = f"colonnes non attendues : {', '.join(en_plus)}"

            if sha256(path) != avant:
                raise RuntimeError("le fichier source a changé pendant l'import")

            q(con, "BEGIN TRANSACTION")
            q(con, f"""CREATE OR REPLACE TABLE {table} AS
                       SELECT *,
                              {sql_value(src["fichier"])} AS _source_file,
                              {sql_value(rid)} AS _run_id,
                              now() AS _loaded_at
                       FROM _import""")
            q(con, "COMMIT")
            entree["lignes"] = q(con, f"SELECT count(*) FROM {table}")[0][0]
        except Exception as e:  # noqa: BLE001 - toute erreur est tracée
            try:
                q(con, "ROLLBACK")
            except duckdb.Error:
                pass
            entree["statut"], entree["erreur"] = "erreur", str(e).splitlines()[0]
        finally:
            q(con, "DROP TABLE IF EXISTS _import")

    entree["duree_s"] = round(time.perf_counter() - t0, 3)
    cols = list(entree)
    q(con, f"INSERT INTO journal_imports ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
      [entree[c] for c in cols])
    return entree


def main() -> int:
    rid = run_id()
    sources = tomllib.loads((CONFIG / "sources.toml").read_text(encoding="utf-8"))["source"]
    DB.parent.mkdir(parents=True, exist_ok=True)
    echec = False
    with duckdb.connect(str(DB)) as con:
        q(con, JOURNAL_DDL)
        for src in sources:
            e = import_source(con, src, rid)
            info = f"{e['lignes']} lignes, {e['version']}" if e["statut"] == "ok" else e["erreur"]
            print(f"{e['statut']:<7} {e['table_cible']:<16} {info}")
            if e["alertes"]:
                print(f"        alerte : {e['alertes']}")
            if e["statut"] != "ok" and src.get("requis", True):
                echec = True
    return 1 if echec else 0


if __name__ == "__main__":
    sys.exit(main())
