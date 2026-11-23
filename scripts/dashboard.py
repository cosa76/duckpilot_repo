"""Tableau de bord local : reports/tableau_de_bord.html (un seul fichier, sans dépendance).

Lit la base en lecture seule et les journaux. Rien ne sort de la machine :
le fichier s'ouvre dans un navigateur, sans serveur ni ressource externe.

Usage : python scripts/dashboard.py
"""

from __future__ import annotations

import html
import json
from datetime import datetime

import duckdb

from common import DB, REPORTS, ROOT

OUT = REPORTS / "tableau_de_bord.html"
JOURNAL_API = ROOT / "logs" / "api_calls.jsonl"


def fr(v, dec=0) -> str:
    if v is None:
        return "n.d."
    return f"{v:,.{dec}f}".replace(",", " ").replace(".", ",")


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


# ---------- Graphiques SVG (une série, un axe, survol) ----------

W, H, ML, MR, MT, MB = 640, 240, 56, 16, 16, 44


def echelle(vmax: float) -> tuple[float, list[float]]:
    """Maximum arrondi et graduations (4 intervalles)."""
    if vmax <= 0:
        return 1, [0, 1]
    import math
    pas = 10 ** math.floor(math.log10(vmax / 4))
    for m in (1, 2, 2.5, 5, 10):
        if vmax / (m * pas) <= 4:
            pas *= m
            break
    top = pas * math.ceil(vmax / pas)
    return top, [pas * i for i in range(int(round(top / pas)) + 1)]


def grille(top, ticks, unite) -> str:
    h = H - MT - MB
    out = []
    for t in ticks:
        y = MT + h - h * t / top
        out.append(f'<line class="grid" x1="{ML}" x2="{W - MR}" y1="{y:.1f}" y2="{y:.1f}"/>'
                   f'<text class="tick" x="{ML - 6}" y="{y + 4:.1f}" text-anchor="end">'
                   f'{esc(fr(t, 0 if float(t).is_integer() else 1))}{unite}</text>')
    return "".join(out)


def courbe(labels: list[str], valeurs: list[float], unite: str, titre: str, fmt_dec=0) -> str:
    top, ticks = echelle(max(valeurs))
    h, w = H - MT - MB, W - ML - MR
    pas = w / max(len(valeurs) - 1, 1)
    pts = [(ML + i * pas, MT + h - h * v / top) for i, v in enumerate(valeurs)]
    chemin = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
    etiquettes = "".join(
        f'<text class="tick" x="{x:.1f}" y="{H - MB + 16}" text-anchor="middle">{esc(labels[i][2:])}</text>'
        for i, (x, _) in enumerate(pts) if i % 3 == 0 or i == len(pts) - 1)
    cibles = "".join(
        f'<rect class="hit" x="{x - pas / 2:.1f}" y="{MT}" width="{pas:.1f}" height="{h}" '
        f'data-tip="{esc(labels[i])} : {esc(fr(valeurs[i], fmt_dec))}{esc(unite)}" '
        f'data-x="{x:.1f}" data-y="{y:.1f}"/>' for i, (x, y) in enumerate(pts))
    dernier = pts[-1]
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(titre)}">'
            f'{grille(top, ticks, unite)}<path class="line" d="{chemin}"/>'
            f'<circle class="dot" cx="{dernier[0]:.1f}" cy="{dernier[1]:.1f}" r="4"/>'
            f'<line class="cross" x1="0" x2="0" y1="{MT}" y2="{MT + h}"/>'
            f'<circle class="hover-dot" r="5"/>{etiquettes}{cibles}</svg>')


def barres_h(labels: list[str], valeurs: list[float], unite: str, titre: str, dec=0) -> str:
    hauteur = 28 * len(valeurs) + 24
    gauche, w = 190, W - 190 - 56
    top = max(valeurs) or 1
    out = [f'<svg viewBox="0 0 {W} {hauteur}" role="img" aria-label="{esc(titre)}">']
    for i, (l, v) in enumerate(zip(labels, valeurs)):
        y = 8 + i * 28
        lg = max(w * v / top, 2)
        out.append(
            f'<text class="tick" x="{gauche - 8}" y="{y + 14}" text-anchor="end">{esc(l)}</text>'
            f'<path class="bar" d="M{gauche},{y} h{lg - 4:.1f} a4,4 0 0 1 4,4 v10 a4,4 0 0 1 -4,4 h-{lg - 4:.1f} z"/>'
            f'<text class="val" x="{gauche + lg + 6:.1f}" y="{y + 14}">{esc(fr(v, dec))}{esc(unite)}</text>'
            f'<rect class="hit" x="{gauche}" y="{y - 4}" width="{w + 50}" height="26" '
            f'data-tip="{esc(l)} : {esc(fr(v, dec))}{esc(unite)}"/>')
    out.append("</svg>")
    return "".join(out)


