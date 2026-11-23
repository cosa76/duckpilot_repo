# DuckPilot

Socle local d'analyse de données : fichiers sources, DuckDB, scripts Python et Claude.

## Prérequis

- Python 3.12 ou plus (testé avec 3.14)
- Paquets : `pip install -r requirements.txt`
- DuckDB CLI optionnel, pour explorer la base à la main

## Lancer le pipeline

Depuis la racine du projet :

```powershell
python scripts/generate_synthetic_data.py   # crée les fichiers dans data/raw/ (synthétiques)
python scripts/run_pipeline.py              # sauvegarde, import, staging, qualité, profil, rapports
python -m pytest                            # tests (sans appel à l'API)
```

Chaque lancement produit `reports/executions/execution_<run_id>.md` (fichiers traités,
lignes lues, validées, rejetées, erreurs principales, contrôles qualité).
Le pipeline s'arrête si une règle de qualité bloquante échoue.

Détail des étapes, garanties et journaux : `docs/pipeline.md`.

La première étape est à sauter dès que des fichiers réels sont déposés dans `data/raw/`.

## Ce qui existe

| étape | script | sortie |
|---|---|---|
| Données synthétiques | `scripts/generate_synthetic_data.py` | `data/raw/*` |
| Import brut | `scripts/import_raw.py` + `config/sources.toml` | tables `raw_*`, `journal_imports` |
| Profil qualité | `scripts/profile_raw.py` | `reports/profil_qualite_raw.md` |
| Nettoyage | `scripts/build.py` + `sql/staging/` | `staging_*`, `rejets`, `journal_transformations`, `data/staging/*.parquet` |
| Vues métier | `sql/marts/` | `v_ventes_enrichies`, `v_clients_statut`, `v_usage_mensuel` |
| Contrôles qualité | `scripts/quality.py` + `config/regles_qualite.toml` | `controles_qualite` |
| Analyses | `scripts/report.py` + `sql/analyses/` | `reports/rapport_analyse.md` |
| Rapport d'exécution | `scripts/execution_report.py` | `reports/executions/` |

Les anomalies volontaires sont listées dans `docs/anomalies_injectees.md`.
Les règles de nettoyage sont décrites dans `docs/transformations.md`.

## Poser une question en français (assistant SQL)

```powershell
python scripts/ask.py "Quel est le chiffre d'affaires HT par catégorie en 2026 ?"
```

L'assistant envoie à l'API Claude le catalogue des vues et la question, jamais les données.
La requête est validée puis exécutée en local, en lecture seule.
Détails, garde-fous et mesure de qualité : `docs/assistant_sql.md`.

## Rapport produit hebdomadaire

```powershell
python scripts/rapport_produit.py               # dernière semaine complète, avec synthèse Claude
python scripts/rapport_produit.py --sans-ia     # indicateurs seuls, sans appel API
```

Sortie : `reports/hebdo/`. Chaque chiffre cité par Claude est vérifié contre les indicateurs.

## Tableau de bord

`reports/tableau_de_bord.html`, régénéré à chaque `run_pipeline.py`. S'ouvre dans un navigateur, sans serveur.

## Sécurité

- Tout appel à l'API passe par `scripts/claude_client.py` : blocage des données sensibles,
  budget journalier (`config/securite.toml`), journal `logs/api_calls.jsonl`.
- `python scripts/securite.py` : data/raw en lecture seule, scan des secrets. Aussi lancé
  par le hook git pre-commit (`.githooks/`, activé avec `git config core.hooksPath .githooks`).
- Décisions et limites du projet : `docs/decisions.md`.

## Explorer la base

La base est écrite par DuckDB 2.0 (paquet Python). Un CLI DuckDB plus ancien
(1.x) ne peut pas l'ouvrir : mets le CLI à jour, ou passe par Python.

```powershell
duckdb db/analytics.duckdb -readonly
```

```sql
SHOW TABLES;
SUMMARIZE raw_ventes;
```

## Clé API Claude

Elle se configure dans la variable d'environnement `ANTHROPIC_API_KEY`, jamais dans un fichier du dépôt.

## Suite

Feuille de route : `docs/use_cases_ia_taches.txt`, section 12.
