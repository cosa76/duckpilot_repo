-- staging_clients
-- Règles :
--   C1  doublons exacts supprimés (une ligne gardée)
--   C2  PII retirées : prenom, nom, telephone non repris ; email remplacé par
--       email_hash (md5 du minuscule) et email_domaine
--   C3  email invalide : email_hash et email_domaine à NULL, email_valide = false
--   C4  ville : trim puis première lettre en majuscule
--   C5  segment vide : 'Inconnu'
--   C6  date_inscription future : mise à NULL, date_inscription_invalide = true
--   C7  même email sur plusieurs client_id : doublon_de = plus petit client_id
--       portant cet email (la ligne est gardée, on ne fusionne pas sans validation)
CREATE OR REPLACE TABLE staging_clients AS
WITH dedup AS (                                            -- C1
    SELECT DISTINCT
        client_id, email, ville, segment, date_inscription, actif
    FROM raw_clients
),
typed AS (
    SELECT
        client_id,
        lower(trim(email)) AS email_norm,
        regexp_matches(coalesce(email, ''), '^[^@\s]+@[^@\s]+\.[^@\s]+$') AS email_valide,
        upper(trim(ville)[1]) || lower(trim(ville)[2:]) AS ville,          -- C4
        coalesce(segment, 'Inconnu') AS segment,                           -- C5
        TRY_CAST(date_inscription AS DATE) AS date_inscription_brute,
        lower(actif) = 'true' AS actif
    FROM dedup
)
SELECT
    client_id,
    CASE WHEN email_valide THEN md5(email_norm) END AS email_hash,           -- C2, C3
    CASE WHEN email_valide THEN split_part(email_norm, '@', 2) END AS email_domaine,
    email_valide,
    ville,
    segment,
    CASE WHEN date_inscription_brute <= current_date
         THEN date_inscription_brute END AS date_inscription,               -- C6
    coalesce(date_inscription_brute > current_date, false) AS date_inscription_invalide,
    actif,
    CASE WHEN email_valide
              AND min(client_id) OVER (PARTITION BY email_norm) <> client_id
         THEN min(client_id) OVER (PARTITION BY email_norm) END AS doublon_de  -- C7
FROM typed;
