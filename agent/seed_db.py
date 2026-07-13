"""Importe les CSV mock (format Sage, séparateur `;`) dans agent/data/maria.db.

Usage : python seed_db.py [--force]

Les lignes de devis résolvent désignation et prix depuis catalogue_mock.csv ;
si les colonnes optionnelles `designation` / `prix_unitaire_ht` sont présentes
dans document_lignes_mock.csv elles priment — c'est le chemin prévu pour les
exports Sage réels (ROADMAP §2), qui portent leurs propres prix figés.
"""

import argparse
import csv
from pathlib import Path

import catalog
import db

DATA_DIR = Path(__file__).parent / "data"
CLIENTS_CSV = DATA_DIR / "clients_mock.csv"
DOCUMENTS_CSV = DATA_DIR / "documents_mock.csv"
LIGNES_CSV = DATA_DIR / "document_lignes_mock.csv"


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def seed(force: bool = False) -> None:
    if db.DB_PATH.exists():
        if not force:
            return
        db.DB_PATH.unlink()

    produits = {p["sageRef"]: p for p in catalog.load_catalog()}
    con = db.connect()
    try:
        con.executescript(db.SCHEMA)

        client_ids: dict[str, int] = {}
        for c in _read_csv(CLIENTS_CSV):
            cur = con.execute(
                "INSERT INTO clients (code, nom, contact, email, telephone, ville, type)"
                " VALUES (?,?,?,?,?,?,?)",
                (c["code"], c["nom"], c["contact"], c["email"], c["telephone"], c["ville"], c["type"]),
            )
            client_ids[c["code"]] = cur.lastrowid

        doc_ids: dict[str, int] = {}
        for d in _read_csv(DOCUMENTS_CSV):
            cur = con.execute(
                "INSERT INTO documents (numero, client_id, type, objet, date_emission,"
                " date_validite, statut, montant_ht, notes) VALUES (?,?,?,?,?,?,?,0,?)",
                (d["numero"], client_ids[d["client_code"]], d["type"], d["objet"],
                 d["date_emission"], d["date_validite"] or None, d["statut"], d["notes"] or None),
            )
            doc_ids[d["numero"]] = cur.lastrowid

        for ligne in _read_csv(LIGNES_CSV):
            ref = ligne["sage_ref"]
            produit = produits.get(ref)
            designation = ligne.get("designation") or (produit and produit["name"])
            prix = ligne.get("prix_unitaire_ht") or (produit and produit["sellPrice"])
            if not designation or prix is None:
                raise ValueError(
                    f"Référence inconnue du catalogue : {ref} (devis {ligne['numero']})"
                )
            con.execute(
                "INSERT INTO document_lignes (document_id, sage_ref, designation,"
                " quantite, prix_unitaire_ht) VALUES (?,?,?,?,?)",
                (doc_ids[ligne["numero"]], ref, designation, float(ligne["quantite"]), float(prix)),
            )

        con.execute(
            """UPDATE documents SET montant_ht = COALESCE(
                 (SELECT ROUND(SUM(quantite * prix_unitaire_ht), 2)
                  FROM document_lignes WHERE document_id = documents.id), 0)"""
        )
        con.commit()
    except BaseException:
        con.close()
        db.DB_PATH.unlink(missing_ok=True)  # jamais de DB partielle sur disque
        raise
    con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed de la base locale clients/devis depuis les CSV mock.")
    parser.add_argument("--force", action="store_true", help="régénère la base même si elle existe déjà")
    args = parser.parse_args()
    seed(force=args.force)
    con = db.connect()
    counts = {
        t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("clients", "documents", "document_lignes")
    }
    con.close()
    print(f"{db.DB_PATH} : {counts['clients']} clients, "
          f"{counts['documents']} devis, {counts['document_lignes']} lignes.")
