-- Support : tickets ouverts dans la semaine et la précédente, résolutions de la semaine.
WITH d AS (SELECT CAST(getvariable('debut') AS DATE) AS debut)
SELECT
    priorite,
    count(*) FILTER (WHERE date_ouverture >= d.debut AND date_ouverture < d.debut + INTERVAL 7 DAY)
        AS ouverts_semaine,
    count(*) FILTER (WHERE date_ouverture >= d.debut - INTERVAL 7 DAY AND date_ouverture < d.debut)
        AS ouverts_semaine_precedente,
    count(*) FILTER (WHERE date_resolution >= d.debut AND date_resolution < d.debut + INTERVAL 7 DAY)
        AS resolus_semaine,
    round(median(delai_resolution_h) FILTER (
        WHERE date_resolution >= d.debut AND date_resolution < d.debut + INTERVAL 7 DAY), 1)
        AS delai_median_h,
    round(avg(satisfaction) FILTER (
        WHERE date_resolution >= d.debut AND date_resolution < d.debut + INTERVAL 7 DAY), 2)
        AS satisfaction_moyenne
FROM staging_tickets, d
GROUP BY ROLLUP (priorite)
ORDER BY CASE priorite WHEN 'critique' THEN 1 WHEN 'haute' THEN 2 WHEN 'normale' THEN 3
                       WHEN 'basse' THEN 4 WHEN 'non_renseignee' THEN 5 ELSE 6 END;
