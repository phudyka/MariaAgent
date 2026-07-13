"""Base locale clients/devis — SQLite stdlib, seedée depuis les CSV mock format Sage.

Lecture seule côté application : l'écriture passe par seed_db.py (import CSV).
Le jour du chantier Sage (ROADMAP §2, palier export), les CSV mock sont
remplacés par les exports réels — même importeur, même schéma. Le catalogue
produits reste dans catalogue_mock.csv (catalog.py) : les lignes de devis y
font référence par sage_ref et figent désignation + prix au moment du devis.
"""

import sqlite3
import unicodedata
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "maria.db"

SCHEMA = """
CREATE TABLE clients (
  id        INTEGER PRIMARY KEY,
  code      TEXT UNIQUE NOT NULL,
  nom       TEXT NOT NULL,
  contact   TEXT, email TEXT, telephone TEXT, ville TEXT,
  type      TEXT CHECK(type IN ('particulier','professionnel','collectivite'))
);

CREATE TABLE documents (
  id            INTEGER PRIMARY KEY,
  numero        TEXT UNIQUE NOT NULL,
  client_id     INTEGER NOT NULL REFERENCES clients(id),
  type          TEXT NOT NULL DEFAULT 'devis',
  objet         TEXT NOT NULL,
  date_emission TEXT NOT NULL,
  date_validite TEXT,
  statut        TEXT CHECK(statut IN ('DRAFT','SENT','ACCEPTED','REJECTED','EXPIRED')),
  montant_ht    REAL NOT NULL,
  notes         TEXT
);

CREATE TABLE document_lignes (
  id               INTEGER PRIMARY KEY,
  document_id      INTEGER NOT NULL REFERENCES documents(id),
  sage_ref         TEXT NOT NULL,
  designation      TEXT NOT NULL,
  quantite         REAL NOT NULL,
  prix_unitaire_ht REAL NOT NULL
);

CREATE INDEX idx_documents_client ON documents(client_id, date_emission DESC);
CREATE INDEX idx_lignes_document ON document_lignes(document_id);
"""

PERIODES = {"3m": "-3 months", "6m": "-6 months", "12m": "-12 months"}


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def ensure_db() -> None:
    """Seed automatique au premier démarrage (DB régénérable, jamais versionnée)."""
    if not DB_PATH.exists():
        import seed_db
        seed_db.seed()


def _fold(text: str) -> str:
    """minuscules + suppression des accents (même logique que catalog.py)"""
    norm = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in norm if not unicodedata.combining(c))


def search_clients(q: str = "", limit: int = 50) -> list[dict]:
    """Clients + nombre de devis, filtrés (code/nom/ville/contact, insensible accents).

    Le filtre se fait côté Python : volume minuscule (dizaines de clients mock),
    et LIKE SQLite ne connaît pas les accents.
    """
    con = connect()
    try:
        rows = con.execute(
            """SELECT c.*, COUNT(d.id) AS nb_documents
               FROM clients c LEFT JOIN documents d ON d.client_id = c.id
               GROUP BY c.id ORDER BY c.nom COLLATE NOCASE"""
        ).fetchall()
    finally:
        con.close()
    clients = [dict(r) for r in rows]
    needle = _fold(q.strip())
    if needle:
        clients = [
            c for c in clients
            if needle in _fold(f"{c['code']} {c['nom']} {c['ville'] or ''} {c['contact'] or ''}")
        ]
    return clients[:limit]


def get_client(client_id: int) -> dict | None:
    con = connect()
    try:
        row = con.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    finally:
        con.close()
    return dict(row) if row else None


def _attach_lignes(con: sqlite3.Connection, docs: list[dict]) -> list[dict]:
    for d in docs:
        d["lignes"] = [
            dict(r) for r in con.execute(
                """SELECT sage_ref, designation, quantite, prix_unitaire_ht
                   FROM document_lignes WHERE document_id = ? ORDER BY id""",
                (d["id"],),
            ).fetchall()
        ]
    return docs


def client_documents(client_id: int, periode: str = "") -> list[dict]:
    """Devis d'un client (lignes imbriquées), du plus récent au plus ancien."""
    sql = "SELECT * FROM documents WHERE client_id = ?"
    params: list = [client_id]
    if periode in PERIODES:
        sql += " AND date_emission >= date('now', ?)"
        params.append(PERIODES[periode])
    sql += " ORDER BY date_emission DESC, numero DESC"
    con = connect()
    try:
        docs = [dict(r) for r in con.execute(sql, params).fetchall()]
        return _attach_lignes(con, docs)
    finally:
        con.close()


def get_document(document_id: int) -> dict | None:
    con = connect()
    try:
        row = con.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        if row is None:
            return None
        return _attach_lignes(con, [dict(row)])[0]
    finally:
        con.close()
