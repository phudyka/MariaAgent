"""Tests de la base locale clients/devis (seed CSV mock → SQLite)."""

import pytest

import db as db_module
import seed_db


def test_seed_importe_tous_les_clients(seeded_db):
    clients = seeded_db.search_clients()
    assert len(clients) == 13


def test_recherche_par_nom(seeded_db):
    res = seeded_db.search_clients("martinets")
    assert len(res) == 1
    assert res[0]["code"] == "CMARTI01"
    assert res[0]["ville"] == "Antibes"


def test_recherche_insensible_aux_accents(seeded_db):
    res = seeded_db.search_clients("elodie")
    assert len(res) == 1
    assert res[0]["code"] == "CNAVAR01"


def test_client_sans_devis(seeded_db):
    navarro = seeded_db.search_clients("navarro")[0]
    assert navarro["nb_documents"] == 0
    assert seeded_db.client_documents(navarro["id"]) == []


def test_documents_avec_lignes_et_montant(seeded_db):
    martinets = seeded_db.search_clients("martinets")[0]
    docs = seeded_db.client_documents(martinets["id"])
    de118 = next(d for d in docs if d["numero"] == "DE00118")
    assert de118["statut"] == "SENT"
    assert len(de118["lignes"]) == 5
    assert all(l["prix_unitaire_ht"] > 0 for l in de118["lignes"])
    assert all(l["designation"] for l in de118["lignes"])
    total = sum(l["quantite"] * l["prix_unitaire_ht"] for l in de118["lignes"])
    assert de118["montant_ht"] == pytest.approx(total, abs=0.01)


def test_documents_tries_par_date_desc(seeded_db):
    martinets = seeded_db.search_clients("martinets")[0]
    docs = seeded_db.client_documents(martinets["id"])
    dates = [d["date_emission"] for d in docs]
    assert dates == sorted(dates, reverse=True)


def test_filtre_periode_3m(seeded_db):
    durand = seeded_db.search_clients("durand")[0]
    tous = seeded_db.client_documents(durand["id"])
    recents = seeded_db.client_documents(durand["id"], periode="3m")
    assert any(d["numero"] == "DE00111" for d in tous)
    assert not any(d["numero"] == "DE00111" for d in recents)  # émis 2026-03-24
    assert any(d["numero"] == "DE00125" for d in recents)      # émis 2026-07-10


def test_get_document_porte_le_client_id(seeded_db):
    martinets = seeded_db.search_clients("martinets")[0]
    de118 = next(d for d in seeded_db.client_documents(martinets["id"]) if d["numero"] == "DE00118")
    doc = seeded_db.get_document(de118["id"])
    assert doc["client_id"] == martinets["id"]
    assert doc["objet"].startswith("Extension filtration")


def test_get_client_inconnu(seeded_db):
    assert seeded_db.get_client(99999) is None
    assert seeded_db.get_document(99999) is None


def test_seed_refuse_ref_inconnue(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "maria.db")
    lignes = tmp_path / "lignes.csv"
    lignes.write_text("numero;sage_ref;quantite\nDE00092;REF-INEXISTANTE;1\n", encoding="utf-8")
    monkeypatch.setattr(seed_db, "LIGNES_CSV", lignes)
    with pytest.raises(ValueError, match="REF-INEXISTANTE"):
        seed_db.seed()
