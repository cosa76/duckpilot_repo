# Rapport produit, semaine du 2026-10-19 au 2026-10-25

_Données synthétiques. Indicateurs calculés en local par `sql/produit/`._

## Synthèse (rédigée par Claude, vérifiée : tous les chiffres cités se retrouvent dans les indicateurs)

Les données sont synthétiques et les effectifs sont petits : la plupart des écarts relèvent du bruit. L'usage est un peu plus élevé, avec 172 utilisateurs actifs contre 154 la semaine précédente et une moyenne de 156.5 sur 8 semaines. Le taux d'erreur est de 5.07 %, sous la moyenne de 5.7 %, mais la durée médiane des requêtes monte à 480.0 ms. Le CA HT recule à 111332.12 € (-14.0 %) alors que la marge HT progresse (+6.5 %) : les indicateurs ne permettent pas d'expliquer cet écart. Le support reste à faible volume, avec 6 tickets ouverts, dont 1 critique noté 2.0 en satisfaction.

### Alertes

- Nouveaux utilisateurs à 0 alors que 172 utilisateurs sont actifs : vérifier la collecte ou le calcul de l'indicateur nouveaux.
- Ticket critique résolu avec une satisfaction de 2.0 : examiner ce cas individuellement.
- Tickets de priorité haute : 3 ouverts contre 0 la semaine précédente, 1 seul résolu, avec un délai médian de 72.8 h.
- CA HT en baisse de 14.0 % alors que la marge HT progresse de 6.5 % : vérifier la cohérence des données de ventes avant toute interprétation.

### Constats

- L'activité est en légère hausse : 172 utilisateurs actifs (+11.7 % vs semaine précédente, +9.9 % vs moyenne 8 semaines) et 54 requêtes contre 44. Sur ces volumes, cela ne suffit pas à parler de tendance. _(sources : activite, fonctionnalites)_
- La durée médiane des requêtes passe de 347.0 ms à 480.0 ms (+38.3 %). Elle reste à +14.5 % de la moyenne 8 semaines (419.2 ms). Le code TIMEOUT apparaît sur les versions 3.1.0, 3.2.0 et 3.3.0, pas sur la 4.0.0. _(sources : activite, erreurs_par_version)_
- Le CA HT baisse à 111332.12 € (-14.0 % vs précédente, -11.7 % vs moyenne), alors que le nombre de ventes est stable (50 contre 52) et que la marge HT monte à 50510.82 € (+6.5 %). Les indicateurs fournis ne permettent pas d'expliquer cette divergence. _(sources : ventes)_
- La rétention hebdomadaire est de 32.5 % (50 retenus sur 154 actifs la semaine précédente). 266 utilisateurs sont à risque et aucun nouvel utilisateur n'est enregistré (0). _(sources : retention)_
- Sur 361 clients payants, 234 n'ont aucun évènement dans la semaine. Les plus gros effectifs sont en PME (65), puis en Grand compte et chez les Particuliers (58 chacun). _(sources : segments)_

### Hypothèses d'amélioration

**1. La lenteur des requêtes, et les timeouts sur les versions antérieures à 4.0.0, dégradent l'expérience. Cela peut freiner le passage de l'analyse à la création de rapports.**

- Indicateur d'appui : duree_requete_mediane_ms à 480.0 (+38.3 %), code TIMEOUT présent sur 3.1.0, 3.2.0 et 3.3.0, 0 erreur sur 4.0.0 (41 évènements).
- Données à vérifier : Distribution complète des durées (p90, p95) par version et par type de requête sur plusieurs semaines. Nombre de TIMEOUT par version. Part des utilisateurs sur 4.0.0.
- Action à tester : Inciter la migration vers 4.0.0 auprès des utilisateurs des anciennes versions. Tester un cache ou une limite de temps avec message explicite sur les requêtes longues.
- Sources : activite, erreurs_par_version

**2. Une part importante des clients payants n'utilise pas le produit dans la semaine, ce qui crée un risque de non-renouvellement.**

