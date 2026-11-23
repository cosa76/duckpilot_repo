"""Évalue l'assistant SQL sur config/questions_exemples.toml.

Pour chaque question : appel de l'assistant (API Claude, coût réel), exécution
de la requête de référence en local, comparaison des valeurs.
Une réponse est juste si chaque valeur de la référence se retrouve dans le résultat
de l'assistant (nombres comparés à 1 % près, textes sans casse).

Sortie : reports/eval_assistant_sql.md

Usage : python scripts/eval_assistant.py [--ids Q01,Q05]
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from datetime import datetime

import ask
import sql_guard
from common import CONFIG, DB, REPORTS


def valeurs(lignes) -> list:
    out = []
    for r in lignes:
        for v in r:
            if v is None:
                continue
            out.append(float(v) if isinstance(v, (int, float)) and not isinstance(v, bool)
                       else str(v).strip().lower())
    return out


def retrouvee(v, candidats: list) -> bool:
    if isinstance(v, float):
        return any(isinstance(c, float) and abs(c - v) <= max(0.01 * abs(v), 0.01)
                   for c in candidats)
    return v in candidats or any(isinstance(c, str) and v in c for c in candidats)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ids", help="liste d'identifiants à évaluer, séparés par des virgules")
    a = p.parse_args()
    questions = tomllib.loads((CONFIG / "questions_exemples.toml").read_text(encoding="utf-8"))["question"]
    if a.ids:
        garder = set(a.ids.split(","))
        questions = [q for q in questions if q["id"] in garder]
    autorisees = {t["nom"] for t in ask.charger_catalogue()["table"]}

    lignes, justes = [], 0
    tok_in = tok_out = 0
    duree = 0.0
    for q in questions:
        trace, _ = ask.repondre(q["question"])
        tok_in += trace.input_tokens + trace.cache_read_tokens + trace.cache_write_tokens
        tok_out += trace.output_tokens
        duree += trace.duree_s or 0
        if q.get("hors_perimetre"):
            ok = trace.statut == "hors_perimetre"
            detail = "refus attendu" + ("" if ok else f", obtenu : {trace.statut}")
        elif trace.statut != "ok":
            ok, detail = False, f"{trace.statut} : {trace.erreur or ''}"
        else:
            con = sql_guard.connexion_lecture(str(DB))
            try:
                ref = sql_guard.executer(con, q["reference"], autorisees)
                obtenu = sql_guard.executer(con, trace.sql, autorisees)
            finally:
                con.close()
            attendues, candidats = valeurs(ref.lignes), valeurs(obtenu.lignes)
            manquantes = [v for v in attendues if not retrouvee(v, candidats)]
            ok = not manquantes
            detail = "valeurs retrouvées" if ok else f"{len(manquantes)} valeur(s) absente(s) : {manquantes[:3]}"
        justes += ok
        lignes.append((q["id"], q["question"], "juste" if ok else "faux", trace.tentatives,
                       trace.duree_s, detail))
        print(f"{q['id']} {'OK ' if ok else 'KO '} {detail}")

    md = [
        "# Évaluation de l'assistant SQL", "",
        f"Exécutée le {datetime.now():%Y-%m-%d %H:%M} avec `{ask.MODELE}` (effort {ask.EFFORT}), "
        f"prompt assistant_sql v{ask.prompt_systeme(ask.charger_catalogue())[0]}, "
        f"questions : {', '.join(q['id'] for q in questions)}.", "",
        f"**{justes} / {len(questions)} réponses justes.** "
        f"Durée totale {duree:.0f} s, soit {duree / max(len(questions), 1):.1f} s par question. "
        f"Tokens : {tok_in} en entrée, {tok_out} en sortie.", "",
        "| id | question | verdict | appels API | durée (s) | détail |",
        "|---|---|---|---|---|---|",
        *[f"| {i} | {qq} | {v} | {t} | {d} | {det} |" for i, qq, v, t, d, det in lignes],
        "",
        "Méthode : chaque valeur du résultat de la requête de référence "
        "(`config/questions_exemples.toml`) doit se retrouver dans le résultat de l'assistant, "
        "à 1 % près pour les nombres. Une question hors périmètre doit être refusée.",
        "",
    ]
    out = REPORTS / "eval_assistant_sql.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"\n{justes} / {len(questions)} justes. Rapport : reports/eval_assistant_sql.md")
    return 0 if justes == len(questions) else 1


if __name__ == "__main__":
    sys.exit(main())
