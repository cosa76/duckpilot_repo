"""Tests unitaires de l'import générique (scripts/import_raw.py), sur base en mémoire."""

import duckdb
import pytest

import import_raw
from common import q, sha256


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(import_raw, "RAW", tmp_path)
    con = duckdb.connect()
    q(con, import_raw.JOURNAL_DDL)
    yield tmp_path, con
    con.close()


SRC = {"table": "raw_test", "fichier": "test.csv", "format": "csv", "requis": True,
       "colonnes": ["id", "valeur"],
       "options": {"header": True, "delim": ";", "all_varchar": True}}


def test_sql_value():
    assert import_raw.sql_value(True) == "true"
    assert import_raw.sql_value(3) == "3"
    assert import_raw.sql_value("a'b") == "'a''b'"
    assert import_raw.sql_value({"x": "VARCHAR"}) == "{x: 'VARCHAR'}"


def test_import_ok_et_fichier_intact(env):
    raw, con = env
    f = raw / "test.csv"
    f.write_text("id;valeur\n1;10,5\n2;\n", encoding="utf-8")
    avant = sha256(f)
    e = import_raw.import_source(con, SRC, "run1")
    assert e["statut"] == "ok" and e["lignes"] == 2 and e["version"] == "nouveau"
    assert sha256(f) == avant
    # valeur brute conservée en texte, colonnes techniques présentes
    assert q(con, "SELECT valeur, _run_id FROM raw_test WHERE id = '1'") == [("10,5", "run1")]


def test_version_inchange_puis_modifie(env):
    raw, con = env
    f = raw / "test.csv"
    f.write_text("id;valeur\n1;a\n", encoding="utf-8")
    import_raw.import_source(con, SRC, "run1")
    assert import_raw.import_source(con, SRC, "run2")["version"] == "inchange"
    f.write_text("id;valeur\n1;b\n", encoding="utf-8")
    assert import_raw.import_source(con, SRC, "run3")["version"] == "modifie"


def test_colonne_manquante_bloque_et_preserve_la_table(env):
    raw, con = env
    f = raw / "test.csv"
    f.write_text("id;valeur\n1;a\n", encoding="utf-8")
    import_raw.import_source(con, SRC, "run1")
    f.write_text("id;autre\n1;x\n2;y\n", encoding="utf-8")
    e = import_raw.import_source(con, SRC, "run2")
    assert e["statut"] == "erreur" and "valeur" in e["erreur"]
    assert q(con, "SELECT count(*) FROM raw_test") == [(1,)]  # ancienne version intacte


def test_colonne_en_plus_alerte(env):
    raw, con = env
    (raw / "test.csv").write_text("id;valeur;extra\n1;a;z\n", encoding="utf-8")
    e = import_raw.import_source(con, SRC, "run1")
    assert e["statut"] == "ok" and "extra" in e["alertes"]


def test_fichier_absent(env):
    _, con = env
    e = import_raw.import_source(con, SRC, "run1")
    assert e["statut"] == "absent"
    assert q(con, "SELECT statut FROM journal_imports") == [("absent",)]


def test_table_doit_commencer_par_raw(env):
    _, con = env
    with pytest.raises(ValueError):
        import_raw.import_source(con, {**SRC, "table": "ventes"}, "run1")
