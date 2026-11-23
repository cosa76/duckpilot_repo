# Bilan des critères de réussite

Section 13 de `docs/use_cases_ia_taches.txt`, évaluée le 23/11/2026 sur le projet tel qu'il est
(données synthétiques, un seul utilisateur).

| # | critère | verdict | preuve | ce qui manque |
|---|---|---|---|---|
| 1 | Un utilisateur peut obtenir une réponse fiable à une question métier | **Atteint techniquement** | `scripts/ask.py` : 18 justes sur 18 questions d'exemple, refus hors périmètre et injection (`docs/assistant_sql.md`) | Tests par de vrais utilisateurs, sur de vraies questions |
| 2 | Les données brutes ne sont jamais modifiées | **Atteint** | Empreinte SHA-256 avant et après chaque import ; sur 7 lancements, une seule empreinte par fichier (`journal_imports`) ; fichiers en lecture seule ; générateur bloqué sans `--force` | Rien |
| 3 | Chaque chiffre important peut être tracé jusqu'à sa requête SQL | **Partiel** | Tableaux du rapport d'analyse : fichier `sql/analyses/` cité ; assistant : SQL affiché ; rapport produit : `sql/produit/` | La synthèse de `report.py` et les tuiles de `dashboard.py` utilisent des requêtes écrites dans le code Python, pas dans `sql/` |
| 4 | Les traitements sont reproductibles | **Atteint** | `run_pipeline.py` en une commande, identifiant d'exécution, empreintes des sources citées dans le rapport, générateur à graine fixe, versions des paquets figées dans `requirements.txt` (corrigé lors de ce bilan : anthropic et matplotlib manquaient, et rien n'était figé) | Rien de bloquant. Pas d'environnement virtuel dédié |
| 5 | Les secrets ne sont jamais exposés | **Atteint** | Clé en variable d'environnement ; scan des secrets et hook pre-commit (passé au premier commit) ; envois API bloqués s'ils contiennent une clé ; email de commit en adresse noreply GitHub | Rien |
| 6 | Les résultats sont vérifiés avant diffusion | **Partiel** | Checklist de validation en fin de rapport d'analyse ; rapport produit marqué « à relire » si un chiffre est introuvable | Aucune validation humaine enregistrée à ce jour : la checklist n'a pas été cochée |
| 7 | Le temps nécessaire pour produire une analyse diminue | **Non mesuré** | Assistant : environ 5 s par question ; pipeline complet : moins de 10 s | Pas de mesure de référence « avant ». À mesurer sur quelques questions réelles, avec et sans l'assistant |
| 8 | Les erreurs de données sont détectées plus tôt | **Atteint (sur données synthétiques)** | Les anomalies injectées (`docs/anomalies_injectees.md`) sont toutes retrouvées par le profil et les contrôles ; 21 règles dont 13 bloquantes arrêtent le pipeline | Confirmer sur un jeu réel, où les anomalies ne sont pas connues d'avance |
| 9 | La documentation reste à jour | **Atteint** | README, CLAUDE.md, `docs/` (pipeline, transformations, assistant, décisions). Ce bilan a corrigé trois écarts : liste des tests dans `docs/pipeline.md`, nombre de questions d'évaluation, dépendances | Une relecture à chaque changement : rien ne l'automatise |
| 10 | Le premier use case apporte une valeur mesurable | **Non atteint** | Rien à mesurer sans utilisateurs ni données réelles | Définir un indicateur de valeur (temps gagné, questions traitées sans analyste) et le suivre sur un mois |

## Synthèse

- 6 critères atteints, 2 partiels, 2 non mesurés ou non atteints.
- Les critères techniques (données brutes, reproductibilité, secrets, détection d'erreurs)
  sont tenus. Les critères qui manquent dépendent d'un usage réel : données réelles,
  utilisateurs, mesure du temps gagné.

## Prochaines actions proposées, par ordre de valeur

1. Déposer un premier jeu de données réel dans `data/raw/` et adapter `config/sources.toml`.
2. Faire tester l'assistant SQL par 2 ou 3 utilisateurs, ajouter leurs questions à
   `config/questions_exemples.toml`, mesurer le temps gagné par rapport à leur méthode actuelle.
3. Valider à la main le rapport d'analyse avec sa checklist, et noter la validation.
4. Déplacer dans `sql/` les requêtes encore écrites dans `report.py` et `dashboard.py`.
