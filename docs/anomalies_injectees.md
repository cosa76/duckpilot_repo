# Anomalies injectées dans les données synthétiques

Les fichiers de `data/raw/` sont générés par `scripts/generate_synthetic_data.py`
(graine fixe 42, résultat reproductible). Toutes les personnes, emails et
téléphones sont fictifs (domaine `exemple.test`).

Ce fichier sert de vérité terrain : le profil qualité et les futurs contrôles
doivent retrouver ces anomalies.

## Fichiers

| fichier | format | table raw | lignes | particularités |
|---|---|---|---|---|
| ventes.csv | CSV séparateur `,` | raw_ventes | 5 025 | lu en texte |
| produits.csv | CSV séparateur `;`, décimale `,` | raw_produits | 40 | lu en texte |
| clients.xlsx | Excel, feuille `clients` | raw_clients | 502 | lu via pandas, en texte |
| evenements.jsonl | JSON lignes, objet imbriqué `proprietes` | raw_evenements | 20 050 | lu en texte, `proprietes` en JSON |
| tickets.parquet | Parquet typé | raw_tickets | 803 | types conservés |

## Ventes

- 150 dates au format `JJ/MM/AAAA` au lieu d'ISO.
- 3 dates impossibles (`2025-02-30`), 8 dates vides.
- 10 montants négatifs, 6 montants vides, 30 montants avec virgule décimale.
- 4 quantités extrêmes (500, 1 200 ou 9 999), montant non recalculé.
- 15 `client_id` inexistants, 5 `produit_id` inexistants (`P999`).
- 40 canaux non normalisés (`Web`, `WEB`, ` web`, `tel`).
- 3 ventes en `USD`.
- 20 lignes en double exact, 5 `vente_id` réutilisés avec une quantité différente.

## Produits

- 1 produit dont le coût dépasse le prix.
- 1 catégorie en minuscules (`logiciel`).

## Clients

- 5 emails vides, 3 emails invalides.
- 2 villes mal écrites (`paris `, `LYON`), 1 segment vide.
- 1 date d'inscription dans le futur.
- 1 même personne sous deux `client_id`, 1 ligne en double exact.

## Évènements

- 30 `user_id` vides.
- 10 timestamps dans le futur, 10 timestamps en epoch texte.
- 15 `event_name` en majuscules.
- 5 `app_version` absentes.
- 3 durées aberrantes (24 h).
- 50 évènements renvoyés deux fois (doublons exacts).

## Tickets

- Jusqu'à 6 tickets résolus avant leur ouverture (4 effectifs).
- 3 tickets `ouvert` avec une date de résolution.
- 4 satisfactions hors échelle 1 à 5, 5 priorités vides.
- 4 descriptions contenant un téléphone et un email (PII en texte libre).
- 3 lignes en double exact.
