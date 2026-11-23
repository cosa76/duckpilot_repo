"""Génère le rapport d'analyse Markdown à partir des requêtes de sql/analyses/.

Chaque chiffre du rapport provient d'une requête versionnée, citée en source.
Le texte ne contient aucune interprétation écrite à la main : seulement des
faits calculés. L'interprétation métier se fait à la relecture.

Lecture seule sur la base. Sorties :
  reports/rapport_analyse.md
  reports/figures/*.png

Usage : python scripts/report.py
"""

from __future__ import annotations

from datetime import datetime

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from common import DB, ROOT, q, run_id  # noqa: E402

ANALYSES = ROOT / "sql" / "analyses"
OUT = ROOT / "reports" / "rapport_analyse.md"
FIG = ROOT / "reports" / "figures"

BLEU, ORANGE, GRIS = "#2a6fdb", "#e8833a", "#8a8f98"


def fr(v, dec: int = 0) -> str:
    """Nombre au format français : espace pour les milliers, virgule décimale."""
    if v is None:
        return ""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        s = f"{v:,.{dec}f}".replace(",", " ").replace(".", ",")
        return s
    return str(v)


def run_file(con, name: str):
    r = con.execute((ANALYSES / name).read_text(encoding="utf-8"))
    cols = [d[0] for d in r.description]
    return cols, r.fetchall()


def md_table(cols, rows, decimals: dict[str, int] | None = None) -> str:
    decimals = decimals or {}
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        cells = []
        for c, v in zip(cols, r):
            if v is None:
                cells.append("**Total**" if c == cols[0] else "")
            elif isinstance(v, float):
                cells.append(fr(v, decimals.get(c, 1)))
            elif isinstance(v, int):
                cells.append(fr(v))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def source(name: str) -> str:
    return f"_Source : `sql/analyses/{name}`_"


def save(fig, name: str) -> str:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=120)
    plt.close(fig)
    return f"![{name}](figures/{name})"


def style(ax, titre: str) -> None:
    ax.set_title(titre, loc="left", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)


