-- staging_ventes
-- Hypothèse : prix_unitaire est HT, montant_ttc inclut une TVA de 20 %.
-- Règles de nettoyage :
--   V1  doublons exacts supprimés
--   V2  date : ISO ou JJ/MM/AAAA, sinon rejet
--   V3  montant_ttc : virgule convertie ; si vide, recalculé (montant_recalcule = true)
--   V4  canal : trim + minuscules, 'tel' devient 'telephone'
-- Règles de rejet (premier motif rencontré, ligne isolée dans la table rejets) :
--   R1  vente_id présent avec des contenus différents (toutes les versions isolées)
--   R2  date manquante ou non convertible
--   R3  client inconnu de staging_clients
--   R4  produit inconnu de staging_produits
--   R5  devise autre que EUR (pas de taux de change disponible)
--   R6  quantité hors plage 1 à 100
--   R7  montant négatif
--   R8  montant incohérent : écart > 0,05 avec quantite x prix x (1 - remise) x 1,2
CREATE OR REPLACE TEMP TABLE _ventes_controle AS
WITH dedup AS (                                                          -- V1
    SELECT DISTINCT
        vente_id, date_vente, client_id, produit_id, quantite,
        prix_unitaire, remise_pct, montant_ttc, canal, devise
    FROM raw_ventes
),
typed AS (
    SELECT
        d.*,
        count(*) OVER (PARTITION BY vente_id) AS nb_versions,
        coalesce(
            TRY_CAST(date_vente AS DATE),
            CAST(try_strptime(date_vente, '%d/%m/%Y') AS DATE)
        ) AS date_vente_typee,                                           -- V2
        TRY_CAST(quantite AS INTEGER) AS quantite_typee,
        TRY_CAST(prix_unitaire AS DECIMAL(12, 2)) AS prix_typee,
        TRY_CAST(remise_pct AS DECIMAL(5, 4)) AS remise_typee,
        TRY_CAST(replace(montant_ttc, ',', '.') AS DECIMAL(12, 2)) AS montant_ttc_lu,
        CASE lower(trim(canal)) WHEN 'tel' THEN 'telephone'
             ELSE lower(trim(canal)) END AS canal_norme                 -- V4
    FROM dedup d
),
calc AS (
    SELECT
        *,
        round(quantite_typee * prix_typee * (1 - remise_typee) * 1.2, 2) AS montant_ttc_theorique
    FROM typed
)
SELECT
    c.*,
    CASE
        WHEN nb_versions > 1                                   THEN 'R1 vente_id en conflit'
        WHEN date_vente_typee IS NULL                          THEN 'R2 date manquante ou invalide'
        WHEN NOT EXISTS (SELECT 1 FROM staging_clients s WHERE s.client_id = c.client_id)
                                                               THEN 'R3 client inconnu'
        WHEN NOT EXISTS (SELECT 1 FROM staging_produits p WHERE p.produit_id = c.produit_id)
                                                               THEN 'R4 produit inconnu'
        WHEN devise <> 'EUR'                                   THEN 'R5 devise non geree'
        WHEN quantite_typee NOT BETWEEN 1 AND 100              THEN 'R6 quantite hors plage'
        WHEN montant_ttc_lu < 0                                THEN 'R7 montant negatif'
        WHEN montant_ttc_lu IS NOT NULL
             AND abs(montant_ttc_lu - montant_ttc_theorique) > 0.05
                                                               THEN 'R8 montant incoherent'
    END AS motif_rejet
FROM calc c;

CREATE OR REPLACE TABLE staging_ventes AS
SELECT
    v.vente_id,
    v.date_vente_typee AS date_vente,
    v.client_id,
    v.produit_id,
    v.quantite_typee AS quantite,
    v.prix_typee AS prix_unitaire_ht,
    v.remise_typee AS remise_pct,
    coalesce(v.montant_ttc_lu, v.montant_ttc_theorique) AS montant_ttc,          -- V3
    round(coalesce(v.montant_ttc_lu, v.montant_ttc_theorique) / 1.2, 2) AS montant_ht,
    round(coalesce(v.montant_ttc_lu, v.montant_ttc_theorique) / 1.2
          - v.quantite_typee * p.cout_unitaire_ht, 2) AS marge_ht,
    v.montant_ttc_lu IS NULL AS montant_recalcule,
    v.canal_norme AS canal,
    v.devise
FROM _ventes_controle v
JOIN staging_produits p USING (produit_id)
WHERE v.motif_rejet IS NULL;

DELETE FROM rejets WHERE table_source = 'raw_ventes';
INSERT INTO rejets
SELECT
    'raw_ventes',
    vente_id,
    motif_rejet,
    to_json({
        vente_id: vente_id, date_vente: date_vente, client_id: client_id,
        produit_id: produit_id, quantite: quantite, prix_unitaire: prix_unitaire,
        remise_pct: remise_pct, montant_ttc: montant_ttc, canal: canal, devise: devise
    }),
    now()
FROM _ventes_controle
WHERE motif_rejet IS NOT NULL;

DROP TABLE _ventes_controle;
