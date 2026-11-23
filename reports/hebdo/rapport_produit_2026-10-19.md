# Rapport produit, semaine du 2026-10-19 au 2026-10-25

_Données synthétiques. Indicateurs calculés en local par `sql/produit/`._

## Synthèse (rédigée par Claude, vérifiée : tous les chiffres cités se retrouvent dans les indicateurs)

L'usage est stable sur la semaine du 2026-10-19 au 2026-10-25. On compte 309 utilisateurs actifs, soit -1.3 % sur une semaine mais +5.7 % par rapport à la moyenne des 8 semaines. La qualité reste proche de l'habituel : le taux d'erreur est de 1.02 % contre une moyenne de 1.1. En revanche, la durée médiane des requêtes monte à 331.0 ms. Les ventes sont nettement au-dessus de la moyenne : le CA HT atteint 395398.0 €, soit +21.6 % vs la moyenne, avec 94 clients acheteurs. Le support reste calme : 14 tickets ouverts, aucun critique ni haute priorité, et une satisfaction moyenne de 4.6.

### Alertes

- 278 clients payants sur 486 n'ont aucun évènement dans la semaine, dont 139 en PME : risque de churn à surveiller.
- Durée médiane des requêtes à 331.0 ms, soit +10.7 % vs la semaine précédente, avec des erreurs TIMEOUT relevées : à surveiller la semaine prochaine.

### Constats

- Les ventes sont fortes. Le CA HT atteint 395398.0 €, soit +57.2 % vs la semaine précédente et +21.6 % vs la moyenne. La marge HT s'établit à 208547.13 €, soit +31.3 % vs la moyenne. Les clients acheteurs sont 94, soit +27.0 % vs la moyenne. _(sources : ventes)_
- L'usage est au-dessus de la moyenne des 8 semaines. Les utilisateurs actifs journaliers moyens sont à 64.9 (+9.3 %) et les requêtes à 642 (+10.2 %). Le nombre d'utilisateurs actifs hebdomadaires (309) recule légèrement de -1.3 % vs la semaine précédente, ce qui n'est pas une tendance. _(sources : activite, fonctionnalites)_
- La durée médiane des requêtes passe à 331.0 ms, contre 299.0 ms la semaine précédente (+10.7 %) et 314.0 ms en moyenne (+5.4 %). Les codes d'erreur relevés sur la version 4.0.1 incluent TIMEOUT. _(sources : activite, erreurs_par_version)_
- Les erreurs passent de 24 à 29 (+20.8 %). Ce sont de petits effectifs. Le taux d'erreur de 1.02 % reste sous la moyenne de 1.1 (-7.3 %), donc pas de dégradation établie. La quasi-totalité de l'activité est sur la version 4.0.1. _(sources : activite, erreurs_par_version)_
- Sur 486 clients payants, 278 n'ont aucun évènement dans la semaine. Le segment PME en compte 139 sur 224 payants. La rétention hebdomadaire est de 50.5 % (158 retenus) et on compte 19 nouveaux utilisateurs. Les 321 utilisateurs à risque relèvent d'un périmètre de 4 semaines : ce chiffre ne se compare pas directement aux 309 actifs. _(sources : segments, retention)_

### Hypothèses d'amélioration

**1. La hausse de latence des requêtes pourrait provoquer une partie des erreurs TIMEOUT et freiner l'usage des tableaux de bord.**

- Indicateur d'appui : duree_requete_mediane_ms à 331.0 ms (+10.7 % vs semaine précédente), code TIMEOUT présent sur la version 4.0.1, view_dashboard à 682 contre 731.
- Données à vérifier : Répartition des erreurs par code (part de TIMEOUT), latence p95/p99 par type de requête et par client, évolution sur plusieurs semaines pour écarter une variation ponctuelle.
- Action à tester : Identifier les requêtes les plus lentes, puis tester une mise en cache des résultats des tableaux de bord fréquemment consultés sur un groupe de clients. Mesurer ensuite la latence et les TIMEOUT.
- Sources : activite, erreurs_par_version, fonctionnalites

**2. Une part importante des clients payants n'utilise pas le produit, ce qui exposerait au churn lors des renouvellements, surtout chez les PME.**

