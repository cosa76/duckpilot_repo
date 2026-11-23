"""Génère un jeu de données fictif mais réaliste dans data/raw/.

Même format de fichiers que generate_synthetic_data.py (le pipeline ne change pas),
mais avec des comportements proches d'un vrai éditeur de logiciel B2B :

  Clients     base existante + acquisition croissante, creux en août et fin décembre,
              mix de segments réaliste, villes pondérées, churn mensuel par segment,
              12 % d'inscrits qui n'activent jamais, tailles de comptes très inégales.
  Ventes      licence initiale adaptée au segment, renouvellement annuel des licences,
              achats complémentaires selon le segment (conseil pour les grands comptes,
              e-learning pour les particuliers), saisonnalité (août creux, fin d'année forte),
              remises selon segment et volume, canaux selon segment, jours ouvrés.
  Produits    40 produits réels du catalogue d'un éditeur, marges par catégorie
              (logiciel ~85 %, matériel ~15 %).
  Usage       sessions en jours ouvrés et heures de bureau, adoption des fonctionnalités
              qui évolue avec l'ancienneté, baisse d'activité avant le churn,
              déploiement progressif des versions, régressions réelles :
              3.2.0 (erreurs E500) corrigée en 3.2.1, 4.0.0 (lenteurs, TIMEOUT) corrigée en 4.0.1.
  Tickets     liés aux erreurs, aux inscriptions (accès), aux ventes (facturation),
              délais par priorité, satisfaction qui baisse avec le délai.

Anomalies : mêmes types que le jeu de generate_synthetic_data.py, à des taux réalistes (voir docs/anomalies_injectees.md).
Personnes, emails et téléphones fictifs (domaine exemple.test). Résultat reproductible (graine fixe).

Usage : python scripts/generate_realistic_data.py --force
"""

from __future__ import annotations

import json
import math
import os
import random
import stat
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

SEED = 2026
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
FICHIERS = ["clients.xlsx", "produits.csv", "ventes.csv", "evenements.jsonl", "tickets.parquet"]

DEBUT, FIN = date(2025, 1, 1), date(2026, 10, 31)
JOURS = [DEBUT + timedelta(days=i) for i in range((FIN - DEBUT).days + 1)]
N_BASE, N_NOUVEAUX = 350, 850

PRENOMS = ["Alice", "Bruno", "Chloé", "David", "Emma", "Farid", "Gaëlle", "Hugo", "Inès", "Julien",
           "Karim", "Léa", "Mathis", "Nadia", "Olivier", "Pauline", "Quentin", "Rania", "Samuel",
           "Théo", "Valérie", "Yanis", "Zoé", "Camille", "Nicolas", "Sophie", "Thomas", "Manon",
           "Lucas", "Sarah", "Antoine", "Julie", "Mehdi", "Aïcha", "Pierre", "Claire"]
NOMS = ["Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit", "Durand", "Leroy",
        "Moreau", "Simon", "Laurent", "Lefebvre", "Michel", "Garcia", "Diallo", "Nguyen", "Mbaye",
        "Rossi", "Fontaine", "Girard", "Bonnet", "Dupont", "Lambert", "Fournier", "Morel", "Benali",
        "Traoré", "Rousseau", "Blanc", "Guerin", "Muller", "Henry", "Roussel", "Nicolas", "Perrin"]
VILLES = {"Paris": 28, "Lyon": 12, "Marseille": 8, "Toulouse": 8, "Lille": 8, "Bordeaux": 8,
          "Nantes": 7, "Rennes": 7, "Montpellier": 8, "Strasbourg": 6}
SEGMENTS = {"PME": 45, "ETI": 18, "Grand compte": 7, "Particulier": 30}
CHURN_MENSUEL = {"Particulier": 0.040, "PME": 0.020, "ETI": 0.012, "Grand compte": 0.006}
TAILLE = {"Particulier": 0.5, "PME": 1.0, "ETI": 2.2, "Grand compte": 5.0}

SAISON_VENTES = {1: 0.8, 2: 0.9, 3: 1.15, 4: 1.0, 5: 0.95, 6: 1.15, 7: 0.85, 8: 0.45,
                 9: 1.1, 10: 1.05, 11: 1.15, 12: 1.3}
