-- Segments de clients (hors doublons probables) à la fin de la semaine analysée.
--   payant      : au moins un achat dans les 90 jours avant la fin de semaine
--   actif_usage : au moins un évènement (hors logout) dans la semaine
WITH d AS (
    SELECT CAST(getvariable('debut') AS DATE) AS debut,
           CAST(getvariable('debut') AS DATE) + INTERVAL 7 DAY AS fin
),
payants AS (
    SELECT DISTINCT client_id FROM staging_ventes, d
    WHERE date_vente >= d.fin - INTERVAL 90 DAY AND date_vente < d.fin
),
usage AS (
    SELECT DISTINCT user_id AS client_id FROM staging_evenements, d
    WHERE event_date >= d.debut AND event_date < d.fin AND event_name <> 'logout'
),
c AS (
    SELECT
        s.segment,
        s.client_id IN (SELECT client_id FROM payants) AS payant,
        s.client_id IN (SELECT client_id FROM usage) AS actif_usage
    FROM staging_clients s
    WHERE s.doublon_de IS NULL
)
SELECT
    segment,
    count(*) AS clients,
    count(*) FILTER (WHERE actif_usage) AS actifs_usage,
    count(*) FILTER (WHERE payant) AS payants,
    count(*) FILTER (WHERE payant AND NOT actif_usage) AS payants_sans_usage
FROM c
GROUP BY ROLLUP (segment)
ORDER BY segment NULLS LAST;
