-- Q6. Utilisateurs actifs mensuels (MAU) et taux d'erreur par mois
-- Source : v_usage_mensuel.
SELECT
    strftime(mois, '%Y-%m') AS mois,
    utilisateurs_actifs,
    nb_evenements,
    nb_erreurs,
    round(100.0 * nb_erreurs / nb_evenements, 2) AS taux_erreur_pct
FROM v_usage_mensuel
ORDER BY mois;