SAISON_ACQUISITION = {1: 1.1, 2: 1.0, 3: 1.1, 4: 1.0, 5: 0.9, 6: 1.0, 7: 0.7, 8: 0.4,
                      9: 1.3, 10: 1.2, 11: 1.1, 12: 0.7}

# (libellé, catégorie, prix HT, segments exclus)
PRODUITS = [
    ("Licence Starter (annuelle)", "Logiciel", 1200, set()),
    ("Licence Pro (annuelle)", "Logiciel", 4800, set()),
    ("Licence Enterprise (annuelle)", "Logiciel", 18000, {"Particulier"}),
    ("Utilisateur supplémentaire (annuel)", "Logiciel", 360, set()),
    ("Licence lecture seule (annuelle)", "Logiciel", 240, set()),
    ("Module Connecteurs", "Logiciel", 2400, set()),
    ("Module Gouvernance", "Logiciel", 3600, {"Particulier"}),
    ("Module IA", "Logiciel", 6000, {"Particulier"}),
    ("Accès API (annuel)", "Logiciel", 3000, set()),
    ("Stockage additionnel 1 To", "Logiciel", 900, set()),
    ("Formation prise en main (1 jour)", "Formation", 950, set()),
    ("Formation SQL avancé (2 jours)", "Formation", 1800, set()),
    ("Formation administrateur (2 jours)", "Formation", 2100, {"Particulier"}),
    ("Atelier datavisualisation (1 jour)", "Formation", 1100, set()),
    ("E-learning (licence individuelle)", "Formation", 290, set()),
    ("Parcours certifiant (5 jours)", "Formation", 4200, set()),
    ("Webinaire équipe", "Formation", 450, set()),
    ("Support Standard (mensuel)", "Support", 150, set()),
    ("Support Premium (mensuel)", "Support", 450, set()),
    ("Support 24/7 (mensuel)", "Support", 1200, {"Particulier"}),
    ("Assistance à l'unité", "Support", 95, set()),
    ("Maintenance annuelle matériel", "Support", 650, set()),
    ("Support onboarding (forfait)", "Support", 1500, set()),
    ("Serveur d'appoint", "Materiel", 3200, {"Particulier"}),
    ("Poste analyste", "Materiel", 1450, set()),
    ("Écran 27 pouces", "Materiel", 320, set()),
    ("Station d'accueil", "Materiel", 210, set()),
    ("Disque SSD 2 To", "Materiel", 180, set()),
    ("Kit visioconférence", "Materiel", 690, set()),
    ("Clavier et souris", "Materiel", 85, set()),
    ("Casque audio", "Materiel", 120, set()),
    ("Audit data (jour)", "Conseil", 1250, {"Particulier"}),
    ("Accompagnement projet (jour)", "Conseil", 1100, set()),
    ("Développement sur mesure (jour)", "Conseil", 950, set()),
    ("Expertise architecture (jour)", "Conseil", 1450, {"Particulier"}),
    ("Cadrage stratégique (jour)", "Conseil", 1600, {"Particulier"}),
    ("Coaching data (demi-journée)", "Conseil", 600, set()),
    ("Mise en place gouvernance (forfait)", "Conseil", 8500, {"Particulier", "PME"}),
    ("Migration de données (forfait)", "Conseil", 12000, {"Particulier", "PME"}),
    ("Revue de sécurité (forfait)", "Conseil", 5400, {"Particulier"}),
]
COUT_RATIO = {"Logiciel": (0.10, 0.20), "Support": (0.30, 0.40), "Formation": (0.50, 0.60),
              "Conseil": (0.60, 0.70), "Materiel": (0.78, 0.88)}