def tableau(cols: list[str], lignes: list[tuple]) -> str:
    tete = "".join(f"<th>{esc(c)}</th>" for c in cols)
    corps = "".join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in l) + "</tr>" for l in lignes)
    return f'<table><thead><tr>{tete}</tr></thead><tbody>{corps}</tbody></table>'


def carte(titre: str, sous_titre: str, graphique: str, cols, lignes, source: str) -> str:
    return (f'<section class="card"><h2>{esc(titre)}</h2><p class="sub">{esc(sous_titre)}</p>'
            f'{graphique}<details><summary>Voir les données</summary>{tableau(cols, lignes)}</details>'
            f'<p class="src">Source : {esc(source)}</p></section>')


def tuile(libelle: str, valeur: str, detail: str = "", statut: str = "") -> str:
    icone = {"ok": "✓ ", "alerte": "! ", "ko": "✕ "}.get(statut, "")
    classe = f" st-{statut}" if statut else ""
    return (f'<div class="tile"><div class="lbl">{esc(libelle)}</div><div class="num">{esc(valeur)}</div>'
            f'<div class="det{classe}">{esc(icone + detail)}</div></div>')


# ---------- Données ----------

def charger() -> dict:
    with duckdb.connect(str(DB), read_only=True) as con:
        q = lambda s: con.execute(s).fetchall()  # noqa: E731
        d = {}
        d["ca"] = q("""SELECT strftime(mois, '%Y-%m'), round(sum(montant_ht), 2), round(sum(marge_ht), 2)
                       FROM v_ventes_enrichies GROUP BY mois ORDER BY mois""")
        d["tot"] = q("""SELECT sum(montant_ht), 100 * sum(marge_ht) / sum(montant_ht), count(*),
                        min(date_vente), max(date_vente) FROM v_ventes_enrichies""")[0]
        d["clients"] = q("""SELECT count(*) FILTER (WHERE statut_achat = 'actif'), count(*)
                            FROM v_clients_statut WHERE doublon_de IS NULL""")[0]
        d["usage"] = q("""SELECT strftime(mois, '%Y-%m'), utilisateurs_actifs,
                          round(100.0 * nb_erreurs / nb_evenements, 2) FROM v_usage_mensuel ORDER BY mois""")
        d["versions"] = q("""SELECT app_version, round(100.0 * count(*) FILTER (WHERE event_name = 'error')
                             / count(*), 2), count(*) FROM staging_evenements
                             WHERE app_version <> 'inconnue' GROUP BY 1 ORDER BY 1""")
        d["tickets"] = q("""SELECT count(*) FILTER (WHERE statut IN ('ouvert', 'en_cours')),
                            median(delai_resolution_h) FROM staging_tickets""")[0]
        d["rejets"] = q("""SELECT table_source || ' : ' || motif, count(*) FROM rejets
                           GROUP BY 1 ORDER BY 2 DESC""")
        d["run"] = q("""SELECT max(run_id) FROM journal_imports""")[0][0]
        d["qualite"] = q(f"""SELECT regle_id, severite, statut, nb_violations, regle FROM controles_qualite
                             WHERE run_id = (SELECT max(run_id) FROM controles_qualite)
                             ORDER BY statut = 'ok', severite, regle_id""")
        d["runs"] = q("""SELECT run_id, count(*) FILTER (WHERE statut = 'ok'), count(*),
                         sum(lignes) FROM journal_imports GROUP BY run_id ORDER BY run_id DESC LIMIT 5""")
    d["api"] = []
    if JOURNAL_API.exists():
        agg: dict[str, list] = {}
        for l in JOURNAL_API.read_text(encoding="utf-8").splitlines():
            e = json.loads(l)
            a = agg.setdefault(e["usage"], [0, 0, 0, 0])
            a[0] += 1
            a[1] += e["statut"] == "bloque"
            a[2] += (e.get("tokens_entree") or 0)
            a[3] += (e.get("output_tokens") or 0)
        d["api"] = [(u, *v) for u, v in sorted(agg.items())]
    return d


