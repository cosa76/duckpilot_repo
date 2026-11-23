-- Q2. Chiffre d'affaires et marge par catégorie de produit et canal
-- Source : v_ventes_enrichies. Part = part du CA HT total.
SELECT
    categorie,
    canal,
    count(*) AS nb_ventes,
    round(sum(montant_ht), 2) AS ca_ht,
    round(sum(marge_ht), 2) AS marge_ht,
    round(100 * sum(marge_ht) / sum(montant_ht), 1) AS taux_marge_pct,
    round(100 * sum(montant_ht) / sum(sum(montant_ht)) OVER (), 1) AS part_ca_pct
FROM v_ventes_enrichies
GROUP BY categorie, canal
ORDER BY ca_ht DESC;