def main() -> None:
    parts: list[str] = []
    with duckdb.connect(str(DB), read_only=True) as con:
        tot = con.execute("""SELECT count(*), round(sum(montant_ht), 2), round(sum(marge_ht), 2),
            min(date_vente), max(date_vente) FROM v_ventes_enrichies""").fetchall()[0]
        n_raw = con.execute("SELECT count(*) FROM raw_ventes").fetchall()[0][0]
        rejets = con.execute("""SELECT table_source, motif, count(*) FROM rejets
            GROUP BY ALL ORDER BY 1, 2""").fetchall()
        tickets_anom = con.execute("""SELECT anomalie, count(*) FROM staging_tickets
            WHERE anomalie IS NOT NULL GROUP BY 1 ORDER BY 1""").fetchall()
        flags = con.execute("""SELECT
            (SELECT count(*) FROM staging_ventes WHERE montant_recalcule),
            (SELECT count(*) FROM staging_clients WHERE doublon_de IS NOT NULL),
            (SELECT count(*) FROM staging_clients WHERE NOT email_valide),
            (SELECT count(*) FROM staging_produits WHERE cout_superieur_prix),
            (SELECT count(*) FROM staging_evenements WHERE ts_depuis_epoch),
            (SELECT count(*) FROM staging_evenements WHERE duree_aberrante)""").fetchall()[0]
        counts = con.execute("""SELECT
            (SELECT count(*) FROM staging_ventes), (SELECT count(*) FROM staging_clients),
            (SELECT count(*) FROM staging_produits), (SELECT count(*) FROM staging_evenements),
            (SELECT count(*) FROM staging_tickets)""").fetchall()[0]

        q1 = run_file(con, "01_ca_marge_mensuels.sql")
        q2 = run_file(con, "02_ca_par_categorie_canal.sql")
        q3 = run_file(con, "03_clients_actifs_segment.sql")
        q4 = run_file(con, "04_support_resolution.sql")
        q5 = run_file(con, "05_usage_erreurs_version.sql")
        q6 = run_file(con, "06_usage_mensuel.sql")
        sources = q(con, """SELECT table_cible, fichier, left(sha256, 12), lignes, run_id
            FROM journal_imports
            WHERE statut = 'ok'
            QUALIFY row_number() OVER (PARTITION BY table_cible ORDER BY debut DESC) = 1
            ORDER BY table_cible""")
        cat = con.execute("""SELECT categorie, round(sum(montant_ht), 2), round(sum(marge_ht), 2)
            FROM v_ventes_enrichies GROUP BY 1 ORDER BY 2 DESC""").fetchall()

    n_ventes, ca, marge, dmin, dmax = tot
    mois_rows = q1[1]
    best = max(mois_rows, key=lambda r: r[3])
    worst = min(mois_rows, key=lambda r: r[3])
    total_seg = [r for r in q3[1] if r[0] is None][0]
    total_tk = [r for r in q4[1] if r[0] is None][0]
    ver_max = max((r for r in q5[1] if r[0] != "inconnue"), key=lambda r: r[4])
    ver_min = min((r for r in q5[1] if r[0] != "inconnue"), key=lambda r: r[4])

    parts += [
        "# Rapport d'analyse",
        "",
        f"Généré le {datetime.now():%Y-%m-%d %H:%M} par `scripts/report.py`, "
        f"exécution `{run_id()}`. "
        f"Période couverte : {dmin:%d/%m/%Y} au {dmax:%d/%m/%Y}.",
        "",
        "> **Données fictives.** Les fichiers sources sont générés par "
        "`scripts/generate_realistic_data.py` : les comportements sont réalistes "
        "(saisonnalité, croissance, churn, incidents de version) mais aucun chiffre "
        "ne décrit une entreprise réelle.",
        "",
        "## Synthèse",
        "",
        f"- {fr(n_ventes)} ventes valides sur {fr(n_raw)} lignes brutes, "
        f"soit {fr(ca)} € de CA HT et {fr(marge)} € de marge HT "
        f"(taux de marge {fr(100 * marge / ca, 1)} %).",
        f"- Meilleur mois : {best[0]} ({fr(best[3])} € HT). "
        f"Mois le plus faible : {worst[0]} ({fr(worst[3])} € HT).",
        f"- Catégorie principale : {cat[0][0]} ({fr(100 * cat[0][1] / ca, 1)} % du CA HT). "
        f"Catégorie la plus petite : {cat[-1][0]} ({fr(100 * cat[-1][1] / ca, 1)} %).",
        f"- {fr(total_seg[2])} clients actifs sur {fr(total_seg[1])} "
        f"({fr(total_seg[5], 1)} %), avec un achat dans les 90 jours avant le {dmax:%d/%m/%Y}.",
        f"- {fr(total_tk[1])} tickets support, dont {fr(total_tk[2])} non résolus. "
        f"Délai médian de résolution : {fr(total_tk[4], 1)} h.",
        f"- Taux d'erreur applicatif le plus élevé : version {ver_max[0]} ({fr(ver_max[4], 2)} %). "
        f"Le plus bas : version {ver_min[0]} ({fr(ver_min[4], 2)} %).",
        "",
    ]

    # Q1
    fig, ax = plt.subplots(figsize=(9, 3.6))
    x = [r[0] for r in mois_rows]
    ax.plot(x, [r[3] / 1000 for r in mois_rows], color=BLEU, marker="o", label="CA HT")
    ax.plot(x, [r[4] / 1000 for r in mois_rows], color=ORANGE, marker="o", label="Marge HT")
    ax.set_ylabel("k€")
    ax.tick_params(axis="x", rotation=60, labelsize=8)
    ax.legend(frameon=False)
    style(ax, "CA et marge HT par mois")
    parts += ["## 1. Chiffre d'affaires et marge par mois", "",
              save(fig, "01_ca_marge_mensuels.png"), "",
              md_table(*q1, decimals={"ca_ht": 0, "marge_ht": 0}), "",
              source("01_ca_marge_mensuels.sql"), ""]

    # Q2
    fig, ax = plt.subplots(figsize=(8, 3.4))
    labels = [r[0] for r in cat]
    ax.barh(labels[::-1], [r[1] / 1000 for r in cat][::-1], color=BLEU, label="CA HT")
    ax.barh(labels[::-1], [r[2] / 1000 for r in cat][::-1], color=ORANGE, label="Marge HT")
    ax.set_xlabel("k€")
    ax.legend(frameon=False, loc="lower right")
    style(ax, "CA et marge HT par catégorie")
    ax.grid(axis="x", alpha=0.3)
    ax.grid(axis="y", visible=False)
    parts += ["## 2. Chiffre d'affaires par catégorie et canal", "",
              save(fig, "02_ca_par_categorie.png"), "",
              md_table(*q2, decimals={"ca_ht": 0, "marge_ht": 0}), "",
              source("02_ca_par_categorie_canal.sql"), ""]

    # Q3
    seg = [r for r in q3[1] if r[0] is not None]
    fig, ax = plt.subplots(figsize=(8, 3.2))
    names = [r[0] for r in seg]
    ax.bar(names, [r[2] for r in seg], color=BLEU, label="Actifs")
    ax.bar(names, [r[3] for r in seg], bottom=[r[2] for r in seg], color=GRIS, label="Inactifs")
    ax.legend(frameon=False)
    ax.set_ylabel("clients")
    style(ax, "Clients actifs et inactifs par segment")
    parts += ["## 3. Clients actifs par segment", "",
              "Actif : au moins un achat dans les 90 jours précédant la dernière vente connue. "
              "Les doublons probables de clients sont exclus.", "",
              save(fig, "03_clients_segment.png"), "",
              md_table(*q3, decimals={"taux_actifs_pct": 1, "ca_ht_moyen_par_acheteur": 0}), "",
              source("03_clients_actifs_segment.sql"), ""]

    # Q4
    parts += ["## 4. Support : incidents et délai de résolution", "",
              "Le délai n'est calculé que pour les tickets résolus ou fermés sans anomalie de dates.",
              "", md_table(*q4, decimals={"satisfaction_moyenne": 2}), "",
              source("04_support_resolution.sql"), ""]

    # Q5 + Q6
    us = q6[1]
    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.plot([r[0] for r in us], [r[1] for r in us], color=BLEU, marker="o")
    ax.set_ylabel("utilisateurs")
    ax.tick_params(axis="x", rotation=60, labelsize=8)
    style(ax, "Utilisateurs actifs mensuels")
    vers = [r for r in q5[1] if r[0] != "inconnue"]
    fig2, ax2 = plt.subplots(figsize=(7, 3))
    ax2.bar([r[0] for r in vers], [r[4] for r in vers], color=ORANGE)
    ax2.set_ylabel("%")
    style(ax2, "Taux d'erreur par version")
    parts += ["## 5. Usage produit et erreurs", "",
              save(fig, "05_mau.png"), "",
              md_table(*q6, decimals={"taux_erreur_pct": 2}), "",
              source("06_usage_mensuel.sql"), "",
              save(fig2, "05_erreurs_version.png"), "",
              md_table(*q5, decimals={"taux_erreur_pct": 2, "duree_requete_mediane_ms": 0}), "",
              source("05_usage_erreurs_version.sql"), ""]

    # Qualité
    parts += ["## 6. Qualité des données", "",
              "Lignes isolées dans la table `rejets` (non comptées dans les analyses) :", "",
              md_table(["table", "motif", "lignes"], rejets), "",
              "Lignes gardées mais signalées :", "",
              md_table(["signal", "lignes"], [
                  ("ventes : montant TTC recalculé (manquant)", flags[0]),
                  ("clients : doublon probable (même email)", flags[1]),
                  ("clients : email invalide ou vide", flags[2]),
                  ("produits : coût supérieur au prix", flags[3]),
                  ("évènements : horodatage converti depuis epoch", flags[4]),
                  ("évènements : durée aberrante mise à vide", flags[5]),
                  *[(f"tickets : {a}", n) for a, n in tickets_anom],
              ]), "",
              "_Sources : table `rejets`, colonnes de signalement des tables `staging_*`, "
              "règles détaillées dans `docs/transformations.md`_", ""]

    parts += ["## Méthode", "",
              "1. `scripts/import_raw.py` charge les fichiers sources sans modification (tables `raw_*`).",
              "2. `scripts/build.py` applique les règles de `sql/staging/` puis crée les vues de `sql/marts/`.",
              "3. Ce rapport exécute les requêtes de `sql/analyses/` en lecture seule.",
              "",
              f"Volumes après nettoyage : {fr(counts[0])} ventes, {fr(counts[1])} clients, "
              f"{fr(counts[2])} produits, {fr(counts[3])} évènements, {fr(counts[4])} tickets.",
              "",
              "Fichiers sources utilisés (empreinte SHA-256, 12 premiers caractères). "
              "Mêmes empreintes et mêmes fichiers SQL = mêmes chiffres :", "",
              md_table(["table", "fichier", "sha256", "lignes", "import"], sources), "",
              "## Limites", "",
              "- Données fictives : les tendances sont simulées, aucune décision ne doit s'appuyer dessus.",
              "- Montants HT déduits du TTC avec une TVA supposée à 20 %.",
              "- Ventes en USD exclues faute de taux de change.",
              "- Horodatages epoch interprétés en UTC (décalage possible d'une à deux heures).",
              "- Clients actifs mesurés sur les achats, pas sur l'usage de l'application.",
              "",
              "## À valider avant diffusion", "",
              "- [ ] Le total du CA HT correspond à une source de référence.",
              "- [ ] Les règles de rejet conviennent au métier (notamment montants négatifs et vente_id en conflit).",
              "- [ ] La définition de client actif (90 jours) est la bonne.",
              "- [ ] Aucune donnée personnelle n'apparaît dans le rapport.",
              ""]

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Rapport écrit dans {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
