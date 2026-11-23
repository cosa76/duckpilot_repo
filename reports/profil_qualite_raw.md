# Profil qualité des tables raw

Généré le 2026-11-23 23:35 par `scripts/profile_raw.py` sur `db/analytics.duckdb`.

Données synthétiques. Les tables raw sont en texte pour les sources CSV et JSON : les valeurs numériques sont converties à la volée pour le profil, les valeurs non convertibles sont comptées comme nulles dans cette section.

## Synthèse

| table | lignes | colonnes |
|---|---|---|
| raw_clients | 502 | 9 |
| raw_evenements | 20050 | 7 |
| raw_produits | 40 | 5 |
| raw_tickets | 803 | 9 |
| raw_ventes | 5025 | 10 |

## Contrôles ciblés

| table | contrôle | lignes concernées |
|---|---|---|
| raw_ventes | date_vente vide | 8 |
| raw_ventes | date_vente au format JJ/MM/AAAA | 150 |
| raw_ventes | date_vente non convertible (ISO ni JJ/MM/AAAA) | 3 |
| raw_ventes | montant_ttc avec virgule décimale | 30 |
| raw_ventes | montant_ttc négatif | 10 |
| raw_ventes | quantite > 100 | 4 |
| raw_ventes | client_id absent de raw_clients | 15 |
| raw_ventes | produit_id absent de raw_produits | 5 |
| raw_ventes | canal hors liste (web, magasin, telephone, partenaire) | 40 |
| raw_ventes | devise différente de EUR | 3 |
| raw_produits | cout_unitaire > prix_unitaire | 1 |
| raw_clients | email vide | 5 |
| raw_clients | email au format invalide | 3 |
| raw_clients | ville hors référentiel (casse, espaces, inconnue) | 2 |
| raw_clients | date_inscription dans le futur | 1 |
| raw_clients | même email sur plusieurs client_id | 1 |
| raw_evenements | user_id vide | 30 |
| raw_evenements | timestamp non ISO (epoch ou autre) | 10 |
| raw_evenements | timestamp dans le futur | 10 |
| raw_evenements | event_name en majuscules | 15 |
| raw_evenements | app_version absente | 5 |
| raw_tickets | date_resolution antérieure à date_ouverture | 4 |
| raw_tickets | statut ouvert avec date_resolution renseignée | 3 |
| raw_tickets | satisfaction hors échelle 1 à 5 | 4 |
| raw_tickets | description contenant un email ou un téléphone (PII) | 4 |

## raw_clients

- Lignes : **502**
- Colonnes métier : 9
- Lignes en double exact (hors colonnes techniques) : **1**
- Clé `client_id` : 1 valeurs en double, portées par 2 lignes

### Colonnes

| colonne | type | nulls | % nulls | distinct (approx) | min | max |
|---|---|---|---|---|---|---|
| client_id | VARCHAR | 0 | 0.00 | 493 | C00001 | C00501 |
| prenom | VARCHAR | 0 | 0.00 | 24 | Alice | Zoé |
| nom | VARCHAR | 0 | 0.00 | 19 | Bernard | Thomas |
| email | VARCHAR | 5 | 1.00 | 503 | @exemple.test | zoe.simon469@exemple.test |
| telephone | VARCHAR | 0 | 0.00 | 518 | 0610344303 | 0699913412 |
| ville | VARCHAR | 0 | 0.00 | 12 | Bordeaux | paris  |
| segment | VARCHAR | 1 | 0.20 | 4 | ETI | Particulier |
| date_inscription | VARCHAR | 0 | 0.00 | 323 | 2025-01-02 00:00:00 | 2027-03-01 00:00:00 |
| actif | VARCHAR | 0 | 0.00 | 2 | False | True |

### Distributions principales

**segment**

| valeur | lignes | % |
|---|---|---|
| Grand compte | 139 | 27.70 |
| PME | 125 | 24.90 |
| Particulier | 125 | 24.90 |
| ETI | 112 | 22.30 |
| (null) | 1 | 0.20 |

**ville**

| valeur | lignes | % |
|---|---|---|
| Lyon | 59 | 11.80 |
| Rennes | 54 | 10.80 |
| Toulouse | 53 | 10.60 |
| Montpellier | 52 | 10.40 |
| Bordeaux | 51 | 10.20 |
| Strasbourg | 50 | 10.00 |
| Marseille | 50 | 10.00 |
| Nantes | 48 | 9.60 |
| Paris | 44 | 8.80 |
| Lille | 39 | 7.80 |

**actif**

| valeur | lignes | % |
|---|---|---|
| True | 421 | 83.90 |
| False | 81 | 16.10 |


## raw_evenements

- Lignes : **20050**
- Colonnes métier : 7
- Lignes en double exact (hors colonnes techniques) : **50**
- Clé `event_id` : 50 valeurs en double, portées par 100 lignes

### Colonnes

