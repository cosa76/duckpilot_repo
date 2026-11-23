-- Erreurs par version de l'application sur la semaine analysée.
SELECT
    app_version AS version,
    count(*) AS evenements,
    count(*) FILTER (WHERE event_name = 'error') AS erreurs,
    round(100.0 * count(*) FILTER (WHERE event_name = 'error') / count(*), 2) AS taux_erreur_pct,
    string_agg(DISTINCT code_erreur, ', ' ORDER BY code_erreur) FILTER (WHERE code_erreur IS NOT NULL)
        AS codes_erreur
FROM staging_evenements
WHERE event_date >= CAST(getvariable('debut') AS DATE)
  AND event_date < CAST(getvariable('debut') AS DATE) + INTERVAL 7 DAY
GROUP BY app_version
ORDER BY app_version;
