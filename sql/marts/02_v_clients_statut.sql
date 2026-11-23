-- v_clients_statut : une ligne par client avec son historique d'achat et son statut.
-- Date de référence : dernière date de vente présente dans les données
-- (et non la date du jour, pour que l'analyse reste stable).
-- Statuts :
--   actif         achat dans les 90 jours précédant la date de référence
--   inactif       a déjà acheté, mais pas dans les 90 derniers jours
--   sans_achat    aucun achat valide
CREATE OR REPLACE VIEW v_clients_statut AS
WITH ref AS (
    SELECT max(date_vente) AS date_reference FROM staging_ventes
),
achats AS (
    SELECT
        client_id,
        min(date_vente) AS premier_achat,
        max(date_vente) AS dernier_achat,
        count(*) AS nb_achats,
        sum(montant_ht) AS ca_ht
    FROM staging_ventes
    GROUP BY client_id
)
SELECT
    c.client_id,
    c.segment,
    c.ville,
    c.date_inscription,
    c.doublon_de,
    a.premier_achat,
    a.dernier_achat,
    coalesce(a.nb_achats, 0) AS nb_achats,
    coalesce(a.ca_ht, 0) AS ca_ht,
    ref.date_reference,
    CASE
        WHEN a.dernier_achat IS NULL THEN 'sans_achat'
        WHEN a.dernier_achat > ref.date_reference - INTERVAL 90 DAY THEN 'actif'
        ELSE 'inactif'
    END AS statut_achat
FROM staging_clients c
CROSS JOIN ref
LEFT JOIN achats a USING (client_id);
