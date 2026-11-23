-- Usage des fonctionnalités : part de chaque type d'évènement, semaine analysée et précédente.
WITH base AS (
    SELECT
        event_name,
        CASE WHEN event_date >= CAST(getvariable('debut') AS DATE) THEN 'semaine' ELSE 'precedente' END AS periode
    FROM staging_evenements
    WHERE event_date >= CAST(getvariable('debut') AS DATE) - INTERVAL 7 DAY
      AND event_date < CAST(getvariable('debut') AS DATE) + INTERVAL 7 DAY
      AND event_name NOT IN ('login', 'logout', 'error')
)
SELECT
    event_name AS fonctionnalite,
    count(*) FILTER (WHERE periode = 'semaine') AS utilisations,
    round(100.0 * count(*) FILTER (WHERE periode = 'semaine')
          / sum(count(*) FILTER (WHERE periode = 'semaine')) OVER (), 1) AS part_pct,
    count(*) FILTER (WHERE periode = 'precedente') AS utilisations_semaine_precedente
FROM base
GROUP BY event_name
ORDER BY utilisations DESC;
