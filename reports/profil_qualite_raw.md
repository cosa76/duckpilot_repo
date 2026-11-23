# Profil qualité des tables raw

Généré le 2026-11-23 23:56 par `scripts/profile_raw.py` sur `db/analytics.duckdb`.

Données synthétiques. Les tables raw sont en texte pour les sources CSV et JSON : les valeurs numériques sont converties à la volée pour le profil, les valeurs non convertibles sont comptées comme nulles dans cette section.

## Synthèse

| table | lignes | colonnes |
|---|---|---|
| raw_clients | 1203 | 9 |
| raw_evenements | 186600 | 7 |
| raw_produits | 40 | 5 |
| raw_tickets | 1081 | 9 |
| raw_ventes | 5757 | 10 |

## Contrôles ciblés

| table | contrôle | lignes concernées |
|---|---|---|
| raw_ventes | date_vente vide | 6 |
| raw_ventes | date_vente au format JJ/MM/AAAA | 86 |
| raw_ventes | date_vente non convertible (ISO ni JJ/MM/AAAA) | 3 |
| raw_ventes | montant_ttc avec virgule décimale | 17 |
| raw_ventes | montant_ttc négatif | 12 |
| raw_ventes | quantite > 100 | 4 |
| raw_ventes | client_id absent de raw_clients | 15 |
| raw_ventes | produit_id absent de raw_produits | 5 |
| raw_ventes | canal hors liste (web, magasin, telephone, partenaire) | 28 |
| raw_ventes | devise différente de EUR | 3 |
| raw_produits | cout_unitaire > prix_unitaire | 0 |
| raw_clients | email vide | 12 |
| raw_clients | email au format invalide | 6 |
| raw_clients | ville hors référentiel (casse, espaces, inconnue) | 6 |
| raw_clients | date_inscription dans le futur | 1 |
| raw_clients | même email sur plusieurs client_id | 2 |
| raw_evenements | user_id vide | 186 |
| raw_evenements | timestamp non ISO (epoch ou autre) | 93 |
| raw_evenements | timestamp dans le futur | 10 |
| raw_evenements | event_name en majuscules | 93 |
| raw_evenements | app_version absente | 37 |
| raw_tickets | date_resolution antérieure à date_ouverture | 6 |
| raw_tickets | statut ouvert avec date_resolution renseignée | 4 |
| raw_tickets | satisfaction hors échelle 1 à 5 | 5 |
| raw_tickets | description contenant un email ou un téléphone (PII) | 8 |

## raw_clients

- Lignes : **1203**
- Colonnes métier : 9
- Lignes en double exact (hors colonnes techniques) : **1**
- Clé `client_id` : 1 valeurs en double, portées par 2 lignes

### Colonnes

| colonne | type | nulls | % nulls | distinct (approx) | min | max |
|---|---|---|---|---|---|---|
| client_id | VARCHAR | 0 | 0.00 | 1213 | C00001 | C01202 |
| prenom | VARCHAR | 0 | 0.00 | 37 | Alice | Zoé |
| nom | VARCHAR | 0 | 0.00 | 36 | Benali | Traoré |
| email | VARCHAR | 12 | 1.00 | 1159 | @exemple.test | zoe.traore973@exemple.test |
| telephone | VARCHAR | 0 | 0.00 | 1202 | 0110255435 | 0799912587 |
| ville | VARCHAR | 0 | 0.00 | 16 |  Marseille | paris  |
| segment | VARCHAR | 2 | 0.17 | 4 | ETI | Particulier |
| date_inscription | VARCHAR | 0 | 0.00 | 703 | 2023-01-01 00:00:00 | 2027-03-01 00:00:00 |
| actif | VARCHAR | 0 | 0.00 | 2 | False | True |

### Distributions principales

**segment**

| valeur | lignes | % |
|---|---|---|
| PME | 538 | 44.70 |
| Particulier | 356 | 29.60 |
| ETI | 230 | 19.10 |
| Grand compte | 77 | 6.40 |
| (null) | 2 | 0.20 |

**ville**

| valeur | lignes | % |
|---|---|---|
| Paris | 331 | 27.50 |
| Lyon | 145 | 12.10 |
| Montpellier | 111 | 9.20 |
| Toulouse | 101 | 8.40 |
| Marseille | 97 | 8.10 |
| Lille | 91 | 7.60 |
| Bordeaux | 85 | 7.10 |
| Rennes | 83 | 6.90 |
| Nantes | 77 | 6.40 |
| Strasbourg | 76 | 6.30 |

**actif**

| valeur | lignes | % |
|---|---|---|
| True | 722 | 60.00 |
| False | 481 | 40.00 |


## raw_evenements

- Lignes : **186600**
- Colonnes métier : 7
- Lignes en double exact (hors colonnes techniques) : **372**
- Clé `event_id` : 372 valeurs en double, portées par 744 lignes

### Colonnes