LICENCE_SEGMENT = {"Particulier": "P001", "PME": "P001", "ETI": "P002", "Grand compte": "P003"}
MIX_CATEGORIES = {
    "Particulier": {"Logiciel": 30, "Formation": 40, "Support": 15, "Materiel": 15, "Conseil": 0},
    "PME": {"Logiciel": 30, "Formation": 20, "Support": 20, "Materiel": 15, "Conseil": 15},
    "ETI": {"Logiciel": 30, "Formation": 15, "Support": 15, "Materiel": 10, "Conseil": 30},
    "Grand compte": {"Logiciel": 25, "Formation": 15, "Support": 10, "Materiel": 10, "Conseil": 40},
}
ACHATS_MENSUELS = {"Particulier": 0.10, "PME": 0.35, "ETI": 0.70, "Grand compte": 1.5}
CANAUX = {
    "Particulier": {"web": 75, "telephone": 10, "magasin": 15, "partenaire": 0},
    "PME": {"web": 35, "telephone": 35, "partenaire": 20, "magasin": 10},
    "ETI": {"web": 20, "telephone": 40, "partenaire": 40, "magasin": 0},
    "Grand compte": {"web": 5, "telephone": 45, "partenaire": 50, "magasin": 0},
}

# Versions : (version, date de sortie, taux d'erreur par action, facteur de durée des requêtes)
VERSIONS = [("3.1.0", date(2024, 9, 2), 0.018, 1.0),
            ("3.2.0", date(2025, 3, 10), 0.045, 1.0),
            ("3.2.1", date(2025, 4, 7), 0.016, 1.0),
            ("3.3.0", date(2025, 10, 6), 0.014, 0.95),
            ("4.0.0", date(2026, 6, 8), 0.038, 1.7),
            ("4.0.1", date(2026, 7, 13), 0.012, 0.8)]
CODES_ERREUR = {"3.2.0": {"E500": 70, "E404": 15, "TIMEOUT": 10, "E403": 5},
                "4.0.0": {"TIMEOUT": 65, "E500": 15, "E404": 15, "E403": 5}}
CODES_DEFAUT = {"E404": 40, "E403": 25, "E500": 20, "TIMEOUT": 15}
PLATEFORMES = {"web": 55, "windows": 25, "macos": 12, "ios": 5, "android": 3}
PROBA_JOUR = {"Particulier": 0.06, "PME": 0.12, "ETI": 0.16, "Grand compte": 0.22}

DESCRIPTIONS = {
    "Bug": ["Erreur 500 à l'ouverture d'un tableau de bord", "Le rapport planifié n'a pas été envoyé",
            "Les filtres ne s'appliquent pas aux graphiques", "Export PDF vide",
            "Message d'erreur après la mise à jour", "Impossible d'enregistrer une requête"],
    "Performance": ["Requête très lente sur gros volume", "Le tableau de bord met plus d'une minute à charger",
                    "Délai dépassé (TIMEOUT) sur l'export", "Lenteurs depuis la dernière version"],
    "Acces": ["Impossible de se connecter après l'invitation", "Mot de passe expiré",
              "Demande d'ajout d'un utilisateur", "Droits insuffisants sur un espace de travail",
              "Configuration de l'authentification unique"],
    "Facturation": ["Question sur la facture du mois", "Demande de duplicata de facture",
                    "Erreur de montant sur la facture", "Changement d'adresse de facturation",
                    "Demande de bon de commande"],
    "Question": ["Comment partager un rapport avec un client externe ?", "Comment planifier un export ?",
                 "Quelle différence entre les licences Pro et Enterprise ?",
                 "Comment connecter une base PostgreSQL ?", "Où trouver la documentation de l'API ?"],
}
DELAI_MEDIAN_H = {"critique": 4, "haute": 10, "normale": 28, "basse": 60}


def tirer(rng: random.Random, poids: dict):
    return rng.choices(list(poids), weights=list(poids.values()))[0]


def sans_accent(s: str) -> str:
    return s.lower().translate(str.maketrans("éèêëàâäîïôöùûüç", "eeeeaaaiioouuuc"))


