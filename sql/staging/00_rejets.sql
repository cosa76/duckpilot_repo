-- Table commune des lignes isolées par la couche staging.
-- Chaque ligne rejetée garde sa clé, son motif et la ligne brute complète en JSON.
CREATE OR REPLACE TABLE rejets (
    table_source VARCHAR,
    cle          VARCHAR,
    motif        VARCHAR,
    ligne_brute  JSON,
    rejete_le    TIMESTAMP
);
