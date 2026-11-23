-- Ventes par semaine : k = 0 semaine analysée, k = 1 précédente, k = 1 à 8 pour la moyenne.
WITH semaines AS (
    SELECT k, CAST(getvariable('debut') AS DATE) - INTERVAL (7 * k) DAY AS debut
    FROM range(0, 9) t(k)
)
SELECT
    s.k,
    count(v.vente_id) AS ventes,
    count(DISTINCT v.client_id) AS clients_acheteurs,
    round(coalesce(sum(v.montant_ht), 0), 2) AS ca_ht,
    round(coalesce(sum(v.marge_ht), 0), 2) AS marge_ht
FROM semaines s
LEFT JOIN staging_ventes v
       ON v.date_vente >= s.debut AND v.date_vente < s.debut + INTERVAL 7 DAY
GROUP BY s.k
ORDER BY s.k;
