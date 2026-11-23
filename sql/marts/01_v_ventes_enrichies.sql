-- v_ventes_enrichies : une ligne par vente valide, avec client et produit.
-- Source : staging_ventes, staging_clients, staging_produits.
CREATE OR REPLACE VIEW v_ventes_enrichies AS
SELECT
    v.vente_id,
    v.date_vente,
    date_trunc('month', v.date_vente) AS mois,
    v.client_id,
    c.segment,
    c.ville,
    v.produit_id,
    p.libelle AS produit,
    p.categorie,
    v.canal,
    v.quantite,
    v.remise_pct,
    v.montant_ht,
    v.montant_ttc,
    v.marge_ht
FROM staging_ventes v
JOIN staging_clients c USING (client_id)
JOIN staging_produits p USING (produit_id);
