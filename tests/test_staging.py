"""Vérifie les règles de la couche staging."""

from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "analytics.duckdb"


@pytest.fixture(scope="module")
def con():
    if not DB.exists():
        pytest.skip("lancer scripts/run_pipeline.py d'abord")
    c = duckdb.connect(str(DB), read_only=True)
    tables = {r[0] for r in c.execute("SHOW TABLES").fetchall()}
    if "staging_ventes" not in tables:
        c.close()
        pytest.skip("lancer scripts/build.py d'abord")
    yield c
    c.close()


def one(con, sql: str):
    return con.execute(sql).fetchall()[0][0]


def test_conservation_ventes(con):
    """Chaque vente brute dédoublonnée est soit en staging, soit en rejets."""
    brut = one(con, """SELECT count(*) FROM (SELECT DISTINCT vente_id, date_vente, client_id,
        produit_id, quantite, prix_unitaire, remise_pct, montant_ttc, canal, devise
        FROM raw_ventes)""")
    gardes = one(con, "SELECT count(*) FROM staging_ventes")
    rejetes = one(con, "SELECT count(*) FROM rejets WHERE table_source = 'raw_ventes'")
    assert brut == gardes + rejetes


def test_conservation_evenements(con):
    brut = one(con, "SELECT count(*) FROM (SELECT DISTINCT * EXCLUDE (_loaded_at) FROM raw_evenements)")
    gardes = one(con, "SELECT count(*) FROM staging_evenements")
    rejetes = one(con, "SELECT count(*) FROM rejets WHERE table_source = 'raw_evenements'")
    assert brut == gardes + rejetes


@pytest.mark.parametrize("table,cle", [
    ("staging_ventes", "vente_id"),
    ("staging_clients", "client_id"),
    ("staging_produits", "produit_id"),
    ("staging_evenements", "event_id"),
    ("staging_tickets", "ticket_id"),
])
def test_cles_uniques(con, table, cle):
    assert one(con, f"SELECT count(*) - count(DISTINCT {cle}) FROM {table}") == 0


def test_ventes_valides(con):
    assert one(con, "SELECT count(*) FROM staging_ventes WHERE date_vente IS NULL") == 0
    assert one(con, "SELECT count(*) FROM staging_ventes WHERE montant_ttc < 0") == 0
    assert one(con, "SELECT count(*) FROM staging_ventes WHERE quantite NOT BETWEEN 1 AND 100") == 0
    assert one(con, "SELECT count(*) FROM staging_ventes WHERE devise <> 'EUR'") == 0
    assert one(con, """SELECT count(*) FROM staging_ventes
        WHERE canal NOT IN ('web', 'magasin', 'telephone', 'partenaire')""") == 0


def test_integrite_referentielle_ventes(con):
    assert one(con, """SELECT count(*) FROM staging_ventes v
        ANTI JOIN staging_clients c USING (client_id)""") == 0
    assert one(con, """SELECT count(*) FROM staging_ventes v
        ANTI JOIN staging_produits p USING (produit_id)""") == 0


def test_pas_de_pii_en_staging(con):
    cols = {r[0] for r in con.execute("DESCRIBE staging_clients").fetchall()}
    assert not cols & {"prenom", "nom", "email", "telephone"}
    assert one(con, """SELECT count(*) FROM staging_tickets
        WHERE regexp_matches(description, '[^@\\s]+@[^@\\s]+\\.[a-z]+|0\\d([ .]?\\d{2}){4}')""") == 0


def test_tickets_coherents(con):
    assert one(con, "SELECT count(*) FROM staging_tickets WHERE delai_resolution_h < 0") == 0
    assert one(con, "SELECT count(*) FROM staging_tickets WHERE satisfaction NOT BETWEEN 1 AND 5") == 0


def test_evenements_normalises(con):
    assert one(con, "SELECT count(*) FROM staging_evenements WHERE event_name <> lower(event_name)") == 0
    assert one(con, "SELECT count(*) FROM staging_evenements WHERE event_ts > now()") == 0
