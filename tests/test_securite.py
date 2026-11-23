"""Tests des contrôles de sécurité et de la vérification des chiffres du rapport produit."""

import json
from datetime import date
from types import SimpleNamespace

import pytest

import claude_client
import rapport_produit
import securite


@pytest.fixture(autouse=True)
def journal_temporaire(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_client, "JOURNAL_API", tmp_path / "api_calls.jsonl")
    return tmp_path / "api_calls.jsonl"


CFG = {
    "budget": {"max_appels_jour": 2, "max_tokens_jour": 1000},
    "envoi": {"max_caracteres": 500, "motifs_interdits": claude_client.config()["envoi"]["motifs_interdits"]},
}


# ---------- Contrôle des envois ----------

@pytest.mark.parametrize("texte", [
    "contact : jean.dupont@exemple.fr",
    "appeler le 06 12 34 56 78",
    "IBAN FR76 3000 6000 0112 3456 7890 189",
    "clé sk-ant-api03-abcdefghijklmnop",
])
def test_envoi_bloque_si_contenu_sensible(texte):
    with pytest.raises(claude_client.EnvoiBloque):
        claude_client.controler_envoi("système", [{"role": "user", "content": texte}], CFG)


def test_envoi_bloque_si_trop_long():
    with pytest.raises(claude_client.EnvoiBloque):
        claude_client.controler_envoi("x" * 600, [], CFG)


def test_envoi_normal_accepte():
    claude_client.controler_envoi("système", [{"role": "user", "content": "CA HT C00012 en 2026"}], CFG)


def test_budget_du_jour(journal_temporaire, monkeypatch):
    monkeypatch.setattr(claude_client, "config", lambda: CFG)
    aujourdhui = date.today().isoformat()
    lignes = [{"horodatage": f"{aujourdhui}T10:00:00", "statut": "ok", "tokens_entree": 100,
               "output_tokens": 10}] * 2
    journal_temporaire.write_text("".join(json.dumps(l) + "\n" for l in lignes), encoding="utf-8")
    with pytest.raises(claude_client.EnvoiBloque):
        claude_client.controler_budget()


def test_appel_bloque_est_journalise_sans_contenu(journal_temporaire):
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(
        create=lambda **k: pytest.fail("l'API ne doit pas être appelée"))))
    with pytest.raises(claude_client.EnvoiBloque):
        claude_client.appeler(client, usage="test", prompt_version="1", systeme="s",
                              messages=[{"role": "user", "content": "mail a@b.fr"}], schema={})
    entree = json.loads(journal_temporaire.read_text(encoding="utf-8"))
    assert entree["statut"] == "bloque" and "a@b.fr" not in json.dumps(entree)


def test_prompts_versionnes():
    for nom in ["assistant_sql", "rapport_produit"]:
        brut = (claude_client.PROMPTS / f"{nom}.md").read_text(encoding="utf-8")
        assert brut.startswith("---\nversion:")


# ---------- Scan des secrets ----------

def test_scan_detecte_secrets_et_donnees(tmp_path, monkeypatch):
    monkeypatch.setattr(securite, "ROOT", tmp_path)
    (tmp_path / "config.py").write_text('API_KEY = "abcdefghijklmnopqrstuvwxyz"\n', encoding="utf-8")
    (tmp_path / "cle.txt").write_text("sk-ant-api03-" + "x" * 30, encoding="utf-8")
    (tmp_path / "export.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "propre.py").write_text("x = 1\n", encoding="utf-8")
    problemes = securite.scanner(sorted(tmp_path.iterdir()))
    assert len(problemes) == 3 and not any("propre.py" in p for p in problemes)


def test_depot_sans_secret():
    assert securite.scanner(securite.fichiers_candidats(staged=False)) == []


# ---------- Vérification des chiffres du rapport produit ----------

IND = {"activite": {"utilisateurs_actifs": {"semaine": 172, "variation_vs_precedente_pct": 11.7}},
       "ventes": {"ca_ht": {"semaine": 111332.12}},
       "erreurs_par_version": [{"version": "4.0.0", "taux_erreur_pct": 5.07}]}


def reponse(texte, sources=("activite",), n=3):
    h = {"hypothese": "h", "indicateur_appui": "i", "donnees_a_verifier": "d",
         "action_a_tester": "a", "sources": list(sources)}
    return {"synthese": texte, "constats": [], "hypotheses": [h] * n, "alertes": []}


def test_chiffres_exacts_acceptes():
    texte = "172 actifs (+11,7 %), CA 111 332,12 €, soit 111 k€, version 4.0.0 à 5.07 %, le 2026-10-19."
    assert rapport_produit.verifier_reponse(reponse(texte), IND) == []


def test_chiffre_invente_signale():
    problemes = rapport_produit.verifier_reponse(reponse("Le taux de conversion atteint 23,4 %."), IND)
    assert problemes == ["chiffre introuvable dans les indicateurs : 23,4"]


def test_source_inconnue_et_nombre_hypotheses():
    problemes = rapport_produit.verifier_reponse(reponse("RAS", sources=["inconnu"], n=2), IND)
    assert "source inconnue : inconnu" in problemes
    assert "2 hypothèses au lieu de 3" in problemes
