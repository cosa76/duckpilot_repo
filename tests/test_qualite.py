"""Tests du moteur de contrôles qualité (scripts/quality.py)."""

from pathlib import Path

import duckdb
import pytest

import quality
from report import fr

DB = Path(__file__).resolve().parents[1] / "db" / "analytics.duckdb"


def regle(sql: str, severite: str = "bloquant", seuil=None) -> dict:
    r = {"id": "T_01", "table": "t", "regle": "test", "severite": severite, "sql": sql}
    if seuil is not None:
        r["seuil_pct"] = seuil
    return r


@pytest.fixture
def con():
    c = duckdb.connect()
    yield c
    c.close()


def test_regle_sans_violation(con):
    assert quality.evaluer(con, regle("SELECT 0, 100"))["statut"] == "ok"


def test_regle_en_violation(con):
    r = quality.evaluer(con, regle("SELECT 2, 100"))
    assert r["statut"] == "ko" and r["taux_pct"] == 2.0


def test_seuil_tolere(con):
    assert quality.evaluer(con, regle("SELECT 2, 100", seuil=3))["statut"] == "ok"
    assert quality.evaluer(con, regle("SELECT 4, 100", seuil=3))["statut"] == "ko"


def test_sql_invalide_donne_erreur(con):
    r = quality.evaluer(con, regle("SELECT * FROM table_inexistante"))
    assert r["statut"] == "erreur" and r["erreur"]


def test_fichier_de_regles_valide():
    regles = quality.charger_regles()
    assert len(regles) >= 10
    assert {r["severite"] for r in regles} <= {"bloquant", "alerte"}


@pytest.mark.skipif(not DB.exists(), reason="lancer scripts/run_pipeline.py d'abord")
def test_toutes_les_regles_s_executent_et_les_bloquantes_passent():
    with duckdb.connect(str(DB), read_only=True) as c:
        for r in quality.charger_regles():
            res = quality.evaluer(c, r)
            assert res["statut"] != "erreur", (r["id"], res["erreur"])
            if r["severite"] == "bloquant":
                assert res["statut"] == "ok", r["id"]


def test_format_francais():
    assert fr(1234567.891, 2) == "1 234 567,89"
    assert fr(None) == ""
