# Anomalies injectées dans les données

Les fichiers de `data/raw/` sont fictifs (domaine `exemple.test`). Ce fichier sert de vérité
terrain : le profil qualité et les contrôles doivent retrouver ces anomalies.

Jeu actuel : `scripts/generate_realistic_data.py` (graine 2026), depuis le 23/11/2026.
Les comportements simulés sont décrits dans `docs/donnees_realistes.md`.
L'ancien jeu uniforme (`scripts/generate_synthetic_data.py`, graine 42) reste disponible.

## Fichiers

| fichier | format | table raw | lignes |
|---|---|---|---|
| ventes.csv | CSV séparateur `,` | raw_ventes | 5 757 |
| produits.csv | CSV séparateur `;`, décimale `,` | raw_produits | 40 |
| clients.xlsx | Excel, feuille `clients` | raw_clients | 1 203 |
| evenements.jsonl | JSON lignes, objet imbriqué `proprietes` | raw_evenements | 186 600 |
| tickets.parquet | Parquet typé | raw_tickets | 1 081 |

## Anomalies du jeu actuel (comptées par `reports/profil_qualite_raw.md`)

**Ventes** : 86 dates au format `JJ/MM/AAAA`, 3 dates impossibles (`2025-02-30`), 6 dates vides,
12 montants négatifs, 6 montants vides, 17 montants avec virgule décimale, 4 quantités extrêmes
(500, 1 200 ou 9 999), 15 clients inexistants, 5 produits inexistants (`P999`), 28 canaux
non normalisés (`Web`, `WEB`, ` web`, `tel`), 3 ventes en USD, 30 lignes en double exact,
6 `vente_id` réutilisés avec une quantité différente.

**Clients** : 12 emails vides, 6 emails invalides, 6 villes mal écrites, 2 segments vides,
1 date d'inscription future, 2 personnes inscrites sous deux identifiants, 1 ligne en double exact.

**Évènements** : 186 `user_id` vides (0,1 %), 10 horodatages futurs, 93 horodatages en epoch texte,
93 `event_name` en majuscules, 37 versions absentes, 5 durées aberrantes (24 h),
372 évènements envoyés deux fois.

**Tickets** : 6 résolus avant leur ouverture, 4 `ouvert` avec une date de résolution,
5 satisfactions hors échelle, 6 priorités vides, 8 descriptions contenant un téléphone et un email,
4 lignes en double exact.

**Produits** : aucune anomalie dans ce jeu (le jeu uniforme avait un coût supérieur au prix).
