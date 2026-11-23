"""Exécute les règles de config/regles_qualite.toml et les historise.

Une règle échoue quand la part de lignes en violation dépasse son seuil
(0 % par défaut). Résultats écrits dans la table controles_qualite.

Usage : python scripts/quality.py
Code retour 1 si une règle bloquante échoue (ou si une règle ne s'exécute pas).
"""

from __future__ import annotations

import sys
import tomllib
from datetime import datetime

import duckdb

from common import CONFIG, DB, q, run_id

DDL = """
CREATE TABLE IF NOT EXISTS controles_qualite (
    run_id        VARCHAR,
    regle_id      VARCHAR,
    table_cible   VARCHAR,
    regle         VARCHAR,
    severite      VARCHAR,
    nb_violations BIGINT,
    nb_lignes     BIGINT,
    taux_pct      DOUBLE,
    seuil_pct     DOUBLE,
    statut        VARCHAR,   -- ok | ko | erreur
    erreur        VARCHAR,
    execute_le    TIMESTAMP
)
"""


def charger_regles() -> list[dict]:
    regles = tomllib.loads((CONFIG / "regles_qualite.toml").read_text(encoding="utf-8"))["regle"]
    ids = [r["id"] for r in regles]
    doublons = {i for i in ids if ids.count(i) > 1}
    if doublons:
        raise ValueError(f"identifiants de règle en double : {sorted(doublons)}")
    for r in regles:
        if r["severite"] not in ("bloquant", "alerte"):
            raise ValueError(f"{r['id']} : sévérité inconnue {r['severite']}")
    return regles


def evaluer(con, regle: dict) -> dict:
    seuil = float(regle.get("seuil_pct", 0))
    res = {"regle_id": regle["id"], "table_cible": regle["table"], "regle": regle["regle"],
           "severite": regle["severite"], "seuil_pct": seuil, "nb_violations": None,
           "nb_lignes": None, "taux_pct": None, "erreur": None}
    try:
        violations, lignes = q(con, regle["sql"])[0]
        taux = round(100.0 * violations / lignes, 3) if lignes else 0.0
        res.update(nb_violations=violations, nb_lignes=lignes, taux_pct=taux,
                   statut="ok" if (violations == 0 or (seuil > 0 and taux <= seuil)) else "ko")
    except duckdb.Error as e:
        res.update(statut="erreur", erreur=str(e).splitlines()[0])
    return res


def main() -> int:
    rid = run_id()
    regles = charger_regles()
    bloque = False
    with duckdb.connect(str(DB)) as con:
        q(con, DDL)
        q(con, "DELETE FROM controles_qualite WHERE run_id = ?", [rid])
        for regle in regles:
            r = evaluer(con, regle)
            r.update(run_id=rid, execute_le=datetime.now())
            cols = list(r)
            q(con, f"INSERT INTO controles_qualite ({', '.join(cols)}) "
                   f"VALUES ({', '.join('?' * len(cols))})", [r[c] for c in cols])
            detail = r["erreur"] or f"{r['nb_violations']} / {r['nb_lignes']} ({r['taux_pct']} %)"
            print(f"{r['statut']:<6} {r['severite']:<8} {r['regle_id']:<7} {r['regle']} : {detail}")
            if r["statut"] == "erreur" or (r["statut"] == "ko" and r["severite"] == "bloquant"):
                bloque = True
    if bloque:
        print("\nÉchec : au moins une règle bloquante n'est pas respectée.")
    return 1 if bloque else 0


if __name__ == "__main__":
    sys.exit(main())