- Indicateur d'appui : payants_sans_usage à 278 sur 486 payants au total, dont 139 en PME. a_risque à 321.
- Données à vérifier : Date du dernier évènement et date d'achat de ces clients, type d'offre achetée (certains achats peuvent ne pas impliquer d'usage hebdomadaire), historique de renouvellement par segment.
- Action à tester : Lancer une séquence de réactivation ciblée sur les PME payantes sans usage (email avec tableau de bord pré-configuré, proposition d'accompagnement). Comparer leur retour à l'usage avec un groupe témoin.
- Sources : segments, retention

**3. L'invitation de collègues est peu utilisée, ce qui limiterait la diffusion du produit dans les comptes et la rétention.**

- Indicateur d'appui : invite_user à 28 utilisations (1.3 % de l'usage), contre 181 pour share_report. Rétention hebdomadaire à 50.5 %.
- Données à vérifier : Rétention comparée des comptes avec un ou plusieurs utilisateurs, nombre d'utilisateurs par client, parcours après un partage de rapport. La baisse de 38 à 28 porte sur de petits effectifs et ne suffit pas à conclure.
- Action à tester : Proposer une invitation directe au moment du partage d'un rapport (share_report). Mesurer le taux d'invitation et la rétention des comptes concernés.
- Sources : fonctionnalites, retention

### Points de vérification

- Aucun problème détecté.

_Modèle claude-opus-5-5, prompt rapport_produit v2, 4224 tokens en entrée, 3017 en sortie, requête req_011ChLgnNLKmfUJfjDFxcjTH._

## Indicateurs

### Activité (semaine, précédente, moyenne des 8 précédentes)

| indicateur | semaine | semaine_precedente | moyenne_8_semaines | variation_vs_precedente_pct | variation_vs_moyenne_pct |
|---|---|---|---|---|---|
| utilisateurs_actifs | 309 | 313 | 292,20 | -1,30 | 5,70 |
| utilisateurs_actifs_jour_moyen | 64,90 | 62,70 | 59,40 | 3,50 | 9,30 |
| evenements | 2 852 | 2 924 | 2 676,50 | -2,50 | 6,60 |
| requetes | 642 | 629 | 582,60 | 2,10 | 10,20 |
| rapports_crees | 257 | 275 | 249,20 | -6,50 | 3,10 |
| exports | 296 | 291 | 276,90 | 1,70 | 6,90 |
| erreurs | 29 | 24 | 28,20 | 20,80 | 2,80 |
| taux_erreur_pct | 1,02 | 0,82 | 1,10 | 24,40 | -7,30 |
| duree_requete_mediane_ms | 331 | 299 | 314 | 10,70 | 5,40 |

### Ventes

| indicateur | semaine | semaine_precedente | moyenne_8_semaines | variation_vs_precedente_pct | variation_vs_moyenne_pct |
|---|---|---|---|---|---|
| ventes | 103 | 88 | 82,20 | 17 | 25,30 |
| clients_acheteurs | 94 | 75 | 74 | 25,30 | 27 |
| ca_ht | 395 398 | 251 539,75 | 325 231,60 | 57,20 | 21,60 |
| marge_ht | 208 547,13 | 137 402,15 | 158 793,10 | 51,80 | 31,30 |

### Fonctionnalités

| fonctionnalite | utilisations | part_pct | utilisations_semaine_precedente |
|---|---|---|---|
| view_dashboard | 682 | 32,70 | 731 |
| run_query | 642 | 30,80 | 629 |
| export_csv | 296 | 14,20 | 291 |
| create_report | 257 | 12,30 | 275 |
| share_report | 181 | 8,70 | 181 |
| invite_user | 28 | 1,30 | 38 |

### Erreurs par version

| version | evenements | erreurs | taux_erreur_pct | codes_erreur |
|---|---|---|---|---|
| 4.0.1 | 2 851 | 29 | 1,02 | E403, E404, E500, TIMEOUT |
| inconnue | 1 | 0 | 0 |  |

### Rétention

| actifs_semaine_precedente | retenus | retention_hebdo_pct | a_risque | nouveaux |
|---|---|---|---|---|
| 313 | 158 | 50,50 | 321 | 19 |

### Segments

| segment | clients | actifs_usage | payants | payants_sans_usage |
|---|---|---|---|---|
| ETI | 230 | 93 | 134 | 62 |
| Grand compte | 77 | 36 | 50 | 20 |
| Inconnu | 2 | 1 | 0 | 0 |
| PME | 536 | 130 | 224 | 139 |
| Particulier | 355 | 49 | 78 | 57 |
| total | 1 200 | 309 | 486 | 278 |

### Support

| priorite | ouverts_semaine | ouverts_semaine_precedente | resolus_semaine | delai_median_h | satisfaction_moyenne |
|---|---|---|---|---|---|
| critique | 0 | 1 | 0 |  |  |
| haute | 0 | 1 | 0 |  |  |
| normale | 9 | 5 | 6 | 28,10 | 4,33 |
| basse | 5 | 5 | 4 | 104,70 | 5 |
| non_renseignee | 0 | 0 | 0 |  |  |
| total | 14 | 12 | 10 | 58,40 | 4,60 |