- Indicateur d'appui : payants_sans_usage à 234 sur 361 payants, 266 utilisateurs à risque, rétention hebdomadaire de 32.5 %.
- Données à vérifier : Date de dernière activité par client payant. Dates de renouvellement. Historique de payants_sans_usage sur plusieurs semaines, pour distinguer un usage mensuel normal d'un désengagement.
- Action à tester : Lancer une campagne de réactivation ciblée (e-mail et message in-app avec un cas d'usage), d'abord sur le segment PME (65 payants sans usage), et mesurer le retour à l'usage.
- Sources : segments, retention

**3. Les utilisateurs lancent des requêtes et exportent en CSV plutôt que de créer des rapports dans l'outil. Le passage de la requête au rapport présenterait une friction.**

- Indicateur d'appui : create_report à 11 (contre 16) alors que run_query est à 54 et export_csv à 18. Les volumes sont faibles, donc ce n'est qu'un signal.
- Données à vérifier : Parcours par utilisateur requête → rapport → partage sur plusieurs semaines. Part des exports qui suivent directement une requête. Abandons en cours de création de rapport.
- Action à tester : Ajouter un bouton « Enregistrer comme rapport » directement après l'exécution d'une requête. Comparer le taux de création de rapports entre deux groupes.
- Sources : fonctionnalites, activite

### Points de vérification

- Aucun problème détecté.

_Modèle claude-opus-5-5, prompt rapport_produit v2, 4400 tokens en entrée, 2950 en sortie, requête req_011ChLfJEMxqavMfVe5jBiM5._

## Indicateurs

### Activité (semaine, précédente, moyenne des 8 précédentes)

| indicateur | semaine | semaine_precedente | moyenne_8_semaines | variation_vs_precedente_pct | variation_vs_moyenne_pct |
|---|---|---|---|---|---|
| utilisateurs_actifs | 172 | 154 | 156,50 | 11,70 | 9,90 |
| utilisateurs_actifs_jour_moyen | 28,60 | 26,60 | 26,50 | 7,50 | 7,90 |
| evenements | 217 | 206 | 206,10 | 5,30 | 5,30 |
| requetes | 54 | 44 | 43,50 | 22,70 | 24,10 |
| rapports_crees | 11 | 16 | 15,20 | -31,20 | -27,60 |
| exports | 18 | 14 | 14,60 | 28,60 | 23,30 |
| erreurs | 11 | 9 | 11,80 | 22,20 | -6,80 |
| taux_erreur_pct | 5,07 | 4,37 | 5,70 | 16 | -11,10 |
| duree_requete_mediane_ms | 480 | 347 | 419,20 | 38,30 | 14,50 |

### Ventes

| indicateur | semaine | semaine_precedente | moyenne_8_semaines | variation_vs_precedente_pct | variation_vs_moyenne_pct |
|---|---|---|---|---|---|
| ventes | 50 | 52 | 53,20 | -3,80 | -6 |
| clients_acheteurs | 49 | 48 | 50 | 2,10 | -2 |
| ca_ht | 111 332,12 | 129 381,50 | 126 131,20 | -14 | -11,70 |
| marge_ht | 50 510,82 | 47 421,65 | 50 014 | 6,50 | 1 |

### Fonctionnalités

| fonctionnalite | utilisations | part_pct | utilisations_semaine_precedente |
|---|---|---|---|
| run_query | 54 | 35,10 | 44 |
| view_dashboard | 54 | 35,10 | 49 |
| export_csv | 18 | 11,70 | 14 |
| create_report | 11 | 7,10 | 16 |
| share_report | 9 | 5,80 | 5 |
| invite_user | 8 | 5,20 | 8 |

### Erreurs par version

| version | evenements | erreurs | taux_erreur_pct | codes_erreur |
|---|---|---|---|---|
| 3.1.0 | 42 | 2 | 4,76 | E403, TIMEOUT |
| 3.2.0 | 38 | 3 | 7,89 | E404, E500, TIMEOUT |
| 3.2.1 | 47 | 3 | 6,38 | E403, E404 |
| 3.3.0 | 49 | 3 | 6,12 | E404, TIMEOUT |
| 4.0.0 | 41 | 0 | 0 |  |

### Rétention

| actifs_semaine_precedente | retenus | retention_hebdo_pct | a_risque | nouveaux |
|---|---|---|---|---|
| 154 | 50 | 32,50 | 266 | 0 |

### Segments

| segment | clients | actifs_usage | payants | payants_sans_usage |
|---|---|---|---|---|
| ETI | 111 | 31 | 72 | 52 |
| Grand compte | 139 | 57 | 105 | 58 |
| Inconnu | 1 | 0 | 1 | 1 |
| PME | 125 | 38 | 91 | 65 |
| Particulier | 124 | 46 | 92 | 58 |
| total | 500 | 172 | 361 | 234 |

### Support

| priorite | ouverts_semaine | ouverts_semaine_precedente | resolus_semaine | delai_median_h | satisfaction_moyenne |
|---|---|---|---|---|---|
| critique | 1 | 0 | 1 | 14,30 | 2 |
| haute | 3 | 0 | 1 | 72,80 |  |
| normale | 1 | 2 | 1 | 41,70 | 3 |
| basse | 1 | 3 | 2 | 61,90 | 4,50 |
| non_renseignee | 0 | 0 | 0 |  |  |
| total | 6 | 5 | 5 | 49,70 | 3,50 |
