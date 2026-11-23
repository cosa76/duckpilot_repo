-- staging_produits
-- Règles :
--   P1  prix et coût : virgule décimale convertie, typage DECIMAL(12,2)
--   P2  categorie : première lettre en majuscule
--   P3  cout_superieur_prix = true si le coût dépasse le prix (produit gardé, signalé)
CREATE OR REPLACE TABLE staging_produits AS
SELECT
    produit_id,
    libelle,
    upper(trim(categorie)[1]) || lower(trim(categorie)[2:]) AS categorie,          -- P2
    CAST(replace(prix_unitaire, ',', '.') AS DECIMAL(12, 2)) AS prix_unitaire_ht,  -- P1
    CAST(replace(cout_unitaire, ',', '.') AS DECIMAL(12, 2)) AS cout_unitaire_ht,
    CAST(replace(cout_unitaire, ',', '.') AS DECIMAL(12, 2))
        > CAST(replace(prix_unitaire, ',', '.') AS DECIMAL(12, 2)) AS cout_superieur_prix  -- P3
FROM raw_produits;
