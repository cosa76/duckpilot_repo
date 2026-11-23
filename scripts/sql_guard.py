"""Validation et exécution sûre d'une requête SQL générée.

Défenses, de la plus forte à la plus simple :
  1. connexion DuckDB en lecture seule, accès externe coupé, configuration verrouillée ;
  2. une seule instruction, de type SELECT (analyse par le parseur DuckDB) ;
  3. tables référencées limitées aux vues du schéma ia (et aux CTE de la requête) ;
  4. aucune fonction de table (read_csv, glob...) ni fonction sensible (getenv...) ;
  5. résultat limité en lignes, exécution interrompue au-delà d'un délai.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field

import duckdb

SCHEMA = "ia"
MAX_LIGNES = 200
DELAI_S = 30
FONCTIONS_INTERDITES = re.compile(
    r"\b(getenv|current_setting|read_\w+|glob|sniff_csv|parquet_\w+|duckdb_\w+|"
    r"pragma_\w+|query|query_table|http\w*|s3\w*|load|install|attach|copy|export|import)\s*\(",
    re.IGNORECASE,
)


class RequeteRefusee(ValueError):
    """La requête ne respecte pas les règles de sécurité."""


@dataclass
class Resultat:
    colonnes: list[str]
    lignes: list[tuple]
    tronque: bool
    tables: list[str] = field(default_factory=list)


def _parcourir(noeud, tables: set[str], ctes: set[str], fonctions_table: list[str]) -> None:
    if isinstance(noeud, dict):
        if "cte_map" in noeud:
            for entree in noeud["cte_map"].get("map", []):
                ctes.add(entree["key"].lower())
        if noeud.get("type") == "BASE_TABLE":
            schema = (noeud.get("schema_name") or "").lower()
            nom = noeud["table_name"].lower()
            catalogue = (noeud.get("catalog_name") or "").lower()
            tables.add(f"{catalogue}.{schema}.{nom}".lstrip("."))
        if noeud.get("type") == "TABLE_FUNCTION":
            fonctions_table.append(json.dumps(noeud.get("function", {}))[:80])
        for v in noeud.values():
            _parcourir(v, tables, ctes, fonctions_table)
    elif isinstance(noeud, list):
        for v in noeud:
            _parcourir(v, tables, ctes, fonctions_table)


def valider(con: duckdb.DuckDBPyConnection, sql: str, autorisees: set[str]) -> list[str]:
    """Vérifie la requête sans l'exécuter. Renvoie les vues utilisées ou lève RequeteRefusee."""
    sql = sql.strip().rstrip(";").strip()
    if not sql:
        raise RequeteRefusee("requête vide")
    if ";" in sql:
        raise RequeteRefusee("une seule instruction est autorisée")
    if FONCTIONS_INTERDITES.search(sql):
        raise RequeteRefusee("fonction interdite (accès fichier, système ou configuration)")

    arbre = json.loads(con.execute("SELECT json_serialize_sql(?)", [sql]).fetchall()[0][0])
    if arbre.get("error"):
        raise RequeteRefusee(f"requête non analysable ou non SELECT : {arbre.get('error_message')}")
    if len(arbre["statements"]) != 1:
        raise RequeteRefusee("une seule instruction est autorisée")

    tables: set[str] = set()
    ctes: set[str] = set()
    fonctions_table: list[str] = []
    _parcourir(arbre["statements"][0], tables, ctes, fonctions_table)
    if fonctions_table:
        raise RequeteRefusee("les fonctions de table (lecture de fichiers, etc.) sont interdites")

    utilisees, hors = [], []
    for t in sorted(tables):
        parts = t.split(".")
        nom = parts[-1]
        schema = parts[-2] if len(parts) >= 2 else ""
        if len(parts) == 1 and nom in ctes:
            continue
        if schema in ("", SCHEMA) and len(parts) <= 2 and nom in autorisees:
            utilisees.append(nom)
        else:
            hors.append(t)
    if hors:
        raise RequeteRefusee(f"tables hors périmètre : {', '.join(hors)}")
    if not utilisees:
        raise RequeteRefusee("la requête doit interroger au moins une vue du schéma ia")
    return sorted(set(utilisees))


def connexion_lecture(db_path: str) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(db_path, read_only=True)
    con.execute(f"SET search_path = '{SCHEMA}'").fetchall()
    con.execute("SET enable_external_access = false").fetchall()
    con.execute("SET lock_configuration = true").fetchall()
    return con


def executer(con: duckdb.DuckDBPyConnection, sql: str, autorisees: set[str],
             max_lignes: int = MAX_LIGNES, delai_s: float = DELAI_S) -> Resultat:
    tables = valider(con, sql, autorisees)
    sql = sql.strip().rstrip(";")
    minuteur = threading.Timer(delai_s, con.interrupt)
    minuteur.start()
    try:
        r = con.execute(f"SELECT * FROM ({sql}) AS q LIMIT {max_lignes + 1}")
        colonnes = [d[0] for d in r.description]
        lignes = r.fetchall()
    except duckdb.InterruptException as e:
        raise RequeteRefusee(f"requête interrompue après {delai_s} s") from e
    finally:
        minuteur.cancel()
    return Resultat(colonnes, lignes[:max_lignes], len(lignes) > max_lignes, tables)
