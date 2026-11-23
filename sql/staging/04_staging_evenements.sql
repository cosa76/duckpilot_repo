-- staging_evenements
-- Règles de nettoyage :
--   E1  doublons exacts supprimés
--   E2  timestamp : ISO, ou epoch en secondes interprété en UTC
--       (l'heure exacte peut être décalée d'une à deux heures pour ces lignes)
--   E3  event_name en minuscules
--   E4  app_version absente : 'inconnue'
--   E5  propriétés JSON extraites en colonnes (session_id, duree_ms, code_erreur, nb_lignes)
--   E6  duree_ms > 1 h (3 600 000 ms) : mise à NULL, duree_aberrante = true
-- Règles de rejet :
--   R1  user_id manquant
--   R2  timestamp non convertible
--   R3  timestamp postérieur à la date de chargement
CREATE OR REPLACE TEMP TABLE _evenements_controle AS
WITH dedup AS (                                                        -- E1
    SELECT DISTINCT
        event_id, user_id, event_name, "timestamp", app_version, plateforme,
        CAST(proprietes AS VARCHAR) AS proprietes
    FROM raw_evenements
),
typed AS (
    SELECT
        d.*,
        coalesce(
            TRY_CAST("timestamp" AS TIMESTAMP),
            CASE WHEN regexp_matches("timestamp", '^\d{9,10}$')
                 THEN make_timestamp(CAST("timestamp" AS BIGINT) * 1000000) END
        ) AS ts                                                        -- E2
    FROM dedup d
)
SELECT
    *,
    CASE
        WHEN user_id IS NULL THEN 'R1 user_id manquant'
        WHEN ts IS NULL      THEN 'R2 timestamp invalide'
        WHEN ts > now()      THEN 'R3 timestamp futur'
    END AS motif_rejet
FROM typed;

CREATE OR REPLACE TABLE staging_evenements AS
SELECT
    event_id,
    user_id,
    lower(event_name) AS event_name,                                   -- E3
    ts AS event_ts,
    CAST(ts AS DATE) AS event_date,
    regexp_matches("timestamp", '^\d{9,10}$') AS ts_depuis_epoch,
    coalesce(app_version, 'inconnue') AS app_version,                  -- E4
    plateforme,
    json_extract_string(proprietes, '$.session_id') AS session_id,     -- E5
    CASE WHEN TRY_CAST(json_extract_string(proprietes, '$.duree_ms') AS BIGINT) <= 3600000
         THEN TRY_CAST(json_extract_string(proprietes, '$.duree_ms') AS BIGINT) END AS duree_ms,
    coalesce(TRY_CAST(json_extract_string(proprietes, '$.duree_ms') AS BIGINT) > 3600000,
             false) AS duree_aberrante,                                -- E6
    json_extract_string(proprietes, '$.code') AS code_erreur,
    TRY_CAST(json_extract_string(proprietes, '$.nb_lignes') AS BIGINT) AS nb_lignes
FROM _evenements_controle
WHERE motif_rejet IS NULL;

DELETE FROM rejets WHERE table_source = 'raw_evenements';
INSERT INTO rejets
SELECT
    'raw_evenements',
    event_id,
    motif_rejet,
    to_json({
        event_id: event_id, user_id: user_id, event_name: event_name,
        "timestamp": "timestamp", app_version: app_version, plateforme: plateforme,
        proprietes: proprietes
    }),
    now()
FROM _evenements_controle
WHERE motif_rejet IS NOT NULL;

DROP TABLE _evenements_controle;
