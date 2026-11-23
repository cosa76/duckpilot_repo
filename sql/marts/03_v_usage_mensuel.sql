-- v_usage_mensuel : activité produit par mois.
-- Utilisateur actif = au moins un évènement dans le mois (hors logout).
CREATE OR REPLACE VIEW v_usage_mensuel AS
SELECT
    date_trunc('month', event_date) AS mois,
    count(DISTINCT user_id) FILTER (WHERE event_name <> 'logout') AS utilisateurs_actifs,
    count(*) AS nb_evenements,
    count(*) FILTER (WHERE event_name = 'error') AS nb_erreurs,
    count(*) FILTER (WHERE event_name = 'run_query') AS nb_requetes,
    count(*) FILTER (WHERE event_name = 'create_report') AS nb_rapports_crees
FROM staging_evenements
GROUP BY ALL;
