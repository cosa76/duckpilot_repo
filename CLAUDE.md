# DuckPilot

Socle local d'analyse de données avec DuckDB, Python et Claude.
Feuille de route : `docs/use_cases_ia_taches.txt` (section 12).
Langue du projet : français.

## Contexte

- Les données restent en local dans `db/analytics.duckdb`.
- Claude Code aide à écrire le code, le SQL et les transformations.
- L'API Claude est réservée au raisonnement, à la synthèse, à la classification,
  à l'extraction et aux rapports. Jamais de données personnelles envoyées à l'API.
- Les données actuelles de `data/raw/` sont fictives mais réalistes (`scripts/generate_realistic_data.py`, voir `docs/donnees_realistes.md` et `docs/anomalies_injectees.md`).

## Arborescence

```
data/raw/       fichiers sources, immuables
data/staging/   exports nettoyés
data/marts/     exports métier
db/             base DuckDB (non versionnée)
sql/staging/    règles de nettoyage raw -> staging (une table par fichier)
sql/marts/      vues métier
sql/analyses/   requêtes d'analyse utilisées par le rapport
config/         sources.toml (sources à importer), regles_qualite.toml (contrôles)
scripts/        scripts Python du pipeline (point d'entrée : run_pipeline.py)
reports/        rapports générés
tests/          tests pytest
docs/           documentation (decisions.md : décisions et limites)
prompts/        prompts versionnés envoyés à l'API Claude
```

## Couches et nommage

- `raw_<entite>` : copie fidèle de la source, colonnes texte pour CSV et JSON,
  plus `_source_file` et `_loaded_at`. Aucune correction.
- `staging_<entite>` : typage, normalisation, dédoublonnage. Une règle par transformation, documentée.
- `mart_<sujet>` ou `v_<sujet>` : vues et tables métier.
- Tables et colonnes en `snake_case`, français, sans accent.
- Identifiants : `<entite>_id`. Dates : `date_<evenement>`. Montants : suffixe de l'unité si ambigu (`_ttc`, `_ht`).
- Fichiers SQL : `sql/<couche>/<numero>_<objet>.sql`, exécutés dans l'ordre par `scripts/build.py`.
- Chaque règle de nettoyage a un code (C1, V2, R3...) en commentaire SQL et dans `docs/transformations.md`.
- Nouvelle source : bloc dans `config/sources.toml`, jamais de chemin codé en dur dans un script.
- Nouvelle règle de qualité : bloc dans `config/regles_qualite.toml` (bloquant ou alerte).
- Avec duckdb 2.0 en Python, lire tout le résultat (`fetchall()`) avant la requête suivante : utiliser `common.q()`.
- Lignes écartées : table `rejets` (table_source, cle, motif, ligne_brute). Jamais de suppression silencieuse.

## Règles SQL

- DuckDB uniquement. Préférer le SQL lisible : CTE nommées, une colonne par ligne.
- Pas de `SELECT *` dans les couches staging et marts.
- Conversion tolérante (`TRY_CAST`, `try_strptime`) puis comptage des rejets. Ne jamais perdre une ligne en silence.
- Toute requête produisant un chiffre diffusé est sauvegardée dans `sql/`.
- Les tables `raw_*` ne sont jamais modifiées par `UPDATE` ou `DELETE`. Seul `scripts/import_raw.py` les recrée.

## Données sensibles

- Colonnes PII : `prenom`, `nom`, `email`, `telephone` (clients), `description` (tickets, texte libre).
- Ne jamais afficher ces colonnes en clair dans un rapport ni les envoyer à l'API Claude.
- Pseudonymiser ou exclure avant toute analyse partagée.
- Tout appel à l'API Claude passe par `scripts/claude_client.py` (contrôles d'envoi, budget, journal).
  Jamais d'appel direct au SDK ailleurs. Les prompts vivent dans `prompts/`, avec une version à incrémenter à chaque changement.
- Rapport produit : seuls les agrégats de `sql/produit/` partent vers l'API, jamais d'identifiant.
- Vers l'API Claude ne partent que le catalogue `config/catalogue_ia.toml` et la question (assistant SQL).
  Toute nouvelle vue exposée à l'assistant va dans le schéma `ia` (`sql/marts/04_schema_ia.sql`), sans PII ni texte libre,
  et doit être décrite dans le catalogue.
- Aucun secret dans le dépôt. La clé API Claude vit dans la variable d'environnement `ANTHROPIC_API_KEY`.

## Commandes

Autorisées sans demander :
- `python scripts/run_pipeline.py` et chacune de ses étapes (`import_raw.py`, `build.py`, `quality.py`, `profile_raw.py`, `report.py`, `execution_report.py`)
- `python scripts/rapport_produit.py --sans-ia`, `python scripts/dashboard.py`, `python scripts/securite.py`
- `python scripts/generate_realistic_data.py` ou `generate_synthetic_data.py` (refusent d'écraser data/raw sans `--force` : ne pas passer `--force` sans accord)
- `python -m pytest`
- lecture DuckDB en Python avec `read_only=True` (le CLI 1.x installé ne lit pas une base écrite par DuckDB 2.0)

Demander avant :
- toute modification d'un prompt sans incrémenter sa version et relancer l'évaluation
- tout appel payant à l'API Claude en série (`scripts/eval_assistant.py`, boucles sur `ask.py`)
- toute installation de paquet (pip, winget, extension DuckDB)
- toute écriture en base hors scripts d'import
- toute commande git qui publie (`push`) ou réécrit l'historique

Interdites :
- modifier ou supprimer un fichier de `data/raw/`
- `DROP` ou `DELETE` sur une table `raw_*`
- écrire une clé ou un mot de passe dans un fichier
