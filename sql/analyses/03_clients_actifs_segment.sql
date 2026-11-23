-- Q3. Clients actifs, inactifs et sans achat par segment
-- Source : v_clients_statut (actif = achat dans les 90 jours avant la dernière vente connue).
-- Les clients signalés comme doublons probables (doublon_de non nul) sont exclus.
SELECT
    segment,
    count(*) AS nb_clients,
    count(*) FILTER (WHERE statut_achat = 'actif') AS actifs,
    count(*) FILTER (WHERE statut_achat = 'inactif') AS inactifs,
    count(*) FILTER (WHERE statut_achat = 'sans_achat') AS sans_achat,
    round(100.0 * count(*) FILTER (WHERE statut_achat = 'actif') / count(*), 1) AS taux_actifs_pct,
    round(sum(ca_ht) / nullif(count(*) FILTER (WHERE nb_achats > 0), 0), 2) AS ca_ht_moyen_par_acheteur
FROM v_clients_statut
WHERE doublon_de IS NULL
GROUP BY ROLLUP (segment)
ORDER BY segment NULLS LAST;
