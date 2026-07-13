"""Tests des endpoints HTTP (TestClient, DB seedée isolée)."""

import pytest
from fastapi.testclient import TestClient

import app as app_module


@pytest.fixture
def client(seeded_db):
    with TestClient(app_module.app) as c:
        yield c


def _client_id(client, q):
    return client.get("/api/clients", params={"q": q}).json()[0]["id"]


def test_liste_clients(client):
    r = client.get("/api/clients")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 13
    assert {"id", "code", "nom", "ville", "type", "nb_documents"} <= set(data[0])


def test_recherche_clients(client):
    data = client.get("/api/clients", params={"q": "martinets"}).json()
    assert len(data) == 1
    assert data[0]["code"] == "CMARTI01"


def test_documents_du_client(client):
    cid = _client_id(client, "martinets")
    r = client.get(f"/api/clients/{cid}/documents")
    assert r.status_code == 200
    docs = r.json()
    de118 = next(d for d in docs if d["numero"] == "DE00118")
    assert de118["statut"] == "SENT"
    assert len(de118["lignes"]) == 5
    assert de118["lignes"][0]["sage_ref"] == "PMP-HAY-SP033"


def test_documents_filtre_periode(client):
    cid = _client_id(client, "durand")
    tous = client.get(f"/api/clients/{cid}/documents").json()
    recents = client.get(f"/api/clients/{cid}/documents", params={"periode": "3m"}).json()
    assert any(d["numero"] == "DE00111" for d in tous)
    assert not any(d["numero"] == "DE00111" for d in recents)


def test_client_inconnu_404(client):
    assert client.get("/api/clients/99999/documents").status_code == 404


def _doc_id(client, q, numero):
    cid = _client_id(client, q)
    return cid, next(d["id"] for d in client.get(f"/api/clients/{cid}/documents").json()
                     if d["numero"] == numero)


def test_chat_mail_libre_sans_message_422(client):
    r = client.post("/api/chat", json={"task": "mail_libre", "message": ""})
    assert r.status_code == 422


def test_chat_reponse_sans_client_422(client):
    r = client.post("/api/chat", json={"task": "reponse_client", "message": "Bonjour…"})
    assert r.status_code == 422
    assert "client" in r.json()["detail"].lower()


def test_chat_reponse_sans_message_422(client):
    cid = _client_id(client, "martinets")
    r = client.post("/api/chat", json={"task": "reponse_client", "client_id": cid})
    assert r.status_code == 422
    assert "message" in r.json()["detail"].lower()


def test_chat_relance_sans_devis_422(client):
    cid = _client_id(client, "martinets")
    r = client.post("/api/chat", json={"task": "relance_devis", "client_id": cid})
    assert r.status_code == 422
    assert "devis" in r.json()["detail"].lower()


def test_chat_devis_d_un_autre_client_422(client):
    cid_martinets = _client_id(client, "martinets")
    _, doc_durand = _doc_id(client, "durand", "DE00125")
    r = client.post("/api/chat", json={"task": "relance_devis",
                                       "client_id": cid_martinets, "document_id": doc_durand})
    assert r.status_code == 422
    assert "appartient" in r.json()["detail"]
