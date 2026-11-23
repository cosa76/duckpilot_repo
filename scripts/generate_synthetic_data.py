"""Génère un jeu de données synthétiques dans data/raw/.

Toutes les personnes, emails et montants sont fictifs.
Des anomalies réalistes sont injectées volontairement pour tester
le profil et les contrôles qualité (voir docs/anomalies_injectees.md).

Usage : python scripts/generate_synthetic_data.py
Le résultat est reproductible (graine fixe).
"""

from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

N_CLIENTS = 500
N_PRODUITS = 40
N_VENTES = 5000
N_EVENEMENTS = 20000
N_TICKETS = 800

DEBUT = date(2025, 1, 1)
FIN = date(2026, 10, 31)

PRENOMS = ["Alice", "Bruno", "Chloé", "David", "Emma", "Farid", "Gaëlle", "Hugo",
           "Inès", "Julien", "Karim", "Léa", "Mathis", "Nadia", "Olivier", "Pauline",
           "Quentin", "Rania", "Samuel", "Théo", "Ulysse", "Valérie", "Yanis", "Zoé"]
NOMS = ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit",
        "Durand", "Leroy", "Moreau", "Simon", "Laurent", "Lefebvre", "Michel",
        "Garcia", "Diallo", "Nguyen", "Mbaye", "Rossi", "Fontaine"]
VILLES = ["Paris", "Lyon", "Marseille", "Toulouse", "Nantes", "Lille", "Bordeaux",
          "Strasbourg", "Rennes", "Montpellier"]
SEGMENTS = ["PME", "ETI", "Grand compte", "Particulier"]
CANAUX = ["web", "magasin", "telephone", "partenaire"]
CATEGORIES = ["Logiciel", "Formation", "Support", "Materiel", "Conseil"]
EVENTS = ["login", "view_dashboard", "run_query", "export_csv", "create_report",
          "share_report", "invite_user", "error", "logout"]
EVENT_WEIGHTS = [20, 25, 22, 8, 7, 4, 2, 5, 7]
PLATEFORMES = ["web", "windows", "macos", "ios", "android"]
VERSIONS = ["3.1.0", "3.2.0", "3.2.1", "3.3.0", "4.0.0"]
TICKET_CATS = ["Bug", "Facturation", "Acces", "Question", "Performance"]
PRIORITES = ["basse", "normale", "haute", "critique"]
STATUTS = ["ouvert", "en_cours", "resolu", "ferme"]


def rand_date(rng: random.Random, start: date = DEBUT, end: date = FIN) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def strip_accents(s: str) -> str:
    table = str.maketrans("éèêëàâäîïôöùûüç", "eeeeaaaiioouuuc")
    return s.lower().translate(table)


def gen_clients(rng: random.Random) -> pd.DataFrame:
    rows = []
    for i in range(1, N_CLIENTS + 1):
        prenom, nom = rng.choice(PRENOMS), rng.choice(NOMS)
        rows.append({
            "client_id": f"C{i:05d}",
            "prenom": prenom,
            "nom": nom,
            "email": f"{strip_accents(prenom)}.{strip_accents(nom)}{i}@exemple.test",
            "telephone": f"06{rng.randint(10000000, 99999999)}",
            "ville": rng.choice(VILLES),
            "segment": rng.choice(SEGMENTS),
            "date_inscription": rand_date(rng, DEBUT, date(2026, 6, 30)),
            "actif": rng.random() > 0.15,
        })
    df = pd.DataFrame(rows)

    # Anomalies
    idx = rng.sample(range(N_CLIENTS), 12)
    df.loc[idx[:5], "email"] = None                                   # emails manquants
    df.loc[idx[5:8], "email"] = ["pas_un_email", "jean@", "@exemple.test"]  # emails invalides
    df.loc[idx[8:10], "ville"] = ["paris ", "LYON"]                   # casse / espaces
    df.loc[idx[10], "segment"] = None
    df.loc[idx[11], "date_inscription"] = date(2027, 3, 1)            # date future
    # Doublon de client (même personne, deux identifiants)
    dup = df.iloc[[3]].copy()
    dup["client_id"] = f"C{N_CLIENTS + 1:05d}"
    # Doublon exact de ligne
    df = pd.concat([df, dup, df.iloc[[10]]], ignore_index=True)
    df["date_inscription"] = pd.to_datetime(df["date_inscription"])
    return df


def gen_produits(rng: random.Random) -> pd.DataFrame:
    rows = []
    for i in range(1, N_PRODUITS + 1):
        cat = rng.choice(CATEGORIES)
        prix = round(rng.uniform(20, 2500), 2)
        cout = round(prix * rng.uniform(0.3, 0.8), 2)
        rows.append({"produit_id": f"P{i:03d}", "libelle": f"{cat} {i:03d}",
                     "categorie": cat, "prix_unitaire": prix, "cout_unitaire": cout})
    df = pd.DataFrame(rows)
    df.loc[7, "cout_unitaire"] = df.loc[7, "prix_unitaire"] * 1.2     # coût > prix
    df.loc[15, "categorie"] = "logiciel"                              # casse
    return df