# ---------- Page ----------

CSS = """
:root{--surface:#fcfcfb;--page:#f3f2ee;--ink:#0b0b0b;--ink2:#52514e;--ink3:#7a7975;--grid:#e4e3de;
--s1:#2a78d6;--good:#0b7a0b;--warn:#8a5a00;--crit:#c22b2b;--line:#d9d8d2}
@media (prefers-color-scheme:dark){:root{--surface:#1a1a19;--page:#111110;--ink:#f0efec;--ink2:#c3c2b7;
--ink3:#9a998f;--grid:#2e2e2c;--s1:#3987e5;--good:#0ca30c;--warn:#fab219;--crit:#e66767;--line:#383835}}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--ink);
font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1360px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:22px;margin:0 0 4px}header p{color:var(--ink2);margin:0 0 20px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px}
.tile,.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.lbl{color:var(--ink2);font-size:13px}.num{font-size:28px;font-weight:600;font-variant-numeric:tabular-nums;margin:2px 0}
.det{color:var(--ink3);font-size:12px}.st-ok{color:var(--good)}.st-alerte{color:var(--warn)}.st-ko{color:var(--crit)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px}
@media (max-width:480px){.grid2{grid-template-columns:1fr}}
h2{font-size:15px;margin:0}.sub{color:var(--ink2);margin:2px 0 8px;font-size:13px}
.src{color:var(--ink3);font-size:12px;margin:8px 0 0}
svg{width:100%;height:auto;display:block;overflow:visible}
.grid{stroke:var(--grid);stroke-width:1}.tick{fill:var(--ink3);font-size:11px}
.val{fill:var(--ink2);font-size:11px;font-variant-numeric:tabular-nums}
.line{fill:none;stroke:var(--s1);stroke-width:2;stroke-linejoin:round}.dot{fill:var(--s1);stroke:var(--surface);stroke-width:2}
.bar{fill:var(--s1)}.hit{fill:transparent;cursor:crosshair}
.cross{stroke:var(--ink3);stroke-width:1;stroke-dasharray:3 3;opacity:0}.hover-dot{fill:var(--s1);stroke:var(--surface);stroke-width:2;opacity:0}
details{margin-top:8px}summary{cursor:pointer;color:var(--ink2);font-size:12px}
table{border-collapse:collapse;width:100%;font-size:12px;margin-top:6px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:4px 8px;border-bottom:1px solid var(--line)}th{color:var(--ink2);font-weight:600}
.wide{margin-top:16px}.scroll{overflow-x:auto}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--surface);padding:4px 8px;
border-radius:6px;font-size:12px;opacity:0;transition:opacity .1s;white-space:nowrap}
"""

JS = """
const tip=document.getElementById('tip');
document.querySelectorAll('.hit').forEach(h=>{
  const svg=h.closest('svg'),cross=svg.querySelector('.cross'),dot=svg.querySelector('.hover-dot');
  h.addEventListener('mousemove',e=>{tip.textContent=h.dataset.tip;tip.style.opacity=1;
    tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY-28)+'px';
    if(cross&&h.dataset.x){cross.setAttribute('x1',h.dataset.x);cross.setAttribute('x2',h.dataset.x);
      cross.style.opacity=1;dot.setAttribute('cx',h.dataset.x);dot.setAttribute('cy',h.dataset.y);dot.style.opacity=1;}});
  h.addEventListener('mouseleave',()=>{tip.style.opacity=0;if(cross){cross.style.opacity=0;dot.style.opacity=0;}});
});
"""


