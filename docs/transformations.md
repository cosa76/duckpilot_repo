# Transformations raw vers staging

Toutes les règles sont dans `sql/staging/`. Chaque règle porte un code repris
en commentaire dans le SQL. Chaque exécution est tracée dans la table
`journal_transformations` (fichier, date, durée, statut, erreur).

Principe : une ligne n'est jamais perdue en silence. Elle est soit gardée
(éventuellement corrigée et signalée), soit isolée dans la table `rejets`
avec son motif et la ligne brute complète en JSON.

Les tables staging sont aussi exportées en Parquet dans `data/staging/`.

## staging_clients (`01_staging_clients.sql`)

| code | règle |
|---|---|
| C1 | Doublons exacts supprimés |
| C2 | PII retirées : prénom, nom et téléphone non repris. Email remplacé par `email_hash` (md5) et `email_domaine` |
| C3 | Email invalide : hash et domaine à NULL, `email_valide = false` |
| C4 | Ville : espaces retirés, première lettre en majuscule |
| C5 | Segment vide : `Inconnu` |
| C6 | Date d'inscription future : NULL, `date_inscription_invalide = true` |
| C7 | Même email sur plusieurs `client_id` : `doublon_de` pointe vers le plus petit identifiant. Pas de fusion automatique |

## staging_produits (`02_staging_produits.sql`)

| code | règle |
|---|---|
| P1 | Prix et coût : virgule convertie, DECIMAL(12,2), considérés HT |
| P2 | Catégorie : première lettre en majuscule |
| P3 | `cout_superieur_prix = true` si le coût dépasse le prix (produit gardé) |

## staging_ventes (`03_staging_ventes.sql`)

Hypothèse : `prix_unitaire` est HT et `montant_ttc` inclut une TVA de 20 %.

| code | règle |
|---|---|
| V1 | Doublons exacts supprimés |
| V2 | Date ISO ou JJ/MM/AAAA |
| V3 | Montant TTC vide : recalculé, `montant_recalcule = true` |
| V4 | Canal : minuscules, espaces retirés, `tel` devient `telephone` |
| R1 | Rejet : même `vente_id` avec des contenus différents (toutes les versions isolées) |
| R2 | Rejet : date manquante ou invalide |
| R3 | Rejet : client inconnu |
| R4 | Rejet : produit inconnu |
| R5 | Rejet : devise autre que EUR |
| R6 | Rejet : quantité hors 1 à 100 |
| R7 | Rejet : montant négatif (avoir ou erreur, à trancher par le métier) |
| R8 | Rejet : montant TTC éloigné de plus de 0,05 du calcul quantité x prix x (1 - remise) x 1,2 |

Colonnes calculées : `montant_ht = montant_ttc / 1,2`, `marge_ht = montant_ht - quantite x cout_unitaire_ht`.

## staging_evenements (`04_staging_evenements.sql`)

| code | règle |
|---|---|
| E1 | Doublons exacts supprimés |
| E2 | Horodatage ISO, ou epoch en secondes interprété en UTC (`ts_depuis_epoch = true`) |
| E3 | `event_name` en minuscules |
| E4 | Version absente : `inconnue` |
| E5 | Propriétés JSON extraites : `session_id`, `duree_ms`, `code_erreur`, `nb_lignes` |
| E6 | Durée > 1 h : NULL, `duree_aberrante = true` |
| R1 | Rejet : `user_id` manquant |
| R2 | Rejet : horodatage non convertible |
| R3 | Rejet : horodatage futur |

## staging_tickets (`05_staging_tickets.sql`)

Aucun rejet : chaque ticket compte comme incident.

| code | règle |
|---|---|
| T1 | Doublons exacts supprimés |
| T2 | Priorité vide : `non_renseignee` |
| T3 | Satisfaction hors 1 à 5 : NULL |
| T4 | Résolution avant ouverture : date de résolution à NULL, `anomalie = resolution_avant_ouverture` |
| T5 | Statut ouvert ou en cours avec date de résolution : `anomalie = statut_incoherent` |
| T6 | Délai calculé seulement pour résolu ou fermé sans anomalie |
| T7 | Description : emails et téléphones masqués |

## Vues métier (`sql/marts/`)

| vue | contenu |
|---|---|
| `v_ventes_enrichies` | Ventes valides avec segment, ville, produit et catégorie |
| `v_clients_statut` | Historique d'achat par client et statut (actif sur 90 jours, inactif, sans achat) |
| `v_usage_mensuel` | Utilisateurs actifs, évènements et erreurs par mois |

## Requêtes d'analyse (`sql/analyses/`)

| fichier | question |
|---|---|
| `01_ca_marge_mensuels.sql` | CA et marge HT par mois |
| `02_ca_par_categorie_canal.sql` | CA et marge par catégorie et canal |
| `03_clients_actifs_segment.sql` | Clients actifs, inactifs et sans achat par segment |
| `04_support_resolution.sql` | Tickets et délai de résolution par priorité |
| `05_usage_erreurs_version.sql` | Usage et taux d'erreur par version |
| `06_usage_mensuel.sql` | Utilisateurs actifs mensuels et taux d'erreur par mois |
