# Pipeline DuckPilot

## Lancer

```powershell
python scripts/run_pipeline.py
```

Code retour 0 si tout passe, 1 sinon. Chaque lancement reçoit un identifiant
`AAAAMMJJ_HHMMSS` (le `run_id`), partagé par toutes les étapes et écrit dans
tous les journaux.

## Étapes

```
data/raw/*  ──(1) sauvegarde de la base──────────────►  db/backups/analytics_<run_id>.duckdb
    ├──(1b) securite.py    data/raw en lecture seule, scan des secrets
    │
    ├──(2) import_raw.py   config/sources.toml       ►  raw_*            + journal_imports
    ├──(3) build.py        sql/staging/, sql/marts/  ►  staging_*, v_*   + rejets, journal_transformations
    │                                                    data/staging/*.parquet
    ├──(4) quality.py      config/regles_qualite.toml ►  controles_qualite   (arrêt si règle bloquante KO)
    ├──(5) profile_raw.py                            ►  reports/profil_qualite_raw.md
    ├──(6) report.py       sql/analyses/             ►  reports/rapport_analyse.md, reports/figures/
    ├──(6b) dashboard.py                             ►  reports/tableau_de_bord.html
    └──(7) execution_report.py                       ►  reports/executions/execution_<run_id>.md
```

L'étape 7 tourne toujours, même après un échec, pour garder une trace.
Les 5 dernières sauvegardes sont conservées.

## Garanties

| garantie | mécanisme |
|---|---|
| Fichiers sources jamais modifiés | lecture seule, empreinte SHA-256 avant et après chaque import |
| Import atomique | lecture en table temporaire, contrôle du schéma, puis remplacement en transaction. En cas d'erreur, l'ancienne table raw reste intacte |
| Schéma surveillé | colonne attendue manquante = échec ; colonne en plus = alerte |
| Nouvelle version de fichier détectée | comparaison avec l'empreinte du dernier import réussi (`nouveau`, `inchange`, `modifie`) |
| Aucune ligne perdue en silence | chaque ligne brute dédoublonnée est en staging ou dans `rejets` (règle VEN_06) |
| Données personnelles hors staging | règles CLI_02 et TIC_02, bloquantes |
| Chiffres reproductibles | le rapport cite le `run_id`, l'empreinte de chaque source et la requête de chaque tableau |

## Journaux dans la base

| table | contenu |
|---|---|
| `journal_imports` | un enregistrement par source et par lancement : fichier, empreinte, lignes, version, statut, alertes, erreur |
| `journal_transformations` | un enregistrement par fichier SQL exécuté : statut, durée, erreur |
| `controles_qualite` | un enregistrement par règle et par lancement : violations, taux, seuil, statut |
| `rejets` | lignes isolées par le dernier build, avec motif et ligne brute JSON |

Exemple, historique des contrôles en échec :

```sql
SELECT run_id, regle_id, severite, nb_violations, taux_pct
FROM controles_qualite
WHERE statut <> 'ok'
ORDER BY run_id DESC, regle_id;
```

## Ajouter une source

1. Déposer le fichier dans `data/raw/`.
2. Ajouter un bloc `[[source]]` dans `config/sources.toml` (table `raw_<entite>`, format, colonnes attendues).
3. Écrire `sql/staging/NN_staging_<entite>.sql` avec des règles codées et les rejets dans `rejets`.
4. Ajouter les règles de qualité dans `config/regles_qualite.toml`.
5. Documenter les règles dans `docs/transformations.md`.
6. Lancer `python scripts/run_pipeline.py` puis `python -m pytest`.

## Ajouter une règle de qualité

Ajouter un bloc `[[regle]]` dans `config/regles_qualite.toml`. La requête renvoie
deux nombres : lignes en violation et lignes contrôlées. Choisir `bloquant` si
une violation rend les chiffres faux, `alerte` si elle mérite seulement un regard.
Un `seuil_pct` tolère une part de violations.

## Tests

```powershell
python -m pytest
```

| fichier | ce qui est vérifié |
|---|---|
| `tests/test_import_generique.py` | import, détection de version, schéma, fichier absent, fichier intact (base en mémoire) |
| `tests/test_qualite.py` | moteur de règles, seuils, validité du fichier de règles, règles bloquantes sur la base réelle |
| `tests/test_raw_import.py` | aucune ligne perdue entre fichiers et tables raw |
| `tests/test_staging.py` | conservation, clés uniques, plages, intégrité référentielle, absence de PII |
| `tests/test_assistant_sql.py` | garde-fous SQL, catalogue conforme aux vues, refus des PII, parcours avec client API simulé |
| `tests/test_securite.py` | blocage des envois sensibles, budget, journal sans contenu, scan des secrets, vérification des chiffres du rapport produit |

Les tests sur la base réelle sont ignorés si le pipeline n'a pas encore tourné.

## Planification

Pas de planification automatique pour l'instant : le pipeline se lance à la main.
Pour un lancement quotidien sous Windows, une tâche planifiée peut appeler
`python scripts/run_pipeline.py` depuis la racine du projet.
