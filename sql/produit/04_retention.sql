-- Rétention et utilisateurs à risque.
--   retenus   : actifs la semaine précédente et cette semaine
--   a_risque  : actifs dans les 4 semaines précédentes, absents cette semaine
--   nouveaux  : premier évènement de leur historique dans la semaine
WITH actifs AS (
    SELECT DISTINCT user_id, CAST(date_trunc('week', event_date) AS DATE) AS semaine
    FROM staging_evenements
    WHERE event_name <> 'logout'
),
d AS (SELECT CAST(getvariable('debut') AS DATE) AS debut),
cette AS (SELECT user_id FROM actifs, d WHERE semaine = d.debut),
prec AS (SELECT user_id FROM actifs, d WHERE semaine = d.debut - INTERVAL 7 DAY),
quatre AS (
    SELECT DISTINCT user_id FROM actifs, d
    WHERE semaine >= d.debut - INTERVAL 28 DAY AND semaine < d.debut
),
premier AS (SELECT user_id, min(event_date) AS premier_evt FROM staging_evenements GROUP BY 1)
SELECT
    (SELECT count(*) FROM prec) AS actifs_semaine_precedente,
    (SELECT count(*) FROM prec SEMI JOIN cette USING (user_id)) AS retenus,
    round(100.0 * (SELECT count(*) FROM prec SEMI JOIN cette USING (user_id))
          / nullif((SELECT count(*) FROM prec), 0), 1) AS retention_hebdo_pct,
    (SELECT count(*) FROM quatre ANTI JOIN cette USING (user_id)) AS a_risque,
    (SELECT count(*) FROM premier, d
     WHERE premier_evt >= d.debut AND premier_evt < d.debut + INTERVAL 7 DAY) AS nouveaux;
