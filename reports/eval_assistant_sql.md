# Évaluation de l'assistant SQL

Exécutée le 2026-11-23 23:33 avec `claude-opus-5-5` (effort medium).

**6 / 6 réponses justes.** Durée totale 31 s, soit 5.2 s par question. Tokens : 16467 en entrée, 3147 en sortie.

| id | question | verdict | appels API | durée (s) | détail |
|---|---|---|---|---|---|
| Q13 | Quelle est la variation en pourcentage du CA HT entre septembre et octobre 2026 ? | juste | 1 | 5.71 | valeurs retrouvées |
| Q14 | Quelle part du CA HT 2025 vient du segment Grand compte, en pourcentage ? | juste | 1 | 4.76 | valeurs retrouvées |
| Q15 | Combien de clients ont acheté au moins une fois mais n'ont jamais ouvert de ticket ? | juste | 1 | 4.11 | valeurs retrouvées |
| Q16 | Quel est le taux d'erreur en 2026 sur la plateforme ios, en pourcentage des évènements ? | juste | 1 | 3.92 | valeurs retrouvées |
| Q17 | Quel est le CA HT cumulé mois par mois en 2026 ? | juste | 1 | 5.53 | valeurs retrouvées |
| Q18 | Quel est le nombre moyen de ventes par client acheteur en 2025 ? | juste | 1 | 7.2 | valeurs retrouvées |

Méthode : chaque valeur du résultat de la requête de référence (`config/questions_exemples.toml`) doit se retrouver dans le résultat de l'assistant, à 1 % près pour les nombres. Une question hors périmètre doit être refusée.