def gen_ventes(rng: random.Random, clients: pd.DataFrame, produits: pd.DataFrame) -> pd.DataFrame:
    client_ids = clients["client_id"].unique().tolist()
    prix = dict(zip(produits["produit_id"], produits["prix_unitaire"]))
    rows = []
    for i in range(1, N_VENTES + 1):
        pid = rng.choice(list(prix))
        qte = rng.choices([1, 2, 3, 5, 10], weights=[50, 20, 12, 10, 8])[0]
        remise = rng.choice([0, 0, 0, 0.05, 0.1, 0.15])
        d = rand_date(rng)
        rows.append({
            "vente_id": f"V{i:06d}",
            "date_vente": d.isoformat(),
            "client_id": rng.choice(client_ids),
            "produit_id": pid,
            "quantite": qte,
            "prix_unitaire": f"{prix[pid]:.2f}",
            "remise_pct": remise,
            "montant_ttc": f"{prix[pid] * qte * (1 - remise) * 1.2:.2f}",
            "canal": rng.choice(CANAUX),
            "devise": "EUR",
        })
    df = pd.DataFrame(rows)

    n = len(df)
    pick = lambda k: rng.sample(range(n), k)  # noqa: E731
    # Formats de date hétérogènes (export Excel FR mélangé)
    for j in pick(150):
        d = date.fromisoformat(df.at[j, "date_vente"])
        df.at[j, "date_vente"] = d.strftime("%d/%m/%Y")
    for j in pick(3):
        df.at[j, "date_vente"] = "2025-02-30"                         # date impossible
    for j in pick(8):
        df.at[j, "date_vente"] = None
    # Montants
    for j in pick(10):
        df.at[j, "montant_ttc"] = f"-{df.at[j, 'montant_ttc']}"       # avoirs ou erreurs
    for j in pick(4):
        df.at[j, "quantite"] = rng.choice([500, 1200, 9999])          # quantités extrêmes
    for j in pick(30):
        df.at[j, "montant_ttc"] = df.at[j, "montant_ttc"].replace(".", ",")  # virgule décimale
    for j in pick(6):
        df.at[j, "montant_ttc"] = None
    # Références
    for j in pick(15):
        df.at[j, "client_id"] = f"C9{rng.randint(1000, 9999)}"        # client orphelin
    for j in pick(5):
        df.at[j, "produit_id"] = "P999"                               # produit inconnu
    for j in pick(40):
        df.at[j, "canal"] = rng.choice(["Web", "WEB", " web", "tel"])  # canal non normalisé
    for j in pick(3):
        df.at[j, "devise"] = "USD"
    # Doublons : 20 lignes exactes + 5 identifiants réutilisés
    dups = df.sample(20, random_state=SEED)
    reused = df.sample(5, random_state=SEED + 1).copy()
    reused["quantite"] = reused["quantite"] + 1
    df = pd.concat([df, dups, reused], ignore_index=True)
    return df.sample(frac=1, random_state=SEED).reset_index(drop=True)


def gen_evenements(rng: random.Random, clients: pd.DataFrame) -> list[dict]:
    client_ids = clients["client_id"].unique().tolist()
    events = []
    for i in range(1, N_EVENEMENTS + 1):
        ts = datetime.combine(rand_date(rng), datetime.min.time()) + timedelta(
            seconds=rng.randint(0, 86399))
        name = rng.choices(EVENTS, weights=EVENT_WEIGHTS)[0]
        props: dict = {"session_id": f"S{rng.randint(1, 6000):05d}"}
        if name == "run_query":
            props["duree_ms"] = int(rng.lognormvariate(6, 1))
        if name == "error":
            props["code"] = rng.choice(["E500", "E404", "TIMEOUT", "E403"])
        if name == "export_csv":
            props["nb_lignes"] = rng.randint(10, 50000)
        events.append({
            "event_id": f"E{i:07d}",
            "user_id": rng.choice(client_ids),
            "event_name": name,
            "timestamp": ts.isoformat(),
            "app_version": rng.choice(VERSIONS),
            "plateforme": rng.choice(PLATEFORMES),
            "proprietes": props,
        })
    # Anomalies
    for j in rng.sample(range(len(events)), 30):
        events[j]["user_id"] = None
    for j in rng.sample(range(len(events)), 10):
        events[j]["timestamp"] = "2027-01-01T00:00:00"                # futur
    for j in rng.sample(range(len(events)), 10):
        events[j]["timestamp"] = str(int(datetime.fromisoformat(
            events[j]["timestamp"]).timestamp()))                     # epoch texte
    for j in rng.sample(range(len(events)), 15):
        events[j]["event_name"] = events[j]["event_name"].upper()
    for j in rng.sample(range(len(events)), 5):
        events[j].pop("app_version")                                  # champ absent
    for j in rng.sample(range(len(events)), 3):
        events[j]["proprietes"]["duree_ms"] = 86_400_000              # durée aberrante
    events += [dict(e) for e in rng.sample(events, 50)]               # doublons (renvoi client)
    rng.shuffle(events)
    return events


