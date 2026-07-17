"""Agent commercial local ETS Maria — proxy FastAPI vers Hermes Agent.

Rôle : servir l'interface web locale, enrichir chaque demande (instruction de
tâche, fiche entreprise, extraits catalogue) puis relayer vers le gateway
Hermes Agent (/v1/chat/completions, OpenAI-compatible), qui pilote lui-même
Ollama. Toute la chaîne est locale : aucun appel réseau externe.

Seul ce proxy est exposé au LAN ; le gateway Hermes et Ollama restent en
127.0.0.1 et ne sont joignables que depuis la machine elle-même.
"""

import json
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

import catalog
import db
import prompts

HERMES_URL = os.environ.get("MARIA_HERMES_URL", "http://127.0.0.1:8642")
HERMES_KEY = os.environ.get("MARIA_HERMES_KEY", "")
HERMES_MODEL = os.environ.get("MARIA_HERMES_MODEL", "maria-agent")
OLLAMA_URL = os.environ.get("MARIA_OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("MARIA_MODEL", "qwen3:4b-instruct-2507-q4_K_M")

STATIC_DIR = Path(__file__).parent / "static"


def _load_hermes_key() -> str:
    """Clé API du gateway : env MARIA_HERMES_KEY, sinon lue dans ~/.hermes/config.yaml."""
    if HERMES_KEY:
        return HERMES_KEY
    cfg = Path.home() / ".hermes" / "config.yaml"
    try:
        in_api_server = False
        for line in cfg.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("api_server:"):
                in_api_server = True
            elif in_api_server and line.strip().startswith("key:"):
                return line.split(":", 1)[1].strip().strip("\"'")
    except OSError:
        pass
    return ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.ensure_db()  # base clients/devis mock : seed automatique au premier démarrage
    key = _load_hermes_key()
    app.state.hermes_headers = {"Authorization": f"Bearer {key}"} if key else {}
    app.state.http = httpx.AsyncClient(base_url=HERMES_URL, timeout=httpx.Timeout(600.0, connect=5.0))
    app.state.ollama = httpx.AsyncClient(base_url=OLLAMA_URL, timeout=httpx.Timeout(10.0, connect=3.0))
    yield
    await app.state.http.aclose()
    await app.state.ollama.aclose()


app = FastAPI(title="Agent commercial ETS Maria", lifespan=lifespan)


class ChatRequest(BaseModel):
    task: str = Field(pattern="^(reponse_client|relance_devis|mail_libre)$")
    message: str = Field(default="", max_length=8000)
    client_id: int | None = None
    document_id: int | None = None
    history: list[dict] = Field(default_factory=list, max_length=20)


# ── Endpoint OpenAI-compatible (pour Open WebUI) ─────────────────────────────
# Sous-agents = presets « Modèles » côté Open WebUI. Le proxy ne sert que deux
# presets en direct (général + mail libre) : ils n'ont besoin d'aucun ID client/
# devis. Réponse client / Relance devis passent exclusivement par /api/handoff
# (sélecteur guidé) — jamais interprétés depuis du texte libre (anti-injection).
OPENAI_MODELS = [
    {"id": "maria-general", "name": "Maria — Général"},
    {"id": "maria-libre", "name": "Maria — Mail libre"},
    {"id": "maria-reponse", "name": "Maria — Réponse client (via sélecteur)"},
    {"id": "maria-relance", "name": "Maria — Relance devis (via sélecteur)"},
]
# Presets traités en direct par ce proxy (les deux autres sont déclenchés par
# /api/handoff depuis le sélecteur, pas par un appel OpenAI-compatible).
DIRECT_MODELS = {"maria-general": "mail_libre", "maria-libre": "mail_libre"}


class OpenAIChatRequest(BaseModel):
    model: str
    messages: list[dict] = Field(default_factory=list)
    stream: bool = True


def _load_chat_context(req: ChatRequest) -> tuple[dict | None, dict | None]:
    """Valide la sélection par tâche et charge client/devis depuis la base locale.

    L'UI n'envoie que des IDs : les données (refs, dates, montants) sont
    assemblées ici, côté serveur — aucune saisie manuelle à vérifier.
    """
    if req.task == "mail_libre":
        if not req.message.strip():
            raise HTTPException(status_code=422, detail="Décrivez le mail à rédiger.")
        return None, None
    if req.client_id is None:
        raise HTTPException(status_code=422, detail="Sélectionnez d'abord un client.")
    client = db.get_client(req.client_id)
    if client is None:
        raise HTTPException(status_code=422, detail="Client introuvable — actualisez la page.")
    if req.task == "reponse_client" and not req.message.strip():
        raise HTTPException(status_code=422, detail="Collez le message reçu du client.")
    if req.task == "relance_devis" and req.document_id is None:
        raise HTTPException(status_code=422, detail="Sélectionnez le devis à relancer.")
    document = None
    if req.document_id is not None:
        document = db.get_document(req.document_id)
        if document is None or document["client_id"] != client["id"]:
            raise HTTPException(status_code=422, detail="Ce devis n'appartient pas au client sélectionné.")
    return client, document


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/static/{path:path}")
async def static_files(path: str):
    target = (STATIC_DIR / path).resolve()
    if not target.is_relative_to(STATIC_DIR.resolve()) or not target.is_file():
        return FileResponse(STATIC_DIR / "index.html", status_code=404)
    return FileResponse(target)


@app.get("/api/config")
async def config():
    return {
        "model": MODEL,
        "tasks": {tid: {"label": t["label"], "placeholder": t["placeholder"]} for tid, t in prompts.TASKS.items()},
        "catalog_size": catalog.catalog_size(),
    }


@app.get("/api/clients")
async def clients(q: str = ""):
    return db.search_clients(q)


@app.get("/api/clients/{client_id}/documents")
async def client_documents(client_id: int, periode: str = ""):
    if db.get_client(client_id) is None:
        raise HTTPException(status_code=404, detail="Client inconnu.")
    return db.client_documents(client_id, periode)


@app.get("/api/health")
async def health():
    hermes_ok = False
    try:
        r = await app.state.http.get("/health")
        hermes_ok = r.status_code == 200
    except httpx.HTTPError:
        pass
    ollama_ok, model_ready = False, False
    try:
        r = await app.state.ollama.get("/api/tags")
        r.raise_for_status()
        ollama_ok = True
        models = [m["name"] for m in r.json().get("models", [])]
        model_ready = any(m == MODEL or m.split(":")[0] == MODEL for m in models)
    except httpx.HTTPError:
        pass
    return {"hermes": hermes_ok, "ollama": ollama_ok, "model": MODEL,
            "model_ready": model_ready, "ready": hermes_ok and ollama_ok and model_ready}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/api/chat")
async def chat(req: ChatRequest):
    client, document = _load_chat_context(req)
    if document:
        # Devis sélectionné : refs exactes des lignes ; le catalogue n'ajoute que le stock.
        refs = [ligne["sage_ref"] for ligne in document["lignes"]]
        rows = catalog.by_refs(refs)
    else:
        rows = catalog.search(req.message)
        refs = [r["sageRef"] for r in rows]
    catalog_lines = catalog.format_rows(rows)
    messages = prompts.build_messages(req.task, req.message, req.history, catalog_lines,
                                      client=client, document=document)

    async def stream():
        yield _sse({"type": "meta", "catalog_refs": refs})
        payload = {"model": HERMES_MODEL, "messages": messages, "stream": True}
        started = time.monotonic()
        n_chunks = 0
        try:
            async with app.state.http.stream(
                "POST", "/v1/chat/completions", json=payload, headers=app.state.hermes_headers
            ) as r:
                if r.status_code != 200:
                    body = (await r.aread()).decode("utf-8", "replace")[:300]
                    yield _sse({"type": "error", "message": f"Le gateway Hermes a répondu {r.status_code} : {body}"})
                    return
                async for line in r.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        elapsed = time.monotonic() - started
                        yield _sse({"type": "done", "stats": {"seconds": round(elapsed, 1), "chunks": n_chunks}})
                        return
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = (chunk.get("choices") or [{}])[0].get("delta", {}).get("content")
                    if delta:
                        n_chunks += 1
                        yield _sse({"type": "delta", "text": delta})
                # Flux terminé sans [DONE] : clore proprement côté UI.
                yield _sse({"type": "done", "stats": {"seconds": round(time.monotonic() - started, 1)}})
        except httpx.HTTPError as e:
            yield _sse({
                "type": "error",
                "message": "Impossible de joindre l'agent local (gateway Hermes). "
                           f"Vérifiez qu'il est démarré : scripts/run.sh — détail : {type(e).__name__}",
            })

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Handoff du sélecteur guidé vers Open WebUI ──────────────────────────────
# Point d'entrée unique où transitent client_id/document_id (jamais depuis du
# texte libre). Réutilise les mêmes validations 422 que /api/chat.
# Plan B (robuste, par défaut) : renvoie le récap assemblé + un lien Open WebUI
#   prêt-à-coller ; l'employé colle une fois, aucune saisie d'ID.
# Plan A (optionnel, fragilité connue) : si OPENWEBUI_BASE_URL + un JWT de
#   service sont fournis, crée une conversation pré-remplie et renvoie son URL.
class HandoffRequest(BaseModel):
    task: str = Field(pattern="^(reponse_client|relance_devis|mail_libre)$")
    message: str = Field(default="", max_length=8000)
    client_id: int | None = None
    document_id: int | None = None


OPENWEBUI_BASE_URL = os.environ.get("MARIA_OPENWEBUI_URL", "http://127.0.0.1:3000")
OPENWEBUI_JWT = os.environ.get("MARIA_OPENWEBUI_JWT", "")


def _build_recap(req: HandoffRequest, client, document) -> str:
    """Assemble le même contexte que /api/chat, renvoyé comme texte prêt-à-coller."""
    if document:
        refs = [ligne["sage_ref"] for ligne in document["lignes"]]
        rows = catalog.by_refs(refs)
    else:
        rows = catalog.search(req.message)
    catalog_lines = catalog.format_rows(rows)
    messages = prompts.build_messages(req.task, req.message, [], catalog_lines,
                                      client=client, document=document)
    # build_messages préfixe tout au 1er message user : on le rend tel quel.
    return messages[0]["content"] if messages else ""


@app.post("/api/handoff")
async def handoff(req: HandoffRequest):
    client, document = _load_chat_context(req)  # valide (422 si besoin)
    recap = _build_recap(req, client, document)
    if OPENWEBUI_JWT:
        # Plan A (best-effort) : tente de créer une conversation Open WebUI.
        try:
            chat_id = await _create_openwebui_chat(req.task, recap)
            if chat_id:
                return {"mode": "openwebui", "chat_url": f"{OPENWEBUI_BASE_URL}/?chat={chat_id}",
                        "recap": recap}
        except Exception:
            pass  # retombe sur Plan B
    return {"mode": "paste", "recap": recap, "openwebui_url": OPENWEBUI_BASE_URL}


async def _create_openwebui_chat(task: str, recap: str) -> str | None:
    """Plan A : crée une conversation Open WebUI pré-remplie (API interne non garantie).

    Flux documenté par la communauté : POST /api/v1/chats/new (messages) →
    injecte un message assistant vide → déclenche /api/chat/completions avec le
    chat_id. Fragile across versions → ne jamais dépendre de ça seul (Plan B existe).
    """
    headers = {"Authorization": f"Bearer {OPENWEBUI_JWT}", "Content-Type": "application/json"}
    model_id = "maria-reponse" if task == "reponse_client" else "maria-relance"
    async with httpx.AsyncClient(base_url=OPENWEBUI_BASE_URL, timeout=30.0) as c:
        r = await c.post("/api/v1/chats/new", headers=headers, json={
            "model": model_id, "title": f"Maria — {task}",
            "messages": [{"role": "user", "content": recap}],
        })
        if r.status_code != 200:
            return None
        chat_id = r.json().get("id")
        if not chat_id:
            return None
        # Déclenche la complétion (le modèle répond dans la conversation existante).
        await c.post("/api/chat/completions", headers=headers, json={
            "model": model_id, "chat_id": chat_id, "stream": False,
            "messages": [{"role": "user", "content": recap}],
        })
        return chat_id


# ── Endpoint OpenAI-compatible (Open WebUI) ─────────────────────────────────
@app.get("/v1/models")
async def openai_models():
    return {
        "object": "list",
        "data": [
            {"id": m["id"], "object": "model", "owned_by": "ets-maria",
             "name": m["name"]} for m in OPENAI_MODELS
        ],
    }


@app.post("/v1/chat/completions")
async def openai_chat(req: OpenAIChatRequest):
    if req.model not in DIRECT_MODELS:
        # maria-reponse / maria-relance : uniquement via /api/handoff (sélecteur).
        return JSONResponse(
            status_code=400,
            content={"error": {"message": "Ce preset nécessite le sélecteur guidé "
                                            "(Maria Agent). Passez par l'UI de sélection."}},
        )
    task = DIRECT_MODELS[req.model]
    user_text = ""
    for m in reversed(req.messages):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            user_text = m["content"]
            break
    if task == "mail_libre" and not user_text.strip():
        return JSONResponse(status_code=422,
                            content={"error": {"message": "Décrivez le mail à rédiger."}})

    catalog_rows = catalog.search(user_text)
    messages = prompts.build_messages(task, user_text, [], catalog.format_rows(catalog_rows))

    payload = {"model": HERMES_MODEL, "messages": messages, "stream": req.stream}
    if not req.stream:
        try:
            r = await app.state.http.post(
                "/v1/chat/completions", json={**payload, "stream": False},
                headers=app.state.hermes_headers,
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError as e:
            return JSONResponse(status_code=502,
                                content={"error": {"message": f"Gateway Hermes injoignable : {type(e).__name__}"}})
        return {
            "id": "chatcmpl-maria", "object": "chat.completion", "model": req.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                         "finish_reason": "stop"}], "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }

    def _chunk(delta=None, finish=None):
        return {
            "id": "chatcmpl-maria", "object": "chat.completion.chunk", "model": req.model,
            "choices": [{"index": 0, "delta": delta or {}, "finish_reason": finish}],
        }

    async def stream():
        yield f"data: {json.dumps(_chunk({'role': 'assistant'}))}\n\n"
        try:
            async with app.state.http.stream(
                "POST", "/v1/chat/completions", json=payload, headers=app.state.hermes_headers
            ) as r:
                if r.status_code != 200:
                    body = (await r.aread()).decode("utf-8", "replace")[:300]
                    yield f"data: {json.dumps({'error': f'Gateway Hermes {r.status_code}: {body}'})}\n\n"
                    return
                async for line in r.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = (chunk.get("choices") or [{}])[0].get("delta", {}).get("content")
                    if delta:
                        yield f"data: {json.dumps(_chunk({'content': delta}))}\n\n"
        except httpx.HTTPError as e:
            yield f"data: {json.dumps({'error': f'Gateway Hermes injoignable : {type(e).__name__}'})}\n\n"
        yield f"data: {json.dumps(_chunk(finish='stop'))}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("MARIA_HOST", "127.0.0.1"),
                port=int(os.environ.get("MARIA_PORT", "8321")))
