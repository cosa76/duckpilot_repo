-- Activité par semaine : k = 0 semaine analysée, k = 1 semaine précédente, k = 1 à 8 pour la moyenne.
-- Variable : debut (lundi de la semaine analysée).
WITH semaines AS (
    SELECT k, CAST(getvariable('debut') AS DATE) - INTERVAL (7 * k) DAY AS debut
    FROM range(0, 9) t(k)
)
SELECT
    s.k,
    count(DISTINCT e.user_id) FILTER (WHERE e.event_name <> 'logout') AS utilisateurs_actifs,
    round(count(DISTINCT (e.event_date, e.user_id)) FILTER (WHERE e.event_name <> 'logout') / 7.0, 1)
        AS utilisateurs_actifs_jour_moyen,
    count(e.event_id) AS evenements,
    count(e.event_id) FILTER (WHERE e.event_name = 'run_query') AS requetes,
    count(e.event_id) FILTER (WHERE e.event_name = 'create_report') AS rapports_crees,
    count(e.event_id) FILTER (WHERE e.event_name = 'export_csv') AS exports,
    count(e.event_id) FILTER (WHERE e.event_name = 'error') AS erreurs,
    round(100.0 * count(e.event_id) FILTER (WHERE e.event_name = 'error')
          / nullif(count(e.event_id), 0), 2) AS taux_erreur_pct,
    round(median(e.duree_ms) FILTER (WHERE e.event_name = 'run_query'), 0) AS duree_requete_mediane_ms
FROM semaines s
LEFT JOIN staging_evenements e
       ON e.event_date >= s.debut AND e.event_date < s.debut + INTERVAL 7 DAY
GROUP BY s.k
ORDER BY s.k;