def page(d: dict) -> str:
    ca_tot, marge_pct, n_ventes, dmin, dmax = d["tot"]
    actifs, n_clients = d["clients"]
    dernier_mois = d["usage"][-1]
    ouverts, delai = d["tickets"]
    ko = [r for r in d["qualite"] if r[2] != "ok"]
    ko_bloq = [r for r in ko if r[1] == "bloquant"]
    statut_q = "ko" if ko_bloq else ("alerte" if ko else "ok")
    n_rejets = sum(n for _, n in d["rejets"])

    tuiles = "".join([
        tuile("CA HT total", f"{fr(ca_tot / 1e6, 2)} M€", f"{fr(n_ventes)} ventes valides"),
        tuile("Taux de marge HT", f"{fr(marge_pct, 1)} %", f"du {dmin:%d/%m/%Y} au {dmax:%d/%m/%Y}"),
        tuile("Clients actifs", fr(actifs), f"sur {fr(n_clients)}, achat sous 90 jours"),
        tuile("Utilisateurs actifs", fr(dernier_mois[1]), f"mois {dernier_mois[0]}"),
        tuile("Taux d'erreur appli", f"{fr(dernier_mois[2], 2)} %", f"mois {dernier_mois[0]}"),
        tuile("Tickets non résolus", fr(ouverts), f"délai médian {fr(delai, 1)} h"),
        tuile("Contrôles qualité", f"{len(d['qualite']) - len(ko)} / {len(d['qualite'])}",
              f"{len(ko_bloq)} bloquante(s), {len(ko) - len(ko_bloq)} alerte(s)", statut_q),
        tuile("Lignes rejetées", fr(n_rejets), "isolées dans la table rejets"),
    ])

    mois = [r[0] for r in d["ca"]]
    cartes = "".join([
        carte("Chiffre d'affaires HT par mois", "En milliers d'euros, ventes valides",
              courbe(mois, [r[1] / 1000 for r in d["ca"]], " k€", "CA HT par mois", 1),
              ["mois", "CA HT (€)", "marge HT (€)"], [(m, fr(c, 2), fr(g, 2)) for m, c, g in d["ca"]],
              "v_ventes_enrichies"),
        carte("Utilisateurs actifs par mois", "Au moins un évènement hors déconnexion",
              courbe([r[0] for r in d["usage"]], [r[1] for r in d["usage"]], "", "Utilisateurs actifs"),
              ["mois", "utilisateurs actifs", "taux d'erreur (%)"],
              [(m, u, fr(t, 2)) for m, u, t in d["usage"]], "v_usage_mensuel"),
        carte("Taux d'erreur par version", "Part des évènements de type erreur, toute la période",
              barres_h([r[0] for r in d["versions"]], [r[1] for r in d["versions"]], " %",
                       "Taux d'erreur par version", 2),
              ["version", "taux d'erreur (%)", "évènements"],
              [(v, fr(t, 2), fr(n)) for v, t, n in d["versions"]], "staging_evenements"),
        carte("Lignes rejetées par motif", "Dernier build staging",
              barres_h([r[0] for r in d["rejets"]], [r[1] for r in d["rejets"]], "", "Rejets par motif"),
              ["source et motif", "lignes"], d["rejets"], "table rejets"),
    ])

    qual = tableau(["règle", "sévérité", "statut", "violations", "description"],
                   [(r[0], r[1], ("✕ " if r[1] == "bloquant" else "! ") + r[2], r[3], r[4]) for r in ko]
                   ) if ko else "<p>Toutes les règles passent.</p>"
    runs = tableau(["exécution", "sources ok", "sources", "lignes importées"],
                   [(r, f"{a}", f"{b}", fr(c)) for r, a, b, c in d["runs"]])
    api = tableau(["usage", "appels", "bloqués avant envoi", "tokens entrée", "tokens sortie"],
                  [(u, a, b, fr(c), fr(e)) for u, a, b, c, e in d["api"]]) if d["api"] \
        else "<p>Aucun appel journalisé.</p>"

    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>DuckPilot</title>
<style>{CSS}</style></head><body><main>
<header><h1>DuckPilot</h1><p>Données synthétiques. Dernière exécution {esc(d['run'])}.
Généré le {datetime.now():%d/%m/%Y à %H:%M} par <code>scripts/dashboard.py</code>.</p></header>
<div class="tiles">{tuiles}</div>
<div class="grid2">{cartes}</div>
<div class="grid2 wide">
<section class="card"><h2>Contrôles qualité en échec</h2><p class="sub">Dernière exécution</p>
<div class="scroll">{qual}</div></section>
<section class="card"><h2>Derniers lancements</h2><p class="sub">journal_imports</p>
<div class="scroll">{runs}</div></section>
<section class="card"><h2>Usage de l'API Claude</h2><p class="sub">logs/api_calls.jsonl, depuis le début</p>
<div class="scroll">{api}</div></section>
</div></main><div id="tip" role="status"></div><script>{JS}</script></body></html>"""


def main() -> None:
    OUT.write_text(page(charger()), encoding="utf-8")
    print(f"Tableau de bord : {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
