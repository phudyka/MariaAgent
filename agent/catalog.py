"""Recherche par mots-clés dans le catalogue mock (format import Sage/Peep, CSV point-virgule).

Volontairement sans embeddings ni dépendance : un scoring lexical suffit pour la démo
et le remplacement futur par une vraie source Sage se fera derrière la même interface.
"""

import csv
import unicodedata
from pathlib import Path

CSV_PATH = Path(__file__).parent / "data" / "catalogue_mock.csv"

# Vocabulaire français courant -> catégorie catalogue
CATEGORY_KEYWORDS = {
    "pompe": "PUMP", "pompes": "PUMP", "filtration": "PUMP",
    "filtre": "FILTER", "filtres": "FILTER",
    "skimmer": "SKIMMER", "skimmers": "SKIMMER",
    "vanne": "VALVE", "vannes": "VALVE", "multivoies": "VALVE",
    "tube": "PIPE", "tubes": "PIPE", "tuyau": "PIPE", "tuyaux": "PIPE", "pvc": "PIPE",
    "buse": "NOZZLE", "buses": "NOZZLE", "refoulement": "NOZZLE",
    "sable": "SAND", "verre": "SAND",
}

STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "au", "aux", "et", "ou", "pour",
    "avec", "sans", "sur", "dans", "que", "qui", "est", "son", "ses", "mon", "mes",
    "votre", "vos", "notre", "nos", "leur", "il", "elle", "nous", "vous", "je", "tu",
    "pas", "plus", "bonjour", "merci", "mail", "client", "monsieur", "madame",
}


def _fold(text: str) -> str:
    """minuscules + suppression des accents"""
    norm = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in norm if not unicodedata.combining(c))


def load_catalog() -> list[dict]:
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


_CATALOG = load_catalog()


def catalog_size() -> int:
    return len(_CATALOG)


def search(query: str, k: int = 5) -> list[dict]:
    """Retourne les k produits les plus pertinents pour la requête (score lexical)."""
    tokens = [t for t in _fold(query).replace("'", " ").split() if len(t) > 2 and t not in STOPWORDS]
    if not tokens:
        return []
    wanted_categories = {CATEGORY_KEYWORDS[t] for t in tokens if t in CATEGORY_KEYWORDS}

    scored = []
    for row in _CATALOG:
        name = _fold(row["name"])
        brand = _fold(row["brand"])
        ref = _fold(row["sageRef"])
        specs = _fold(row.get("specs", ""))
        score = 0
        for t in tokens:
            if t in name:
                score += 3
            if t in brand:
                score += 2
            if t in ref:
                score += 2
            if t in specs:
                score += 1
        if row["category"] in wanted_categories:
            score += 2
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda x: -x[0])
    return [row for _, row in scored[:k]]


def by_refs(refs: list[str]) -> list[dict]:
    """Produits du catalogue pour ces références exactes, dans l'ordre demandé.

    Utilisé quand un devis est sélectionné : ses lignes portent déjà les refs,
    le catalogue n'apporte plus que les infos fraîches (stock, prix courant).
    """
    by_ref = {row["sageRef"]: row for row in _CATALOG}
    return [by_ref[r] for r in refs if r in by_ref]


def format_rows(rows: list[dict]) -> list[str]:
    return [
        f"- {r['sageRef']} | {r['name']} | {r['brand']} | {float(r['sellPrice']):.2f} € HT | stock : {r['stock']} | {r.get('specs', '')}"
        for r in rows
    ]
