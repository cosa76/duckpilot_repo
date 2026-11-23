-- Q1. Chiffre d'affaires et marge par mois
-- Source : v_ventes_enrichies (ventes valides uniquement, montants HT).
SELECT
    strftime(mois, '%Y-%m') AS mois,
    count(*) AS nb_ventes,
    count(DISTINCT client_id) AS nb_clients,
    round(sum(montant_ht), 2) AS ca_ht,
    round(sum(marge_ht), 2) AS marge_ht,
    round(100 * sum(marge_ht) / sum(montant_ht), 1) AS taux_marge_pct
FROM v_ventes_enrichies
GROUP BY mois
ORDER BY mois;
