# Décisions et limites

Journal des choix structurants du projet. Une décision = le contexte, le choix,
les options écartées et ce qui pourrait la remettre en cause.
À compléter à chaque nouveau choix, sans réécrire les anciennes entrées.

## Décisions

### D01. Données synthétiques en attendant un jeu réel (semaine 1)

- **Choix** : générer 5 fichiers synthétiques (`scripts/generate_synthetic_data.py`, graine 42)
  avec environ 40 types d'anomalies documentées (`docs/anomalies_injectees.md`).
- **Pourquoi** : tester la chaîne sans exposer de données réelles, avec une vérité terrain
  pour les contrôles.
- **Conséquence** : aucun chiffre du projet n'a de valeur métier. Les tirages sont uniformes,
  donc les tendances observées sont du bruit.
- **À revoir** : dès qu'un jeu réel est déposé dans `data/raw/`.

### D02. Couche raw en texte, typage en staging (semaine 1)

- **Choix** : CSV et JSON chargés en VARCHAR, sans correction.
- **Pourquoi** : ne rien perdre des valeurs mal formées, pouvoir tracer chaque rejet.
- **Écarté** : typage à l'import (perte silencieuse des dates FR, virgules décimales).

### D03. Isoler plutôt que corriger ou supprimer (semaine 2)

- **Choix** : une ligne invalide va dans `rejets` avec son motif et sa ligne brute.
  Une ligne corrigeable est corrigée et signalée par une colonne booléenne.
- **Règles à valider par le métier** : montants négatifs rejetés (ce sont peut-être des avoirs),
  `vente_id` en conflit rejetés en totalité, ventes en USD rejetées faute de taux de change,
  TVA supposée à 20 %, client actif = achat dans les 90 jours avant la dernière vente connue.

### D04. Données personnelles retirées dès staging (semaine 2)

- **Choix** : prénom, nom et téléphone non repris, email remplacé par un hash et un domaine,
  descriptions de tickets masquées. Les vues exposées à l'IA (schéma `ia`) n'ont ni PII
  ni texte libre.
- **Contrôle** : règles qualité bloquantes CLI_02 et TIC_02, tests dédiés.

### D05. Configuration plutôt que code pour les sources et les règles (semaine 3)

- **Choix** : `config/sources.toml` et `config/regles_qualite.toml`.
- **Pourquoi** : ajouter une source ou une règle sans toucher au code, versionner les règles.

### D06. Premier cas d'usage API : générateur SQL (semaine 4)

- **Choix** : question en français vers SQL DuckDB (`scripts/ask.py`).
- **Pourquoi** : seul le catalogue des vues part vers l'API, jamais les données.
  C'est le cas le plus sûr et le plus utile sur ces données.
- **Écarté** : classification des tickets (texte libre contenant des PII, 6 modèles de
  description seulement dans les données synthétiques) ; RAG documentaire (pas de corpus).

### D07. Garde-fous SQL par analyse syntaxique, pas par liste noire (semaine 4)

- **Choix** : `json_serialize_sql` de DuckDB pour n'accepter qu'un SELECT et lister les tables,
  connexion en lecture seule, accès externe coupé, configuration verrouillée.
- **Pourquoi** : une liste noire de mots-clés se contourne ; l'arbre syntaxique non.
  La liste noire de fonctions reste en défense complémentaire.

### D08. Modèle et réglages (semaine 4)

- **Choix** : `claude-opus-5-5`, effort `medium`, sortie JSON contrainte par schéma,
  repli serveur activé en cas de refus de sécurité.
- **Mesure** : 18 réponses justes sur 18 questions d'exemple (`reports/eval_assistant_sql.md`),
  environ 5 s par question.
- **À revoir** : un modèle moins cher (Sonnet, Haiku) ou un effort `low` pourraient suffire.
  À décider sur l'évaluation, pas a priori.

### D09. Second cas d'usage : rapport produit hebdomadaire (semaine 5)

- **Choix** : indicateurs calculés en local (`sql/produit/`), seuls les agrégats partent
  vers l'API, Claude rédige synthèse, constats et 3 hypothèses.
- **Contrôle anti-invention** : chaque chiffre cité par Claude est comparé aux indicateurs
  envoyés. Un chiffre introuvable passe le rapport en « à relire ». Les variations sont
  précalculées pour que le modèle n'ait rien à calculer.

### D10. Un seul point de passage vers l'API (semaine 5)

- **Choix** : `scripts/claude_client.py` pour tous les appels : blocage des emails,
  téléphones, IBAN et clés API dans tout envoi, taille maximale, budget journalier,
  journal sans contenu (`logs/api_calls.jsonl`).
- **Pourquoi** : une règle de sécurité appliquée à un seul endroit ne peut pas être oubliée
  par un nouveau cas d'usage.

### D11. Prompts versionnés en fichiers (semaine 5)

- **Choix** : `prompts/<usage>.md` avec un en-tête `version`. La version est écrite dans
  le journal API et dans chaque sortie.
- **Historique** :
  - `assistant_sql` v1 : inchangé. 6 questions plus difficiles ajoutées (variations,
    parts, cumuls, anti-jointure) : 6 sur 6 justes, aucune raison de modifier le prompt.
  - `rapport_produit` v1 puis v2 : en v1, le modèle a signalé à tort une incohérence entre
    `a_risque` (266) et les actifs de la semaine précédente (154), faute de définitions.
    v2 envoie un bloc `definitions` et demande de s'y référer. La fausse alerte a disparu
    au passage suivant.

### D12. Tableau de bord en HTML statique local (semaine 5)

- **Choix** : `reports/tableau_de_bord.html`, un seul fichier généré à chaque pipeline,
  sans serveur ni ressource externe.
- **Écarté** : Streamlit ou Power BI (installation ou publication de données, inutile à ce stade).

### D13. Protection des données brutes et des secrets (semaine 5)

- **Choix** : fichiers de `data/raw/` en lecture seule à chaque pipeline ; le générateur
  refuse d'écraser sans `--force`. Scan des secrets et des fichiers de données
  (`scripts/securite.py`), branché en hook git pre-commit (`.githooks/`).

## Limites connues

- **Données** : synthétiques et uniformes. Les indicateurs produit portent sur de petits
  effectifs (environ 200 évènements par semaine). La rétention par cohorte (J1, J7, J30)
  n'est pas calculable : tous les utilisateurs apparaissent dès janvier 2025.
- **Assistant SQL** : 18 questions d'évaluation, c'est peu. Un `;` dans une chaîne de
  caractères est refusé à tort. L'interprétation des résultats reste humaine.
- **Rapport produit** : la vérification contrôle les chiffres, pas le raisonnement.
  Une hypothèse peut être plausible et fausse : elle liste les données qui la confirmeraient.
- **Sécurité** : la détection de PII repose sur des expressions régulières (emails,
  téléphones français, IBAN français). Un nom propre dans une question n'est pas détecté.
- **Horodatages epoch** interprétés en UTC (décalage possible d'une à deux heures).
- **Outils** : le CLI DuckDB installé (1.5.6) ne lit pas la base écrite par DuckDB 2.0.
- **Versionnement** : dépôt git local sans commit ni remote à ce jour.
- **Planification** : aucun lancement automatique, tout se lance à la main.
