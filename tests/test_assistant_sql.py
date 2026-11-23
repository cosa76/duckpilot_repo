"""Tests de l'assistant SQL, sans appel à l'API (client simulé)."""

import json
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest

import ask
import sql_guard

DB = Path(__file__).resolve().parents[1] / "db" / "analytics.duckdb"
AUTORISEES = {t["nom"] for t in ask.charger_catalogue()["table"]}


def ia_presente() -> bool:
    if not DB.exists():
        return False
    with duckdb.connect(str(DB), read_only=True) as c:
        return bool(c.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = 'ia'").fetchall())


avec_base = pytest.mark.skipif(not ia_presente(), reason="schéma ia absent : lancer scripts/build.py")


@pytest.fixture
def con():
    c = sql_guard.connexion_lecture(str(DB))
    yield c
    c.close()


# ---------- Garde-fous SQL ----------

@avec_base
@pytest.mark.parametrize("sql", [
    "SELECT categorie, sum(montant_ht) FROM ventes GROUP BY 1",
    "WITH x AS (SELECT * FROM ventes) SELECT count(*) FROM x JOIN clients USING (client_id)",
    "SELECT * FROM ia.tickets WHERE priorite = 'critique'",
])
def test_requetes_acceptees(con, sql):
    assert sql_guard.executer(con, sql, AUTORISEES).lignes


@avec_base
@pytest.mark.parametrize("sql", [
    "SELECT * FROM main.raw_clients",
    "SELECT * FROM staging_clients",
    "SELECT * FROM ventes, raw_clients",
    "DELETE FROM ventes",
    "DROP VIEW ventes",
    "SELECT 1; SELECT 2",
    "SELECT * FROM read_csv('data/raw/clients.xlsx')",
    "SELECT * FROM 'data/raw/ventes.csv'",
    "SELECT getenv('ANTHROPIC_API_KEY')",
    "COPY ventes TO 'fuite.csv'",
    "ATTACH 'autre.db'",
    "SELECT 1",
    "",
])
def test_requetes_refusees(con, sql):
    with pytest.raises(sql_guard.RequeteRefusee):
        sql_guard.executer(con, sql, AUTORISEES)


@avec_base
def test_limite_de_lignes(con):
    r = sql_guard.executer(con, "SELECT * FROM evenements", AUTORISEES, max_lignes=10)
    assert len(r.lignes) == 10 and r.tronque


@avec_base
def test_catalogue_conforme_aux_vues(con):
    for t in ask.charger_catalogue()["table"]:
        reelles = [r[0] for r in con.execute(f"DESCRIBE ia.{t['nom']}").fetchall()]
        assert reelles == list(t["colonnes"]), t["nom"]


@avec_base
def test_aucune_colonne_pii_exposee(con):
    cols = {r[0] for r in con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = 'ia'").fetchall()}
    assert not cols & {"prenom", "nom", "email", "telephone", "description", "email_hash"}


# ---------- Contrôle des questions ----------

@pytest.mark.parametrize("q", ["", "x" * 1001, "tickets de jean@exemple.test",
                               "rappeler le 06 12 34 56 78"])
def test_questions_refusees_en_local(q):
    assert ask.verifier_question(q)


def test_question_normale_acceptee():
    assert ask.verifier_question("CA HT par mois en 2026") is None


# ---------- Parcours complet avec client simulé ----------

def reponse(data: dict, stop="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""),
                 SimpleNamespace(type="text", text=json.dumps(data))],
        stop_reason=stop, model="modele-test", _request_id="req_test",
        usage=SimpleNamespace(input_tokens=10, output_tokens=5,
                              cache_read_input_tokens=0, cache_creation_input_tokens=0),
    )


class ClientSimule:
    def __init__(self, *reponses):
        self.reponses, self.appels = list(reponses), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.appels.append(kwargs)
        return self.reponses.pop(0)


@pytest.fixture(autouse=True)
def journal_temporaire(tmp_path, monkeypatch):
    import claude_client
    monkeypatch.setattr(claude_client, "JOURNAL_API", tmp_path / "api_calls.jsonl")
    monkeypatch.setattr(ask, "JOURNAL", tmp_path / "journal.jsonl")
    return tmp_path / "journal.jsonl"


def ok(sql):
    return {"hors_perimetre": False, "sql": sql, "explication": "e", "incertitudes": []}


@avec_base
def test_parcours_ok_et_journal(journal_temporaire):
    client = ClientSimule(reponse(ok("SELECT count(*) AS n FROM ventes")))
    trace, md = ask.repondre("Combien de ventes ?", client=client)
    assert trace.statut == "ok" and trace.nb_lignes == 1
    entree = json.loads(journal_temporaire.read_text(encoding="utf-8").splitlines()[-1])
    assert entree["statut"] == "ok" and entree["request_ids"] == ["req_test"]
    # seuls le catalogue et la question partent vers l'API
    envoye = json.dumps(client.appels[0], default=str)
    assert "Combien de ventes" in envoye and "C00001" not in envoye


@avec_base
def test_correction_apres_requete_refusee():
    client = ClientSimule(reponse(ok("SELECT * FROM raw_clients")),
                          reponse(ok("SELECT count(*) FROM clients")))
    trace, _ = ask.repondre("Combien de clients ?", client=client)
    assert trace.statut == "ok" and trace.tentatives == 2


@avec_base
def test_echec_apres_deux_requetes_refusees():
    client = ClientSimule(reponse(ok("DELETE FROM ventes")), reponse(ok("DROP VIEW ventes")))
    trace, _ = ask.repondre("Vide la table", client=client)
    assert trace.statut == "sql_refusee"


def test_hors_perimetre():
    client = ClientSimule(reponse({"hors_perimetre": True, "sql": "", "explication": "absent",
                                   "incertitudes": ["pas d'abonnements"]}))
    trace, md = ask.repondre("Churn premium ?", client=client)
    assert trace.statut == "hors_perimetre" and "Hors périmètre" in md


def test_refus_du_modele():
    client = ClientSimule(reponse(ok(""), stop="refusal"))
    trace, _ = ask.repondre("Question", client=client)
    assert trace.statut == "reponse_invalide"


def test_pii_jamais_envoyee():
    client = ClientSimule()
    trace, _ = ask.repondre("ventes de paul@exemple.test", client=client)
    assert trace.statut == "refus_local" and client.appels == []
