"""Rapport d'exécution d'un lancement du pipeline.

Lit les journaux de la base pour un run_id donné :
fichiers traités, lignes lues, validées et rejetées, erreurs principales,
transformations et contrôles qualité.

Sortie : reports/executions/execution_<run_id>.md (un fichier par lancement, conservé).

Usage : python scripts/execution_report.py [run_id] [--etapes fichier.json]
Sans run_id, prend le dernier lancement connu.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

from common import DB, REPORTS, q

OUT_DIR = REPORTS / "executions"

# Table raw -> table staging correspondante
COUPLES = {
    "raw_ventes": "staging_ventes",
    "raw_clients": "staging_clients",
    "raw_produits": "staging_produits",
    "raw_evenements": "staging_evenements",
    "raw_tickets": "staging_tickets",
}


def table_md(cols: list[str], rows) -> str:
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
    return "\n".join(out)


def existe(con, table: str) -> bool:
    return bool(q(con, "SELECT 1 FROM information_schema.tables WHERE table_name = ?", [table]))


def generer(rid: str | None, etapes: list[dict] | None = None) -> Path:
    with duckdb.connect(str(DB), read_only=True) as con:
        if rid is None:
            rid = q(con, "SELECT max(run_id) FROM journal_imports")[0][0]
        parts = [f"# Exécution {rid}", ""]

        if etapes:
            statut = "succès" if all(e["statut"] == "ok" for e in etapes) else "échec"
            parts += [f"Statut global : **{statut}**", "", "## Étapes", "",
                      table_md(["étape", "statut", "durée (s)", "détail"],
                               [(e["etape"], e["statut"], e["duree_s"], e.get("detail", ""))
                                for e in etapes]), ""]

        imports = q(con, """SELECT table_cible, fichier, statut, version, lignes,
                left(sha256, 12), alertes, erreur
            FROM journal_imports WHERE run_id = ? ORDER BY table_cible""", [rid])
        parts += ["## Fichiers traités", "",
                  table_md(["table", "fichier", "statut", "version", "lignes lues",
                            "sha256 (début)", "alertes", "erreur"], imports), ""]

        volumes = []
        rejets_ok = existe(con, "rejets")
        for raw, stg in COUPLES.items():
            if not (existe(con, raw) and existe(con, stg)):
                continue
            lus = q(con, f"SELECT count(*) FROM {raw}")[0][0]
            valides = q(con, f"SELECT count(*) FROM {stg}")[0][0]
            rejetes = (q(con, "SELECT count(*) FROM rejets WHERE table_source = ?", [raw])[0][0]
                       if rejets_ok else 0)
            volumes.append((raw, lus, valides, rejetes, lus - valides - rejetes))
        parts += ["## Volumes", "",
                  "Doublons exacts = lignes lues - validées - rejetées.", "",
                  table_md(["source", "lues", "validées", "rejetées", "doublons exacts"], volumes),
                  ""]

        if rejets_ok:
            top = q(con, """SELECT table_source, motif, count(*) n FROM rejets
                GROUP BY ALL ORDER BY n DESC LIMIT 10""")
            parts += ["## Erreurs principales", "", table_md(["source", "motif", "lignes"], top), ""]

        if existe(con, "journal_transformations"):
            tr = q(con, """SELECT couche, fichier, statut, duree_s, erreur
                FROM journal_transformations WHERE run_id = ? ORDER BY execute_le""", [rid])
            parts += ["## Transformations", "",
                      table_md(["couche", "fichier", "statut", "durée (s)", "erreur"], tr), ""]

        if existe(con, "controles_qualite"):
            cq = q(con, """SELECT regle_id, severite, statut, nb_violations, nb_lignes,
                    taux_pct, seuil_pct, regle
                FROM controles_qualite WHERE run_id = ?
                ORDER BY statut = 'ok', severite, regle_id""", [rid])
            ko = [r for r in cq if r[2] != "ok"]
            parts += ["## Contrôles qualité", "",
                      f"{len(cq)} règles exécutées, {len(ko)} en échec "
                      f"({sum(1 for r in ko if r[1] == 'bloquant')} bloquantes).", "",
                      table_md(["règle", "sévérité", "statut", "violations", "lignes",
                                "taux %", "seuil %", "description"], cq), ""]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"execution_{rid}.md"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def main() -> None:
    args = sys.argv[1:]
    etapes = None
    if "--etapes" in args:
        i = args.index("--etapes")
        etapes = json.loads(Path(args[i + 1]).read_text(encoding="utf-8"))
        del args[i:i + 2]
    out = generer(args[0] if args else None, etapes)
    print(f"Rapport d'exécution : {out.relative_to(REPORTS.parent)}")


if __name__ == "__main__":
    main()
