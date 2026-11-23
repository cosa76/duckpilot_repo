-- Q4. Incidents support et délai de résolution par priorité
-- Source : staging_tickets. Le délai n'est calculé que pour les tickets
-- résolus ou fermés sans anomalie de dates.
SELECT
    priorite,
    count(*) AS nb_tickets,
    count(*) FILTER (WHERE statut IN ('ouvert', 'en_cours')) AS non_resolus,
    count(delai_resolution_h) AS avec_delai,
    round(median(delai_resolution_h), 1) AS delai_median_h,
    round(avg(delai_resolution_h), 1) AS delai_moyen_h,
    round(quantile_cont(delai_resolution_h, 0.9), 1) AS delai_p90_h,
    round(avg(satisfaction), 2) AS satisfaction_moyenne,
    count(satisfaction) AS nb_notes
FROM staging_tickets
GROUP BY ROLLUP (priorite)
ORDER BY
    CASE priorite WHEN 'critique' THEN 1 WHEN 'haute' THEN 2 WHEN 'normale' THEN 3
                  WHEN 'basse' THEN 4 WHEN 'non_renseignee' THEN 5 ELSE 6 END;
