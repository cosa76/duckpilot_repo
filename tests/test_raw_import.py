"""Vérifie que l'import raw reflète fidèlement les fichiers sources."""

from pathlib import Path

import duckdb
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB = ROOT / "db" / "analytics.duckdb"

pytestmark = pytest.mark.skipif(not DB.exists(), reason="lancer scripts/import_raw.py d'abord")


def count_lines(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f)


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(DB), read_only=True)
    yield c
    c.close()


def n_rows(con, table: str) -> int:
    return con.execute(f"SELECT count(*) FROM {table}").fetchall()[0][0]


def test_tables_raw_presentes(con):
    tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    assert {"raw_ventes", "raw_produits", "raw_clients", "raw_evenements", "raw_tickets"} <= tables


def test_aucune_ligne_perdue(con):
    assert n_rows(con, "raw_evenements") == count_lines(RAW / "evenements.jsonl")
    assert n_rows(con, "raw_clients") == len(pd.read_excel(RAW / "clients.xlsx"))
    assert n_rows(con, "raw_tickets") == len(pd.read_parquet(RAW / "tickets.parquet"))
    assert n_rows(con, "raw_ventes") == len(pd.read_csv(RAW / "ventes.csv", dtype=str))
    assert n_rows(con, "raw_produits") == len(pd.read_csv(RAW / "produits.csv", sep=";", dtype=str))


def test_colonnes_techniques(con):
    for t in ["raw_ventes", "raw_produits", "raw_clients", "raw_evenements", "raw_tickets"]:
        cols = {r[0] for r in con.execute(f"DESCRIBE {t}").fetchall()}
        assert {"_source_file", "_loaded_at"} <= cols, t


def test_valeurs_brutes_conservees(con):
    # Les dates au format FR ne doivent pas avoir été converties à l'import
    n = con.execute("""SELECT count(*) FROM raw_ventes
        WHERE regexp_matches(date_vente, '^\\d{2}/\\d{2}/\\d{4}$')""").fetchall()[0][0]
    assert n > 0