def jour_ouvre(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def version_au(d: date, retard: float) -> tuple[str, float, float]:
    courante = VERSIONS[0]
    for v in VERSIONS:
        if v[1] + timedelta(days=retard) <= d:
            courante = v
    return courante[0], courante[2], courante[3]


# ---------- Clients ----------

def gen_clients(rng: random.Random) -> list[dict]:
    clients = []
    # base existante : inscriptions 2023-2024
    dates = [date(2023, 1, 1) + timedelta(days=rng.randint(0, 730)) for _ in range(N_BASE)]
    # acquisition : croissance de 60 % sur la période, saisonnalité
    poids = [(1 + 0.6 * i / len(JOURS)) * SAISON_ACQUISITION[d.month] * (0.3 if d.weekday() >= 5 else 1)
             for i, d in enumerate(JOURS)]
    dates += rng.choices(JOURS, weights=poids, k=N_NOUVEAUX)
    dates.sort()
    for i, d in enumerate(dates, 1):
        seg = tirer(rng, SEGMENTS)
        prenom, nom = rng.choice(PRENOMS), rng.choice(NOMS)
        mois_vie = rng.expovariate(CHURN_MENSUEL[seg])
        churn = d + timedelta(days=int(30.4 * mois_vie))
        active_jamais = rng.random() < 0.12
        clients.append({
            "client_id": f"C{i:05d}", "prenom": prenom, "nom": nom,
            "email": f"{sans_accent(prenom)}.{sans_accent(nom)}{i}@exemple.test",
            "telephone": f"0{rng.choice([1, 6, 7])}{rng.randint(10000000, 99999999)}",
            "ville": tirer(rng, VILLES), "segment": seg, "date_inscription": d,
            "actif": churn > FIN and not active_jamais,
            # attributs internes (non exportés)
            "_churn": churn, "_jamais": active_jamais,
            "_taille": TAILLE[seg] * rng.lognormvariate(0, 0.7),
            "_engagement": rng.lognormvariate(0, 0.5),
            "_plateforme": tirer(rng, PLATEFORMES),
            "_retard_maj": rng.expovariate(1 / 20),
        })
    return clients


# ---------- Produits ----------

def gen_produits(rng: random.Random) -> pd.DataFrame:
    rows = []
    for i, (lib, cat, prix, _) in enumerate(PRODUITS, 1):
        cout = round(prix * rng.uniform(*COUT_RATIO[cat]), 2)
        rows.append({"produit_id": f"P{i:03d}", "libelle": lib, "categorie": cat,
                     "prix_unitaire": float(prix), "cout_unitaire": cout})
    return pd.DataFrame(rows)


# ---------- Ventes ----------

def quantite(rng, cat: str, lib: str, seg: str, taille: float) -> int:
    if "Licence" in lib and "lecture" not in lib or "forfait" in lib or "Module" in lib \
            or "Accès API" in lib or "Serveur" in lib:
        return 1
    if "Utilisateur" in lib or "lecture seule" in lib or "E-learning" in lib:
        return max(1, min(60, int(rng.lognormvariate(math.log(3 * taille + 1), 0.6))))
    if "mensuel" in lib:
        return rng.choice([1, 3, 6, 12])
    if cat == "Conseil":
        return max(1, min(40, int(rng.lognormvariate(math.log(2 + taille), 0.6))))
    if cat == "Formation":
        return max(1, min(15, int(rng.lognormvariate(math.log(1 + taille), 0.5))))
    return max(1, min(30, int(rng.lognormvariate(math.log(1 + taille), 0.7))))


def remise(rng, seg: str, qte: int, d: date) -> float:
    base = {"Particulier": 0.0, "PME": 0.0, "ETI": 0.05, "Grand compte": 0.10}[seg]
    if qte >= 10:
        base += 0.05
    if d.month == 11 and seg in ("Particulier", "PME") and rng.random() < 0.4:
        base += 0.05  # opération commerciale de novembre
    if seg == "PME" and rng.random() < 0.15:
        base += 0.05
    return round(min(base, 0.20), 2)


def gen_ventes(rng: random.Random, clients: list[dict], produits: pd.DataFrame) -> list[dict]:
    prix = dict(zip(produits.produit_id, produits.prix_unitaire))
    infos = {f"P{i:03d}": p for i, p in enumerate(PRODUITS, 1)}
    par_cat: dict[str, list[str]] = {}
    for pid, (_, cat, _, _) in infos.items():
        par_cat.setdefault(cat, []).append(pid)

    ventes = []

    def vendre(c, pid, d):
        if d < DEBUT or d > FIN:
            return
        lib, cat, _, _ = infos[pid]
        seg = c["segment"]
        if seg != "Particulier" or rng.random() < 0.6:
            d = jour_ouvre(d)
            if d > FIN:
                return
        qte = quantite(rng, cat, lib, seg, c["_taille"])
        r = remise(rng, seg, qte, d)
        ventes.append({"date_vente": d, "client_id": c["client_id"], "produit_id": pid,
                       "quantite": qte, "prix_unitaire": prix[pid], "remise_pct": r,
                       "canal": tirer(rng, CANAUX[seg]), "devise": "EUR"})

    for c in clients:
        if c["_jamais"]:
            continue
        seg, fin_vie = c["segment"], min(c["_churn"], FIN)
        debut_achat = c["date_inscription"] + timedelta(days=rng.randint(0, 25))
        # licence initiale + renouvellements annuels tant que le client est actif
        licence = LICENCE_SEGMENT[seg]
        if seg in ("PME", "ETI") and c["_taille"] > 2.5 * TAILLE[seg]:
            licence = "P002" if seg == "PME" else "P003"
        d = debut_achat
        while d <= fin_vie:
            vendre(c, licence, d)
            d += timedelta(days=365)
        if rng.random() < 0.55:
            vendre(c, "P011", debut_achat + timedelta(days=rng.randint(5, 40)))  # prise en main
        # achats complémentaires (processus de Poisson saisonnier)
        d = max(debut_achat + timedelta(days=15), DEBUT)
        taux = ACHATS_MENSUELS[seg] * min(c["_taille"] / TAILLE[seg], 3)
        while d <= fin_vie:
            d += timedelta(days=max(1, int(rng.expovariate(taux / 30.4))))
            if d > fin_vie:
                break
            if rng.random() > SAISON_VENTES[d.month] / 1.3:
                continue
            cat = tirer(rng, MIX_CATEGORIES[seg])
            choix = [p for p in par_cat[cat] if seg not in infos[p][3] and p != licence]
            # les produits moins chers se vendent plus souvent
            pid = rng.choices(choix, weights=[1 / math.sqrt(prix[p]) for p in choix])[0]
            vendre(c, pid, d)

    ventes.sort(key=lambda v: v["date_vente"])
    rows = []
    for i, v in enumerate(ventes, 1):
        ttc = v["prix_unitaire"] * v["quantite"] * (1 - v["remise_pct"]) * 1.2
        rows.append({"vente_id": f"V{i:06d}", "date_vente": v["date_vente"].isoformat(),
                     "client_id": v["client_id"], "produit_id": v["produit_id"],
                     "quantite": v["quantite"], "prix_unitaire": f"{v['prix_unitaire']:.2f}",
                     "remise_pct": v["remise_pct"], "montant_ttc": f"{ttc:.2f}",
                     "canal": v["canal"], "devise": "EUR"})
    return rows


# ---------- Évènements ----------

def facteur_jour(d: date, seg: str) -> float:
    wk = 1.0 if d.weekday() < 5 else (0.5 if seg == "Particulier" else 0.08)
    saison = 0.55 if d.month == 8 else (0.6 if d.month == 12 and d.day >= 22 else 1.0)
    return wk * saison


def gen_evenements(rng: random.Random, clients: list[dict]) -> tuple[list[dict], list[dict]]:
    """Renvoie (évènements, erreurs utiles pour générer les tickets)."""
    evts, erreurs = [], []
    n = 0
    for c in clients:
        if c["_jamais"]:
            continue
        seg = c["segment"]
        debut = max(c["date_inscription"] + timedelta(days=rng.randint(0, 10)), DEBUT)
        fin = min(c["_churn"], FIN)
        d = debut
        while d <= fin:
            anciennete = (d - c["date_inscription"]).days
            avant_churn = (c["_churn"] - d).days
            p = PROBA_JOUR[seg] * c["_engagement"] * facteur_jour(d, seg)
            p *= 1.4 if anciennete < 21 else (0.85 if anciennete > 365 else 1.0)
            if c["_churn"] <= FIN and avant_churn < 60:
                p *= max(avant_churn, 0) / 60  # désengagement avant départ
            if rng.random() < min(p, 0.9):
                plateforme = c["_plateforme"] if rng.random() < 0.85 else tirer(rng, PLATEFORMES)
                retard = 0 if plateforme == "web" else c["_retard_maj"]
                version, taux_err, f_duree = version_au(d, retard)
                heure = min(max(rng.gauss(13.5, 2.8), 7), 21)
                ts = datetime.combine(d, datetime.min.time()) + timedelta(hours=heure)
                session = f"S{n:07d}"
                actions = ["login"]
                tot = max(1, int(rng.expovariate(1 / 5)))
                for _ in range(tot):
                    if anciennete < 30:
                        poids = {"view_dashboard": 35, "run_query": 22, "invite_user": 8,
                                 "create_report": 10, "export_csv": 15, "share_report": 5}
                    else:
                        poids = {"view_dashboard": 32, "run_query": 30, "invite_user": 1,
                                 "create_report": 13, "export_csv": 14, "share_report": 8}
                    actions.append(tirer(rng, poids))
                if rng.random() < 0.7:
                    actions.append("logout")
                for a in actions:
                    props = {"session_id": session}
                    nom = a
                    if a not in ("login", "logout") and rng.random() < taux_err:
                        nom = "error"
                        code = tirer(rng, CODES_ERREUR.get(version, CODES_DEFAUT))
                        props["code"] = code
                        erreurs.append({"client": c, "ts": ts, "version": version, "code": code})
                    elif a == "run_query":
                        props["duree_ms"] = int(rng.lognormvariate(math.log(350), 0.9)
                                                * f_duree * (1.8 if seg == "Grand compte" else 1))
                    elif a == "export_csv":
                        props["nb_lignes"] = int(rng.lognormvariate(math.log(2000 * c["_taille"]), 1.2))
                    n += 1
                    evts.append({"event_id": f"E{n:07d}", "user_id": c["client_id"], "event_name": nom,
                                 "timestamp": ts.isoformat(timespec="seconds"), "app_version": version,
                                 "plateforme": plateforme, "proprietes": props})
                    ts += timedelta(seconds=int(rng.expovariate(1 / 90)) + 3)
            d += timedelta(days=1)
    return evts, erreurs


# ---------- Tickets ----------

def gen_tickets(rng: random.Random, clients: list[dict], erreurs: list[dict],
                ventes: list[dict]) -> pd.DataFrame:
    par_id = {c["client_id"]: c for c in clients}
    demandes = []
    for e in erreurs:
        proba = {"E500": 0.12, "TIMEOUT": 0.10}.get(e["code"], 0.03)
        if rng.random() < proba:
            cat = "Performance" if e["code"] == "TIMEOUT" else "Bug"
            demandes.append((e["client"], e["ts"] + timedelta(minutes=rng.randint(5, 600)), cat))
    for c in clients:
        if c["date_inscription"] >= DEBUT and rng.random() < 0.25:
            d = datetime.combine(c["date_inscription"], datetime.min.time())
            demandes.append((c, d + timedelta(hours=rng.uniform(9, 24 * 14)), "Acces"))
        if not c["_jamais"] and rng.random() < 0.5:
            for _ in range(rng.randint(1, 3)):
                d = c["date_inscription"] + timedelta(days=rng.randint(0, 600))
                if DEBUT <= d <= min(c["_churn"], FIN):
                    demandes.append((c, datetime.combine(d, datetime.min.time())
                                     + timedelta(hours=rng.uniform(8, 19)), "Question"))
    for v in ventes:
        if rng.random() < 0.06:
            d = date.fromisoformat(v["date_vente"]) + timedelta(days=rng.randint(1, 10))
            demandes.append((par_id[v["client_id"]], datetime.combine(d, datetime.min.time())
                             + timedelta(hours=rng.uniform(8, 19)), "Facturation"))

    demandes = [x for x in demandes if datetime.combine(DEBUT, datetime.min.time()) <= x[1]
                < datetime.combine(FIN + timedelta(days=1), datetime.min.time())]
    demandes.sort(key=lambda x: x[1])
    fin_donnees = datetime.combine(FIN, datetime.max.time())
    rows = []
    for i, (c, ouverture, cat) in enumerate(demandes, 1):
        seg = c["segment"]
        poids = {"basse": 25, "normale": 45, "haute": 22, "critique": 8}
        if cat == "Bug":
            poids = {"basse": 10, "normale": 40, "haute": 35, "critique": 15}
        if cat in ("Question", "Facturation"):
            poids = {"basse": 45, "normale": 45, "haute": 9, "critique": 1}
        if seg == "Grand compte":
            poids["haute"] *= 1.6
            poids["critique"] *= 1.6
        prio = tirer(rng, poids)
        delai_h = rng.lognormvariate(math.log(DELAI_MEDIAN_H[prio]), 0.8)
        resolution = ouverture + timedelta(hours=delai_h)
        if resolution.weekday() >= 5 and prio in ("normale", "basse"):
            resolution += timedelta(days=7 - resolution.weekday())
        if resolution > fin_donnees:
            statut, resolution, satisfaction = rng.choice(["ouvert", "en_cours"]), None, None
        else:
            statut = "resolu" if rng.random() < 0.6 else "ferme"
            retard = delai_h / DELAI_MEDIAN_H[prio]
            note = 5 - (1 if retard > 1.5 else 0) - (1 if retard > 3 else 0) - (1 if retard > 6 else 0)
            note = max(1, min(5, note + rng.choice([-2, -1, -1, 0, 0, 0, 1])))
            satisfaction = note if rng.random() < 0.6 else None
        rows.append({"ticket_id": f"T{i:05d}", "client_id": c["client_id"],
                     "date_ouverture": ouverture.replace(microsecond=0),
                     "date_resolution": resolution.replace(microsecond=0) if resolution else None,
                     "categorie": cat, "priorite": prio, "statut": statut,
                     "satisfaction": satisfaction, "description": rng.choice(DESCRIPTIONS[cat])})
    return pd.DataFrame(rows)


# ---------- Anomalies (taux réalistes) ----------

def anomalies_clients(rng, df: pd.DataFrame) -> pd.DataFrame:
    n = len(df)
    idx = rng.sample(range(n), 30)
    df.loc[idx[:12], "email"] = None
    df.loc[idx[12:18], "email"] = ["pas_un_email", "jean@", "@exemple.test", "marie.exemple.test",
                                   "contact@@exemple.test", "x y@exemple.test"]
    df.loc[idx[18:24], "ville"] = ["paris ", "LYON", " Marseille", "lille", "BORDEAUX", "nantes "]
    df.loc[idx[24:26], "segment"] = None
    df.loc[idx[26], "date_inscription"] = pd.Timestamp("2027-03-01")
    dups = df.iloc[[idx[27], idx[28]]].copy()
    dups["client_id"] = [f"C{n + 1:05d}", f"C{n + 2:05d}"]
    return pd.concat([df, dups, df.iloc[[idx[29]]]], ignore_index=True)


def anomalies_ventes(rng, rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    n = len(df)
    pick = lambda k: rng.sample(range(n), k)  # noqa: E731
    for j in pick(int(n * 0.015)):
        df.at[j, "date_vente"] = date.fromisoformat(df.at[j, "date_vente"]).strftime("%d/%m/%Y")
    for j in pick(3):
        df.at[j, "date_vente"] = "2025-02-30"
    for j in pick(6):
        df.at[j, "date_vente"] = None
    for j in pick(12):
        df.at[j, "montant_ttc"] = f"-{df.at[j, 'montant_ttc']}"
    for j in pick(4):
        df.at[j, "quantite"] = rng.choice([500, 1200, 9999])
    for j in pick(int(n * 0.003)):
        df.at[j, "montant_ttc"] = str(df.at[j, "montant_ttc"]).replace(".", ",")
    for j in pick(6):
        df.at[j, "montant_ttc"] = None
    for j in pick(15):
        df.at[j, "client_id"] = f"C9{rng.randint(1000, 9999)}"
    for j in pick(5):
        df.at[j, "produit_id"] = "P999"
    for j in pick(int(n * 0.005)):
        df.at[j, "canal"] = rng.choice(["Web", "WEB", " web", "tel"])
    for j in pick(3):
        df.at[j, "devise"] = "USD"
    dups = df.sample(30, random_state=SEED)
    reused = df.sample(6, random_state=SEED + 1).copy()
    reused["quantite"] = reused["quantite"].astype(int) + 1
    df = pd.concat([df, dups, reused], ignore_index=True)
    return df.sample(frac=1, random_state=SEED).reset_index(drop=True)


def anomalies_evenements(rng, evts: list[dict]) -> list[dict]:
    n = len(evts)
    for j in rng.sample(range(n), int(n * 0.001)):
        evts[j]["user_id"] = None
    for j in rng.sample(range(n), 10):
        evts[j]["timestamp"] = "2027-01-01T00:00:00"
    for j in rng.sample(range(n), int(n * 0.0005)):
        evts[j]["timestamp"] = str(int(datetime.fromisoformat(evts[j]["timestamp"]).timestamp()))
    for j in rng.sample(range(n), int(n * 0.0005)):
        evts[j]["event_name"] = evts[j]["event_name"].upper()
    for j in rng.sample(range(n), int(n * 0.0002)):
        evts[j].pop("app_version")
    for j in rng.sample(range(n), 5):
        evts[j]["proprietes"]["duree_ms"] = 86_400_000
    evts += [json.loads(json.dumps(e)) for e in rng.sample(evts, int(n * 0.002))]
    rng.shuffle(evts)
    return evts


def anomalies_tickets(rng, df: pd.DataFrame) -> pd.DataFrame:
    n = len(df)
    resolus = [j for j in range(n) if pd.notna(df.at[j, "date_resolution"])]
    for j in rng.sample(resolus, 6):
        df.at[j, "date_resolution"] = df.at[j, "date_ouverture"] - timedelta(hours=5)
    for j in rng.sample(range(n), 5):
        df.at[j, "satisfaction"] = rng.choice([0, 7, 10])
    for j in rng.sample(range(n), 6):
        df.at[j, "priorite"] = None
    for j in rng.sample(resolus, 4):
        df.at[j, "statut"] = "ouvert"
    for j in rng.sample(range(n), 8):
        df.at[j, "description"] += " - rappeler au 06 12 34 56 78 ou test.client@exemple.test"
    df = pd.concat([df, df.iloc[[1, 2, 3, 4]]], ignore_index=True)
    df["satisfaction"] = df["satisfaction"].astype("Int64")
    return df


# ---------- Principal ----------

def main() -> None:
    existants = [f for f in FICHIERS if (RAW / f).exists()]
    if existants and "--force" not in sys.argv:
        raise SystemExit("data/raw/ contient déjà des fichiers (protégés en lecture seule). "
                         "Relancer avec --force pour les remplacer.")
    for f in existants:
        os.chmod(RAW / f, stat.S_IREAD | stat.S_IWRITE)
    RAW.mkdir(parents=True, exist_ok=True)

    rng = random.Random(SEED)
    clients = gen_clients(rng)
    produits = gen_produits(rng)
    ventes = gen_ventes(rng, clients, produits)
    evts, erreurs = gen_evenements(rng, clients)
    tickets = gen_tickets(rng, clients, erreurs, ventes)

    cols = ["client_id", "prenom", "nom", "email", "telephone", "ville", "segment",
            "date_inscription", "actif"]
    df_clients = pd.DataFrame([{k: c[k] for k in cols} for c in clients])
    df_clients["date_inscription"] = pd.to_datetime(df_clients["date_inscription"])
    df_clients = anomalies_clients(rng, df_clients)
    df_ventes = anomalies_ventes(rng, ventes)
    evts = anomalies_evenements(rng, evts)
    tickets = anomalies_tickets(rng, tickets)

    df_clients.to_excel(RAW / "clients.xlsx", index=False, sheet_name="clients")
    produits.to_csv(RAW / "produits.csv", index=False, sep=";", decimal=",", encoding="utf-8")
    df_ventes.to_csv(RAW / "ventes.csv", index=False, encoding="utf-8")
    with open(RAW / "evenements.jsonl", "w", encoding="utf-8") as f:
        for e in evts:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    tickets.to_parquet(RAW / "tickets.parquet", index=False)

    for nom, n in [("clients.xlsx", len(df_clients)), ("produits.csv", len(produits)),
                   ("ventes.csv", len(df_ventes)), ("evenements.jsonl", len(evts)),
                   ("tickets.parquet", len(tickets))]:
        print(f"{nom:<18} {n:>7} lignes")


if __name__ == "__main__":
    main()