| colonne | type | nulls | % nulls | distinct (approx) | min | max |
|---|---|---|---|---|---|---|
| event_id | VARCHAR | 0 | 0.00 | 19727 | E0000001 | E0020000 |
| user_id | VARCHAR | 30 | 0.15 | 493 | C00001 | C00501 |
| event_name | VARCHAR | 0 | 0.00 | 15 | CREATE_REPORT | view_dashboard |
| timestamp | VARCHAR | 0 | 0.00 | 19517 | 1736495488 | 2027-01-01T00:00:00 |
| app_version | VARCHAR | 5 | 0.02 | 5 | 3.1.0 | 4.0.0 |
| plateforme | VARCHAR | 0 | 0.00 | 5 | android | windows |
| proprietes | JSON | 0 | 0.00 | 12327 | {"session_id":"S00001","duree_… | {"session_id":"S06000"} |

### Valeurs numériques (conversion tolérante)

| colonne | valeurs | min | p01 | médiane | p99 | max | moyenne | écart-type | extrêmes (3 IQR) |
|---|---|---|---|---|---|---|---|---|---|
| duree_ms | 4391 | 5.00 | 38.00 | 409.00 | 4 013.60 | 86 400 000.00 | 59 700.35 | 2 257 825.47 | 124 |
| nb_lignes | 1584 | 19.00 | 497.83 | 24 658.00 | 49 199.68 | 49 924.00 | 24 626.34 | 14 511.95 | 0 |

### Distributions principales

**event_name**

| valeur | lignes | % |
|---|---|---|
| view_dashboard | 4962 | 24.70 |
| run_query | 4385 | 21.90 |
| login | 4026 | 20.10 |
| export_csv | 1584 | 7.90 |
| create_report | 1479 | 7.40 |
| logout | 1417 | 7.10 |
| error | 976 | 4.90 |
| share_report | 811 | 4.00 |
| invite_user | 395 | 2.00 |
| VIEW_DASHBOARD | 6 | 0.00 |

**plateforme**

| valeur | lignes | % |
|---|---|---|
| ios | 4082 | 20.40 |
| web | 4017 | 20.00 |
| macos | 3995 | 19.90 |
| android | 3988 | 19.90 |
| windows | 3968 | 19.80 |

**app_version**

| valeur | lignes | % |
|---|---|---|
| 3.3.0 | 4056 | 20.20 |
| 3.2.0 | 4017 | 20.00 |
| 3.2.1 | 4011 | 20.00 |
| 3.1.0 | 3998 | 19.90 |
| 4.0.0 | 3963 | 19.80 |
| (null) | 5 | 0.00 |


## raw_produits

- Lignes : **40**
- Colonnes métier : 5
- Lignes en double exact (hors colonnes techniques) : **0**
- Clé `produit_id` : 0 valeurs en double, portées par 0 lignes

### Colonnes

| colonne | type | nulls | % nulls | distinct (approx) | min | max |
|---|---|---|---|---|---|---|
| produit_id | VARCHAR | 0 | 0.00 | 41 | P001 | P040 |
| libelle | VARCHAR | 0 | 0.00 | 41 | Conseil 007 | Support 035 |
| categorie | VARCHAR | 0 | 0.00 | 6 | Conseil | logiciel |
| prix_unitaire | VARCHAR | 0 | 0.00 | 40 | 1035,01 | 940,13 |
| cout_unitaire | VARCHAR | 0 | 0.00 | 41 | 10,13 | 949,2 |

### Valeurs numériques (conversion tolérante)

| colonne | valeurs | min | p01 | médiane | p99 | max | moyenne | écart-type | extrêmes (3 IQR) |
|---|---|---|---|---|---|---|---|---|---|
| prix_unitaire | 40 | 29.46 | 36.79 | 987.57 | 2 428.01 | 2 430.97 | 978.25 | 715.45 | 0 |
| cout_unitaire | 40 | 10.13 | 13.80 | 484.78 | 1 764.94 | 1 798.81 | 570.05 | 467.47 | 0 |

### Distributions principales

**categorie**

| valeur | lignes | % |
|---|---|---|
| Logiciel | 10 | 25.00 |
| Materiel | 9 | 22.50 |
| Formation | 9 | 22.50 |
| Conseil | 8 | 20.00 |
| Support | 3 | 7.50 |
| logiciel | 1 | 2.50 |


## raw_tickets

- Lignes : **803**
- Colonnes métier : 9
- Lignes en double exact (hors colonnes techniques) : **3**
- Clé `ticket_id` : 3 valeurs en double, portées par 6 lignes

### Colonnes

| colonne | type | nulls | % nulls | distinct (approx) | min | max |
|---|---|---|---|---|---|---|
| ticket_id | VARCHAR | 0 | 0.00 | 768 | T00001 | T00800 |
| client_id | VARCHAR | 0 | 0.00 | 401 | C00001 | C00501 |
| date_ouverture | TIMESTAMP | 0 | 0.00 | 809 | 2025-01-02 02:45:00 | 2026-10-30 09:26:00 |
| date_resolution | TIMESTAMP | 180 | 22.42 | 618 | 2025-01-02 10:17:26.660771 | 2026-10-31 20:12:15.797113 |
| categorie | VARCHAR | 0 | 0.00 | 5 | Acces | Question |
| priorite | VARCHAR | 5 | 0.62 | 4 | basse | normale |
| statut | VARCHAR | 0 | 0.00 | 4 | en_cours | resolu |
| satisfaction | BIGINT | 277 | 34.50 | 7 | 1 | 10 |
| description | VARCHAR | 0 | 0.00 | 9 | Demande d'ajout d'un utilisate… | Requête très lente sur gros vo… |

### Valeurs numériques (conversion tolérante)

| colonne | valeurs | min | p01 | médiane | p99 | max | moyenne | écart-type | extrêmes (3 IQR) |
|---|---|---|---|---|---|---|---|---|---|
| satisfaction | 526 | 1.00 | 1.00 | 4.00 | 5.00 | 10.00 | 3.56 | 1.46 | 0 |
| delai_resolution_h | 623 | -5.00 | 0.02 | 21.13 | 121.29 | 179.47 | 30.24 | 29.39 | 3 |

### Distributions principales

**categorie**

| valeur | lignes | % |
|---|---|---|
| Acces | 170 | 21.20 |
| Bug | 162 | 20.20 |
| Facturation | 161 | 20.00 |
| Performance | 161 | 20.00 |
| Question | 149 | 18.60 |

**priorite**

| valeur | lignes | % |
|---|---|---|
| normale | 376 | 46.80 |
| basse | 180 | 22.40 |
| haute | 178 | 22.20 |
| critique | 64 | 8.00 |
| (null) | 5 | 0.60 |

**statut**

| valeur | lignes | % |
|---|---|---|
| resolu | 370 | 46.10 |
| ferme | 250 | 31.10 |
| ouvert | 94 | 11.70 |
| en_cours | 89 | 11.10 |


## raw_ventes

- Lignes : **5025**
- Colonnes métier : 10
- Lignes en double exact (hors colonnes techniques) : **20**
- Clé `vente_id` : 25 valeurs en double, portées par 50 lignes

### Colonnes

| colonne | type | nulls | % nulls | distinct (approx) | min | max |
|---|---|---|---|---|---|---|
| vente_id | VARCHAR | 0 | 0.00 | 4901 | V000001 | V005000 |
| date_vente | VARCHAR | 8 | 0.16 | 820 | 01/01/2026 | 31/05/2025 |
| client_id | VARCHAR | 0 | 0.00 | 511 | C00001 | C99497 |
| produit_id | VARCHAR | 0 | 0.00 | 42 | P001 | P999 |
| quantite | VARCHAR | 0 | 0.00 | 9 | 1 | 9999 |
| prix_unitaire | VARCHAR | 0 | 0.00 | 41 | 1035.01 | 940.13 |
| remise_pct | VARCHAR | 0 | 0.00 | 4 | 0.0 | 0.15 |
| montant_ttc | VARCHAR | 6 | 0.12 | 803 | -1298.68 | 985.36 |
| canal | VARCHAR | 0 | 0.00 | 8 |  web | web |
| devise | VARCHAR | 0 | 0.00 | 2 | EUR | USD |

### Valeurs numériques (conversion tolérante)

| colonne | valeurs | min | p01 | médiane | p99 | max | moyenne | écart-type | extrêmes (3 IQR) |
|---|---|---|---|---|---|---|---|---|---|
| quantite | 5025 | 1.00 | 1.00 | 1.00 | 10.00 | 9 999.00 | 6.67 | 199.67 | 365 |
| prix_unitaire | 5025 | 29.46 | 29.46 | 940.13 | 2 430.97 | 2 430.97 | 978.81 | 702.48 | 0 |
| remise_pct | 5025 | 0.00 | 0.00 | 0.05 | 0.15 | 0.15 | 0.05 | 0.06 | 0 |
| montant_ttc | 5019 | -8 724.13 | 35.35 | 1 453.45 | 20 357.09 | 29 171.64 | 2 775.53 | 3 879.40 | 280 |

### Distributions principales

**canal**

| valeur | lignes | % |
|---|---|---|
| web | 1261 | 25.10 |
| partenaire | 1252 | 24.90 |
| telephone | 1250 | 24.90 |
| magasin | 1222 | 24.30 |
| Web | 14 | 0.30 |
| tel | 10 | 0.20 |
| WEB | 9 | 0.20 |
|  web | 7 | 0.10 |

**devise**

| valeur | lignes | % |
|---|---|---|
| EUR | 5022 | 99.90 |
| USD | 3 | 0.10 |

