-- Q5. Usage et taux d'erreur par version de l'application
-- Source : staging_evenements. Taux d'erreur = évènements 'error' / tous les évènements.
SELECT
    app_version,
    count(DISTINCT user_id) AS utilisateurs,
    count(*) AS nb_evenements,
    count(*) FILTER (WHERE event_name = 'error') AS nb_erreurs,
    round(100.0 * count(*) FILTER (WHERE event_name = 'error') / count(*), 2) AS taux_erreur_pct,
    round(median(duree_ms) FILTER (WHERE event_name = 'run_query'), 0) AS duree_requete_mediane_ms
FROM staging_evenements
GROUP BY app_version
ORDER BY app_version;
