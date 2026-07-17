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


# ── Handoff du sélecteur guidé (mêmes validations 422 que /api/chat) ─────────
def test_handoff_mail_libre_sans_message_422(client):
    r = client.post("/api/handoff", json={"task": "mail_libre", "message": ""})
    assert r.status_code == 422


def test_handoff_reponse_sans_client_422(client):
    r = client.post("/api/handoff", json={"task": "reponse_client", "message": "Bonjour…"})
    assert r.status_code == 422
    assert "client" in r.json()["detail"].lower()


def test_handoff_relance_devis_d_un_autre_client_422(client):
    cid_martinets = _client_id(client, "martinets")
    _, doc_durand = _doc_id(client, "durand", "DE00125")
    r = client.post("/api/handoff", json={"task": "relance_devis",
                                          "client_id": cid_martinets, "document_id": doc_durand})
    assert r.status_code == 422
    assert "appartient" in r.json()["detail"]


def test_handoff_renvoie_recap(client):
    cid = _client_id(client, "martinets")
    r = client.post("/api/handoff", json={"task": "reponse_client",
                                          "client_id": cid, "message": "Pouvez-vous me confirmer le délai ?"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "paste"  # Plan B par défaut (pas de JWT configuré en test)
    assert "FICHE ENTREPRISE" in body["recap"]
    assert "CLIENT" in body["recap"] or "<client>" in body["recap"]


# ── Endpoint OpenAI-compatible (presets Open WebUI) ─────────────────────────
def test_v1_models(client):
    r = client.get("/v1/models")
    assert r.status_code == 200
    ids = {m["id"] for m in r.json()["data"]}
    assert {"maria-general", "maria-libre", "maria-reponse", "maria-relance"} <= ids


def test_v1_chat_preset_reponse_refuse(client):
    # maria-reponse / maria-relance ne sont pas servis en direct (sélecteur obligatoire).
    r = client.post("/v1/chat/completions",
                    json={"model": "maria-reponse", "messages": [{"role": "user", "content": "x"}]})
    assert r.status_code == 400


def test_v1_chat_general_sans_gateway(client):
    # Pas de gateway Hermes en test : on vérifie seulement que le routing accepte
    # le modèle et tente l'appel (échec 502 = bon signe, pas d'erreur de validation).
    r = client.post("/v1/chat/completions",
                    json={"model": "maria-general", "stream": False,
                          "messages": [{"role": "user", "content": "Mail fournisseur pour pompe"}]})
    assert r.status_code in (200, 502)