def gen_tickets(rng: random.Random, clients: pd.DataFrame) -> pd.DataFrame:
    client_ids = clients["client_id"].unique().tolist()
    rows = []
    for i in range(1, N_TICKETS + 1):
        ouvert = datetime.combine(rand_date(rng), datetime.min.time()) + timedelta(
            minutes=rng.randint(0, 1439))
        statut = rng.choices(STATUTS, weights=[10, 10, 50, 30])[0]
        resolu = (ouvert + timedelta(hours=rng.expovariate(1 / 30))
                  if statut in ("resolu", "ferme") else None)
        rows.append({
            "ticket_id": f"T{i:05d}",
            "client_id": rng.choice(client_ids),
            "date_ouverture": ouvert,
            "date_resolution": resolu,
            "categorie": rng.choice(TICKET_CATS),
            "priorite": rng.choices(PRIORITES, weights=[25, 45, 22, 8])[0],
            "statut": statut,
            "satisfaction": rng.choice([None, 1, 2, 3, 4, 5, 5, 4]) if resolu else None,
            "description": rng.choice([
                "Impossible d'exporter le rapport",
                "Erreur 500 lors de la connexion",
                "Question sur la facture du mois",
                "Requête très lente sur gros volume",
                "Demande d'ajout d'un utilisateur",
                "Le tableau de bord ne se charge pas",
            ]),
        })
    df = pd.DataFrame(rows)
    n = len(df)
    for j in rng.sample(range(n), 6):                                 # résolu avant ouverture
        if pd.notna(df.at[j, "date_resolution"]):
            df.at[j, "date_resolution"] = df.at[j, "date_ouverture"] - timedelta(hours=5)
    for j in rng.sample(range(n), 4):
        df.at[j, "satisfaction"] = rng.choice([0, 7, 10])             # hors échelle 1-5
    for j in rng.sample(range(n), 5):
        df.at[j, "priorite"] = None
    for j in rng.sample(range(n), 3):                                 # résolution sans statut cohérent
        df.at[j, "statut"] = "ouvert"
        df.at[j, "date_resolution"] = df.at[j, "date_ouverture"] + timedelta(hours=2)
    for j in rng.sample(range(n), 4):                                 # PII dans le texte libre
        df.at[j, "description"] += " - rappeler au 06 12 34 56 78 ou test.client@exemple.test"
    df = pd.concat([df, df.iloc[[1, 2, 3]]], ignore_index=True)        # doublons
    df["satisfaction"] = df["satisfaction"].astype("Int64")
    return df


FICHIERS = ["clients.xlsx", "produits.csv", "ventes.csv", "evenements.jsonl", "tickets.parquet"]


def main() -> None:
    import os
    import stat
    import sys

    existants = [f for f in FICHIERS if (RAW / f).exists()]
    if existants and "--force" not in sys.argv:
        raise SystemExit(
            "data/raw/ contient déjà des fichiers (protégés en lecture seule). "
            "Relancer avec --force pour les régénérer.")
    for f in existants:  # --force : on lève la protection avant d'écraser
        os.chmod(RAW / f, stat.S_IREAD | stat.S_IWRITE)

    rng = random.Random(SEED)
    np.random.seed(SEED)
    RAW.mkdir(parents=True, exist_ok=True)

    clients = gen_clients(rng)
    produits = gen_produits(rng)
    ventes = gen_ventes(rng, clients, produits)
    evenements = gen_evenements(rng, clients)
    tickets = gen_tickets(rng, clients)

    clients.to_excel(RAW / "clients.xlsx", index=False, sheet_name="clients")
    produits.to_csv(RAW / "produits.csv", index=False, sep=";", decimal=",", encoding="utf-8")
    ventes.to_csv(RAW / "ventes.csv", index=False, encoding="utf-8")
    with open(RAW / "evenements.jsonl", "w", encoding="utf-8") as f:
        for e in evenements:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    tickets.to_parquet(RAW / "tickets.parquet", index=False)

    print(f"clients.xlsx      {len(clients):>6} lignes")
    print(f"produits.csv      {len(produits):>6} lignes")
    print(f"ventes.csv        {len(ventes):>6} lignes")
    print(f"evenements.jsonl  {len(evenements):>6} lignes")
    print(f"tickets.parquet   {len(tickets):>6} lignes")


if __name__ == "__main__":
    main()