| colonne | type | nulls | % nulls | distinct (approx) | min | max |
|---|---|---|---|---|---|---|
| event_id | VARCHAR | 0 | 0.00 | 179276 | E0000001 | E0186228 |
| user_id | VARCHAR | 186 | 0.10 | 943 | C00009 | C01193 |
| event_name | VARCHAR | 0 | 0.00 | 17 | CREATE_REPORT | view_dashboard |
| timestamp | VARCHAR | 0 | 0.00 | 174356 | 1736759248 | 2027-01-01T00:00:00 |
| app_version | VARCHAR | 37 | 0.02 | 6 | 3.1.0 | 4.0.1 |
| plateforme | VARCHAR | 0 | 0.00 | 5 | android | windows |
| proprietes | JSON | 0 | 0.00 | 94401 | {"session_id":"S0000000","nb_l… | {"session_id":"S0186217"} |

### Valeurs numériques (conversion tolérante)

| colonne | valeurs | min | p01 | médiane | p99 | max | moyenne | écart-type | extrêmes (3 IQR) |
|---|---|---|---|---|---|---|---|---|---|
| duree_ms | 40533 | 7.00 | 43.00 | 372.00 | 3 371.00 | 86 400 000.00 | 11 239.59 | 959 555.57 | 1259 |
| nb_lignes | 19468 | 7.00 | 86.00 | 2 896.00 | 117 102.67 | 1 851 324.00 | 10 125.13 | 30 700.73 | 1388 |

### Distributions principales

**event_name**

| valeur | lignes | % |
|---|---|---|
| view_dashboard | 44155 | 23.70 |
| run_query | 40511 | 21.70 |
| login | 29089 | 15.60 |
| logout | 20491 | 11.00 |
| export_csv | 19454 | 10.40 |
| create_report | 17535 | 9.40 |
| share_report | 10881 | 5.80 |
| error | 2360 | 1.30 |
| invite_user | 2031 | 1.10 |
| LOGIN | 19 | 0.00 |

**plateforme**

| valeur | lignes | % |
|---|---|---|
| web | 102543 | 55.00 |
| windows | 46283 | 24.80 |
| macos | 23070 | 12.40 |
| ios | 9722 | 5.20 |
| android | 4982 | 2.70 |

**app_version**

| valeur | lignes | % |
|---|---|---|
| 3.3.0 | 79548 | 42.60 |
| 3.2.1 | 38578 | 20.70 |
| 4.0.1 | 36120 | 19.40 |
| 4.0.0 | 14561 | 7.80 |
| 3.1.0 | 12287 | 6.60 |
| 3.2.0 | 5469 | 2.90 |
| (null) | 37 | 0.00 |


## raw_produits

- Lignes : **40**
- Colonnes métier : 5
- Lignes en double exact (hors colonnes techniques) : **0**
- Clé `produit_id` : 0 valeurs en double, portées par 0 lignes

### Colonnes

| colonne | type | nulls | % nulls | distinct (approx) | min | max |
|---|---|---|---|---|---|---|
| produit_id | VARCHAR | 0 | 0.00 | 41 | P001 | P040 |
| libelle | VARCHAR | 0 | 0.00 | 41 | Accompagnement projet (jour) | Écran 27 pouces |
| categorie | VARCHAR | 0 | 0.00 | 5 | Conseil | Support |
| prix_unitaire | VARCHAR | 0 | 0.00 | 36 | 1100,0 | 950,0 |
| cout_unitaire | VARCHAR | 0 | 0.00 | 41 | 1069,04 | 984,81 |

### Valeurs numériques (conversion tolérante)

| colonne | valeurs | min | p01 | médiane | p99 | max | moyenne | écart-type | extrêmes (3 IQR) |
|---|---|---|---|---|---|---|---|---|---|
| prix_unitaire | 40 | 85.00 | 88.90 | 1 150.00 | 15 660.00 | 18 000.00 | 2 363.50 | 3 540.66 | 2 |
| cout_unitaire | 40 | 32.46 | 36.64 | 543.54 | 6 951.13 | 7 928.82 | 1 039.53 | 1 598.59 | 3 |

### Distributions principales

**categorie**

| valeur | lignes | % |
|---|---|---|
| Logiciel | 10 | 25.00 |
| Conseil | 9 | 22.50 |
| Materiel | 8 | 20.00 |
| Formation | 7 | 17.50 |
| Support | 6 | 15.00 |


## raw_tickets

- Lignes : **1081**
- Colonnes métier : 9
- Lignes en double exact (hors colonnes techniques) : **4**
- Clé `ticket_id` : 4 valeurs en double, portées par 8 lignes

### Colonnes

| colonne | type | nulls | % nulls | distinct (approx) | min | max |
|---|---|---|---|---|---|---|
| ticket_id | VARCHAR | 0 | 0.00 | 1017 | T00001 | T01077 |
| client_id | VARCHAR | 0 | 0.00 | 586 | C00019 | C01189 |
| date_ouverture | TIMESTAMP | 0 | 0.00 | 1067 | 2025-01-04 08:59:01 | 2026-10-31 18:36:15 |
| date_resolution | TIMESTAMP | 4 | 0.37 | 1118 | 2025-01-06 23:44:17 | 2026-10-30 08:20:24 |
| categorie | VARCHAR | 0 | 0.00 | 5 | Acces | Question |
| priorite | VARCHAR | 6 | 0.56 | 4 | basse | normale |
| statut | VARCHAR | 0 | 0.00 | 4 | en_cours | resolu |
| satisfaction | BIGINT | 427 | 39.50 | 7 | 0 | 7 |
| description | VARCHAR | 0 | 0.00 | 33 | Changement d'adresse de factur… | Requête très lente sur gros vo… |

### Valeurs numériques (conversion tolérante)

| colonne | valeurs | min | p01 | médiane | p99 | max | moyenne | écart-type | extrêmes (3 IQR) |
|---|---|---|---|---|---|---|---|---|---|
| satisfaction | 654 | 0.00 | 1.00 | 4.00 | 5.00 | 7.00 | 4.12 | 0.99 | 1 |
| delai_resolution_h | 1077 | -5.00 | 1.71 | 39.20 | 298.00 | 950.07 | 57.77 | 67.76 | 19 |

### Distributions principales

**categorie**

| valeur | lignes | % |
|---|---|---|
| Question | 402 | 37.20 |
| Facturation | 333 | 30.80 |
| Acces | 201 | 18.60 |
| Bug | 98 | 9.10 |
| Performance | 47 | 4.30 |

**priorite**

| valeur | lignes | % |
|---|---|---|
| normale | 468 | 43.30 |
| basse | 415 | 38.40 |
| haute | 161 | 14.90 |
| critique | 31 | 2.90 |
| (null) | 6 | 0.60 |

**statut**

| valeur | lignes | % |
|---|---|---|
| resolu | 645 | 59.70 |
| ferme | 428 | 39.60 |
| ouvert | 7 | 0.60 |
| en_cours | 1 | 0.10 |


## raw_ventes

- Lignes : **5757**
- Colonnes métier : 10
- Lignes en double exact (hors colonnes techniques) : **30**
- Clé `vente_id` : 36 valeurs en double, portées par 72 lignes

### Colonnes

| colonne | type | nulls | % nulls | distinct (approx) | min | max |
|---|---|---|---|---|---|---|
| vente_id | VARCHAR | 0 | 0.00 | 5734 | V000001 | V005721 |
| date_vente | VARCHAR | 6 | 0.10 | 631 | 01/07/2025 | 31/07/2026 |
| client_id | VARCHAR | 0 | 0.00 | 950 | C00009 | C99281 |
| produit_id | VARCHAR | 0 | 0.00 | 42 | P001 | P999 |
| quantite | VARCHAR | 0 | 0.00 | 61 | 1 | 9 |
| prix_unitaire | VARCHAR | 0 | 0.00 | 36 | 1100.00 | 950.00 |
| remise_pct | VARCHAR | 0 | 0.00 | 4 | 0.0 | 0.15 |
| montant_ttc | VARCHAR | 6 | 0.10 | 729 | -1140.00 | 9975.00 |
| canal | VARCHAR | 0 | 0.00 | 8 |  web | web |
| devise | VARCHAR | 0 | 0.00 | 2 | EUR | USD |

### Valeurs numériques (conversion tolérante)

| colonne | valeurs | min | p01 | médiane | p99 | max | moyenne | écart-type | extrêmes (3 IQR) |
|---|---|---|---|---|---|---|---|---|---|
| quantite | 5757 | 1.00 | 1.00 | 2.00 | 40.00 | 1 200.00 | 5.83 | 25.35 | 249 |
| prix_unitaire | 5757 | 85.00 | 85.00 | 950.00 | 18 000.00 | 18 000.00 | 1 825.45 | 3 115.75 | 674 |
| remise_pct | 5757 | 0.00 | 0.00 | 0.05 | 0.15 | 0.15 | 0.05 | 0.05 | 0 |
| montant_ttc | 5751 | -19 440.00 | 114.00 | 2 565.00 | 31 405.50 | 65 280.00 | 5 032.11 | 6 589.89 | 326 |

### Distributions principales

**canal**

| valeur | lignes | % |
|---|---|---|
| telephone | 2105 | 36.60 |
| partenaire | 1713 | 29.80 |
| web | 1619 | 28.10 |
| magasin | 292 | 5.10 |
| WEB | 10 | 0.20 |
|  web | 9 | 0.20 |
| tel | 5 | 0.10 |
| Web | 4 | 0.10 |

**devise**

| valeur | lignes | % |
|---|---|---|
| EUR | 5754 | 99.90 |
| USD | 3 | 0.10 |

