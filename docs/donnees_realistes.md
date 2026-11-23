# Jeu de données réaliste

Généré par `scripts/generate_realistic_data.py` (graine 2026, résultat reproductible).
Les données sont **fictives** : aucune entreprise, aucun client réel. Mais elles suivent des
comportements qu'on retrouve chez un éditeur de logiciel B2B, ce qui permet de tester
l'assistant SQL et les rapports sur des questions qui ont une vraie réponse.

```powershell
python scripts/generate_realistic_data.py --force   # remplace data/raw (protégé sans --force)
python scripts/run_pipeline.py
```

## Ce qui est simulé

### Clients (1 200)
- 350 clients déjà présents avant 2025, puis 850 inscriptions sur la période,
  avec une croissance de l'acquisition (+60 % entre début et fin) et des creux en août et fin décembre.
- Segments : PME 45 %, Particulier 30 %, ETI 18 %, Grand compte 7 %. Villes pondérées (Paris 28 %).
- Churn mensuel par segment : Particulier 4 %, PME 2 %, ETI 1,2 %, Grand compte 0,6 %.
- 12 % des inscrits n'activent jamais le produit (ni achat, ni usage).
- Tailles de comptes très inégales : les 10 % premiers clients font environ 60 % du CA.

### Catalogue (40 produits)
Licences annuelles (Starter, Pro, Enterprise), modules, formations, support mensuel, matériel,
conseil au jour ou au forfait. Marges par catégorie : logiciel environ 80 %, support 60 %,
formation 40 %, conseil 27 %, matériel 11 %.

### Ventes (5 700)
- Licence initiale adaptée au segment (Starter pour particuliers et PME, Pro pour ETI,
  Enterprise pour grands comptes), puis **renouvelée chaque année** tant que le client reste.
- Achats complémentaires : conseil surtout chez les grands comptes, e-learning chez les particuliers.
- Saisonnalité : août creux, mars, juin, septembre et décembre forts.
- Remises : 5 % ETI, 10 % grands comptes, +5 % au-delà de 10 unités, opération en novembre.
- Canaux selon le segment : web pour les particuliers, partenaires et téléphone pour les grands comptes.
- Ventes en jours ouvrés (sauf une partie des achats web des particuliers).

### Usage de l'application (186 000 évènements)
- Sessions en jours ouvrés, aux heures de bureau. Activité plus forte les 3 premières semaines,
  plus faible après un an, en chute dans les 60 jours avant un départ.
- `invite_user` surtout au début, `create_report` et `share_report` plus fréquents avec l'ancienneté.
- Versions déployées progressivement (le web passe tout de suite, les applications avec retard) :
  - **3.2.0** (10/03/2025) : régression, erreurs E500, taux d'erreur multiplié par 2 à 3 ;
    corrigée par **3.2.1** (07/04/2025) ;
  - **4.0.0** (08/06/2026) : requêtes environ 1,7 fois plus lentes, erreurs TIMEOUT ;
    corrigée par **4.0.1** (13/07/2026), plus rapide que les versions 3.x.

### Support (1 080 tickets)
- Bug et Performance déclenchés par les erreurs (pics en mars-avril 2025 et juin-juillet 2026),
  Accès après les inscriptions, Facturation après les ventes, Questions au fil de l'usage.
- Délais médians par priorité : critique 4 h, haute 10 h, normale 28 h, basse 60 h,
  reportés au lundi le week-end pour normale et basse.
- Satisfaction qui baisse quand le délai dépasse la cible. Tickets récents parfois encore ouverts.

## Questions pour tester l'assistant

Les réponses ne sont pas données ici : la tendance attendue permet de juger si le résultat est plausible.

| question | ce qu'on doit voir |
|---|---|
| Quel est le CA HT par mois en 2026 ? | creux net en août |
| Quel segment génère le plus de CA HT, et avec quel taux de marge ? | grands comptes en tête, marge plus faible (conseil) |
| Quelle catégorie a le meilleur taux de marge ? | Logiciel |
| Quel est le taux d'erreur par version ? | 3.2.0 et 4.0.0 au-dessus des autres |
| Quelle est la durée médiane des requêtes par version ? | 4.0.0 la plus lente, 4.0.1 la plus rapide |
| Combien de tickets Performance par mois en 2026 ? | pic en juin et juillet |
| Comment évoluent les utilisateurs actifs mensuels ? | croissance, creux en août |
| Quelle part du CA HT vient des 10 % meilleurs clients ? | environ 60 % |
| Quel est le délai médian de résolution par priorité ? | critique le plus court, basse le plus long |
| Quels canaux utilisent les grands comptes ? | partenaire et téléphone, très peu de web |
| Combien de clients inscrits n'ont jamais rien acheté ? | une part non nulle (environ 12 % des inscrits) |
| Quel est le nombre de clients par ville ? | Paris largement en tête |

Commande : `python scripts/ask.py "<question>"`. Chaque réponse est enregistrée dans `reports/questions/`.

## Limites

- Un client = un utilisateur (`user_id` = `client_id`) : pas de comptes multi-utilisateurs.
- Pas d'abonnements ni de dates de résiliation explicites : le churn se voit dans l'arrêt des achats et de l'usage.
- Les clients déjà présents avant 2025 n'ont pas d'historique d'achat avant 2025.
