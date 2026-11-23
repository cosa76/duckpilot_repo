-- staging_tickets
-- Aucun ticket n'est rejeté : chaque ticket compte comme incident.
-- Règles :
--   T1  doublons exacts supprimés
--   T2  priorite vide : 'non_renseignee'
--   T3  satisfaction hors 1 à 5 : NULL
--   T4  date_resolution antérieure à date_ouverture : NULL, anomalie = 'resolution_avant_ouverture'
--   T5  statut ouvert ou en_cours avec date_resolution : date gardée,
--       anomalie = 'statut_incoherent', délai non calculé
--   T6  delai_resolution_h calculé seulement pour les statuts resolu et ferme sans anomalie
--   T7  description : emails et téléphones masqués
CREATE OR REPLACE TABLE staging_tickets AS
WITH dedup AS (                                                        -- T1
    SELECT DISTINCT
        ticket_id, client_id, date_ouverture, date_resolution, categorie,
        priorite, statut, satisfaction, description
    FROM raw_tickets
),
flagged AS (
    SELECT
        *,
        CASE
            WHEN date_resolution < date_ouverture THEN 'resolution_avant_ouverture'   -- T4
            WHEN statut IN ('ouvert', 'en_cours') AND date_resolution IS NOT NULL
                 THEN 'statut_incoherent'                                           -- T5
        END AS anomalie
    FROM dedup
)
SELECT
    ticket_id,
    client_id,
    date_ouverture,
    CASE WHEN anomalie = 'resolution_avant_ouverture' THEN NULL
         ELSE date_resolution END AS date_resolution,
    categorie,
    coalesce(priorite, 'non_renseignee') AS priorite,                  -- T2
    statut,
    CASE WHEN satisfaction BETWEEN 1 AND 5 THEN satisfaction END AS satisfaction,  -- T3
    CASE WHEN anomalie IS NULL AND statut IN ('resolu', 'ferme')
         THEN round(date_diff('second', date_ouverture, date_resolution) / 3600.0, 2)
    END AS delai_resolution_h,                                         -- T6
    anomalie,
    regexp_replace(
        regexp_replace(description, '[^@\s]+@[^@\s]+', '[email]', 'g'),
        '0\d([ .]?\d{2}){4}', '[telephone]', 'g'
    ) AS description                                                   -- T7
FROM flagged;
