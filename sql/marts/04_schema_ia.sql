-- Schéma ia : seul périmètre interrogeable par l'assistant SQL (scripts/ask.py).
-- Vues en lecture, sans données personnelles ni texte libre.
-- Toute colonne ajoutée ici doit être décrite dans config/catalogue_ia.toml.
CREATE SCHEMA IF NOT EXISTS ia;

CREATE OR REPLACE VIEW ia.ventes AS
SELECT
    vente_id,
    date_vente,
    mois,
    client_id,
    segment,
    ville,
    produit_id,
    produit,
    categorie,
    canal,
    quantite,
    remise_pct,
    montant_ht,
    montant_ttc,
    marge_ht
FROM main.v_ventes_enrichies;

CREATE OR REPLACE VIEW ia.clients AS
SELECT
    client_id,
    segment,
    ville,
    date_inscription,
    premier_achat,
    dernier_achat,
    nb_achats,
    ca_ht,
    statut_achat,
    doublon_de IS NOT NULL AS doublon_probable
FROM main.v_clients_statut;

CREATE OR REPLACE VIEW ia.produits AS
SELECT
    produit_id,
    libelle,
    categorie,
    prix_unitaire_ht,
    cout_unitaire_ht
FROM main.staging_produits;

CREATE OR REPLACE VIEW ia.evenements AS
SELECT
    event_id,
    user_id,
    event_name,
    event_ts,
    event_date,
    app_version,
    plateforme,
    session_id,
    duree_ms,
    code_erreur,
    nb_lignes
FROM main.staging_evenements;

CREATE OR REPLACE VIEW ia.usage_mensuel AS
SELECT
    mois,
    utilisateurs_actifs,
    nb_evenements,
    nb_erreurs,
    nb_requetes,
    nb_rapports_crees
FROM main.v_usage_mensuel;

-- La description des tickets (texte libre) est volontairement exclue.
CREATE OR REPLACE VIEW ia.tickets AS
SELECT
    ticket_id,
    client_id,
    date_ouverture,
    date_resolution,
    categorie,
    priorite,
    statut,
    satisfaction,
    delai_resolution_h
FROM main.staging_tickets;
