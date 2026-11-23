"""Profil qualité automatique des tables raw_* de db/analytics.duckdb.

Pour chaque table : nombre de lignes, colonnes et types, valeurs manquantes,
cardinalité, doublons (lignes entières et clé), valeurs extrêmes des colonnes
numériques (après conversion tolérante), distributions principales.
Ajoute des contrôles ciblés (dates, références, formats).

Lecture seule : le script ouvre la base en read_only.
Sortie : reports/profil_qualite_raw.md

Usage : python scripts/profile_raw.py
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "analytics.duckdb"
OUT = ROOT / "reports" / "profil_qualite_raw.md"

TECH_COLS = {"_source_file", "_run_id", "_loaded_at"}

# Clé métier attendue par table
KEYS = {
    "raw_ventes": "vente_id",
    "raw_produits": "produit_id",
    "raw_clients": "client_id",
    "raw_evenements": "event_id",
    "raw_tickets": "ticket_id",
}

# Colonnes à analyser comme numériques (expression de conversion tolérante)
NUMERIC = {
    "raw_ventes": {
        "quantite": "TRY_CAST(quantite AS DOUBLE)",
        "prix_unitaire": "TRY_CAST(prix_unitaire AS DOUBLE)",
        "remise_pct": "TRY_CAST(remise_pct AS DOUBLE)",
        "montant_ttc": "TRY_CAST(replace(montant_ttc, ',', '.') AS DOUBLE)",
    },
    "raw_produits": {
        "prix_unitaire": "TRY_CAST(replace(prix_unitaire, ',', '.') AS DOUBLE)",
        "cout_unitaire": "TRY_CAST(replace(cout_unitaire, ',', '.') AS DOUBLE)",
    },
    "raw_evenements": {
        "duree_ms": "TRY_CAST(proprietes->>'duree_ms' AS DOUBLE)",
        "nb_lignes": "TRY_CAST(proprietes->>'nb_lignes' AS DOUBLE)",
    },
    "raw_tickets": {
        "satisfaction": "CAST(satisfaction AS DOUBLE)",
        "delai_resolution_h": "date_diff('minute', date_ouverture, date_resolution) / 60.0",
    },
}

# Colonnes catégorielles dont on affiche la distribution
CATEGORICAL = {
    "raw_ventes": ["canal", "devise"],
    "raw_produits": ["categorie"],
    "raw_clients": ["segment", "ville", "actif"],
    "raw_evenements": ["event_name", "plateforme", "app_version"],
    "raw_tickets": ["categorie", "priorite", "statut"],
}

# Contrôles ciblés : (table, libellé, requête renvoyant un entier)
CHECKS = [
    ("raw_ventes", "date_vente vide",
     "SELECT count(*) FROM raw_ventes WHERE date_vente IS NULL"),
    ("raw_ventes", "date_vente au format JJ/MM/AAAA",
     "SELECT count(*) FROM raw_ventes WHERE regexp_matches(date_vente, '^\\d{2}/\\d{2}/\\d{4}$')"),
    ("raw_ventes", "date_vente non convertible (ISO ni JJ/MM/AAAA)",
     """SELECT count(*) FROM raw_ventes WHERE date_vente IS NOT NULL
        AND TRY_CAST(date_vente AS DATE) IS NULL
        AND try_strptime(date_vente, '%d/%m/%Y') IS NULL"""),
    ("raw_ventes", "montant_ttc avec virgule décimale",
     "SELECT count(*) FROM raw_ventes WHERE montant_ttc LIKE '%,%'"),
    ("raw_ventes", "montant_ttc négatif",
     "SELECT count(*) FROM raw_ventes WHERE TRY_CAST(replace(montant_ttc, ',', '.') AS DOUBLE) < 0"),
    ("raw_ventes", "quantite > 100",
     "SELECT count(*) FROM raw_ventes WHERE TRY_CAST(quantite AS INT) > 100"),
    ("raw_ventes", "client_id absent de raw_clients",
     """SELECT count(*) FROM raw_ventes v
        WHERE NOT EXISTS (SELECT 1 FROM raw_clients c WHERE c.client_id = v.client_id)"""),
    ("raw_ventes", "produit_id absent de raw_produits",
     """SELECT count(*) FROM raw_ventes v
        WHERE NOT EXISTS (SELECT 1 FROM raw_produits p WHERE p.produit_id = v.produit_id)"""),
    ("raw_ventes", "canal hors liste (web, magasin, telephone, partenaire)",
     "SELECT count(*) FROM raw_ventes WHERE canal NOT IN ('web', 'magasin', 'telephone', 'partenaire')"),
    ("raw_ventes", "devise différente de EUR",
     "SELECT count(*) FROM raw_ventes WHERE devise <> 'EUR'"),
    ("raw_produits", "cout_unitaire > prix_unitaire",
     """SELECT count(*) FROM raw_produits
        WHERE TRY_CAST(replace(cout_unitaire, ',', '.') AS DOUBLE)
            > TRY_CAST(replace(prix_unitaire, ',', '.') AS DOUBLE)"""),
    ("raw_clients", "email vide",
     "SELECT count(*) FROM raw_clients WHERE email IS NULL"),
    ("raw_clients", "email au format invalide",
     """SELECT count(*) FROM raw_clients WHERE email IS NOT NULL
        AND NOT regexp_matches(email, '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$')"""),
    ("raw_clients", "ville hors référentiel (casse, espaces, inconnue)",
     """SELECT count(*) FROM raw_clients WHERE ville NOT IN ('Paris', 'Lyon', 'Marseille',
        'Toulouse', 'Nantes', 'Lille', 'Bordeaux', 'Strasbourg', 'Rennes', 'Montpellier')"""),
    ("raw_clients", "date_inscription dans le futur",
     "SELECT count(*) FROM raw_clients WHERE TRY_CAST(date_inscription AS DATE) > current_date"),
    ("raw_clients", "même email sur plusieurs client_id",
     """SELECT count(*) FROM (SELECT email FROM raw_clients WHERE email IS NOT NULL
        GROUP BY email HAVING count(DISTINCT client_id) > 1)"""),
    ("raw_evenements", "user_id vide",
     "SELECT count(*) FROM raw_evenements WHERE user_id IS NULL"),
    ("raw_evenements", "timestamp non ISO (epoch ou autre)",
     "SELECT count(*) FROM raw_evenements WHERE TRY_CAST(timestamp AS TIMESTAMP) IS NULL"),
    ("raw_evenements", "timestamp dans le futur",
     "SELECT count(*) FROM raw_evenements WHERE TRY_CAST(timestamp AS TIMESTAMP) > now()"),
    ("raw_evenements", "event_name en majuscules",
     "SELECT count(*) FROM raw_evenements WHERE event_name <> lower(event_name)"),
    ("raw_evenements", "app_version absente",
     "SELECT count(*) FROM raw_evenements WHERE app_version IS NULL"),
    ("raw_tickets", "date_resolution antérieure à date_ouverture",
     "SELECT count(*) FROM raw_tickets WHERE date_resolution < date_ouverture"),
    ("raw_tickets", "statut ouvert avec date_resolution renseignée",
     "SELECT count(*) FROM raw_tickets WHERE statut = 'ouvert' AND date_resolution IS NOT NULL"),
    ("raw_tickets", "satisfaction hors échelle 1 à 5",
     "SELECT count(*) FROM raw_tickets WHERE satisfaction NOT BETWEEN 1 AND 5"),
    ("raw_tickets", "description contenant un email ou un téléphone (PII)",
     """SELECT count(*) FROM raw_tickets
        WHERE regexp_matches(description, '[^@\\s]+@[^@\\s]+|0\\d([ .]?\\d{2}){4}')"""),
]


def q(con, sql: str):
    return con.execute(sql).fetchall()


def md_table(headers: list[str], rows: list[tuple]) -> str:
    def fmt(v):
        if v is None:
            return ""
        if isinstance(v, float):
            return f"{v:,.2f}".replace(",", " ")
        return str(v).replace("|", "\\|")
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(fmt(v) for v in r) + " |" for r in rows]
    return "\n".join(out)


def profile_table(con, table: str) -> str:
    cols = [(r[0], r[1]) for r in q(con, f"DESCRIBE {table}") if r[0] not in TECH_COLS]
    col_list = ", ".join(f'"{c}"' for c, _ in cols)
    n = q(con, f"SELECT count(*) FROM {table}")[0][0]
    key = KEYS[table]

    full_dup = q(con, f"""SELECT coalesce(sum(c - 1), 0) FROM
        (SELECT count(*) c FROM {table} GROUP BY ALL HAVING c > 1)""".replace(
        "GROUP BY ALL", f"GROUP BY {col_list}"))[0][0]
    key_dup = q(con, f"""SELECT count(*), coalesce(sum(c), 0) FROM
        (SELECT count(*) c FROM {table} GROUP BY "{key}" HAVING c > 1)""")[0]

    lines = [f"## {table}", "",
             f"- Lignes : **{n}**",
             f"- Colonnes métier : {len(cols)}",
             f"- Lignes en double exact (hors colonnes techniques) : **{full_dup}**",
             f"- Clé `{key}` : {key_dup[0]} valeurs en double, portées par {key_dup[1]} lignes",
             "", "### Colonnes", ""]

    rows = []
    for c, t in cols:
        nulls, distinct, mn, mx = q(con, f"""SELECT count(*) - count("{c}"),
            approx_count_distinct("{c}"), min("{c}")::VARCHAR, max("{c}")::VARCHAR FROM {table}""")[0]
        mn = (mn[:30] + "…") if mn and len(mn) > 30 else mn
        mx = (mx[:30] + "…") if mx and len(mx) > 30 else mx
        rows.append((c, t, nulls, round(100 * nulls / n, 2) if n else 0, distinct, mn, mx))
    lines.append(md_table(["colonne", "type", "nulls", "% nulls", "distinct (approx)",
                           "min", "max"], rows))

    if table in NUMERIC:
        lines += ["", "### Valeurs numériques (conversion tolérante)", ""]
        rows = []
        for c, expr in NUMERIC[table].items():
            r = q(con, f"""WITH x AS (SELECT {expr} AS v FROM {table})
                SELECT count(v), min(v), quantile_cont(v, 0.01), median(v),
                       quantile_cont(v, 0.99), max(v), avg(v), stddev(v),
                       count(*) FILTER (WHERE v < quantile_cont_v.q1 - 3 * (quantile_cont_v.q3 - quantile_cont_v.q1)
                                         OR v > quantile_cont_v.q3 + 3 * (quantile_cont_v.q3 - quantile_cont_v.q1))
                FROM x, (SELECT quantile_cont(v, 0.25) q1, quantile_cont(v, 0.75) q3 FROM x) quantile_cont_v""")[0]
            rows.append((c, *r))
        lines.append(md_table(["colonne", "valeurs", "min", "p01", "médiane", "p99", "max",
                               "moyenne", "écart-type", "extrêmes (3 IQR)"], rows))

    lines += ["", "### Distributions principales", ""]
    for c in CATEGORICAL.get(table, []):
        r = q(con, f"""SELECT coalesce("{c}"::VARCHAR, '(null)') AS v, count(*) n,
            round(100.0 * count(*) / sum(count(*)) OVER (), 1) pct
            FROM {table} GROUP BY 1 ORDER BY n DESC LIMIT 10""")
        lines += [f"**{c}**", "", md_table(["valeur", "lignes", "%"], r), ""]
    return "\n".join(lines)


def main() -> None:
    with duckdb.connect(str(DB), read_only=True) as con:
        tables = [r[0] for r in q(con, """SELECT table_name FROM information_schema.tables
            WHERE table_name LIKE 'raw_%' ORDER BY table_name""")]
        parts = [
            "# Profil qualité des tables raw",
            "",
            f"Généré le {datetime.now():%Y-%m-%d %H:%M} par `scripts/profile_raw.py` "
            f"sur `db/analytics.duckdb`.",
            "",
            "Données synthétiques. Les tables raw sont en texte pour les sources CSV et JSON : "
            "les valeurs numériques sont converties à la volée pour le profil, "
            "les valeurs non convertibles sont comptées comme nulles dans cette section.",
            "",
            "## Synthèse",
            "",
        ]
        summary = []
        for t in tables:
            n = q(con, f"SELECT count(*) FROM {t}")[0][0]
            ncol = len([r for r in q(con, f"DESCRIBE {t}") if r[0] not in TECH_COLS])
            summary.append((t, n, ncol))
        parts.append(md_table(["table", "lignes", "colonnes"], summary))

        parts += ["", "## Contrôles ciblés", ""]
        rows = [(t, label, q(con, sql)[0][0]) for t, label, sql in CHECKS if t in tables]
        parts.append(md_table(["table", "contrôle", "lignes concernées"], rows))
        parts.append("")

        for t in tables:
            parts += [profile_table(con, t), ""]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Profil écrit dans {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
