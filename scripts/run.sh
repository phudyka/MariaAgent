#!/usr/bin/env bash
# Lance la chaîne complète en local : Ollama → gateway Hermes Agent → proxy web.
# Hermétique : OLLAMA_NO_CLOUD interdit toute fonction cloud d'Ollama ;
# Hermes est configuré sans aucun provider cloud (~/.hermes/config.yaml).
set -euo pipefail

cd "$(dirname "$0")/.."

# ── 1. Ollama ────────────────────────────────────────────────────────────────
# Contexte 64k requis par Hermes Agent (minimum codé en dur). Sur GPU 8 Go,
# le KV cache doit être quantisé (q4_0) + flash attention, sinon débordement
# VRAM et bascule CPU (~3× plus lent). Validé : 59 tok/s, 100 % GPU, GTX 1080.
export OLLAMA_NO_CLOUD=1
export OLLAMA_CONTEXT_LENGTH="${OLLAMA_CONTEXT_LENGTH:-65536}"
export OLLAMA_FLASH_ATTENTION="${OLLAMA_FLASH_ATTENTION:-1}"
export OLLAMA_KV_CACHE_TYPE="${OLLAMA_KV_CACHE_TYPE:-q4_0}"

OLLAMA_BIN="${OLLAMA_BIN:-$(command -v ollama || echo "$HOME/.local/bin/ollama")}"
OLLAMA_URL="${MARIA_OLLAMA_URL:-http://127.0.0.1:11434}"

if ! curl -fsS --max-time 2 "$OLLAMA_URL/api/version" >/dev/null 2>&1; then
  echo "Démarrage d'Ollama…"
  nohup "$OLLAMA_BIN" serve > .ollama-serve.log 2>&1 &
  for i in $(seq 1 30); do
    curl -fsS --max-time 2 "$OLLAMA_URL/api/version" >/dev/null 2>&1 && break
    sleep 1
  done
fi
curl -fsS --max-time 2 "$OLLAMA_URL/api/version" >/dev/null || { echo "ERREUR : Ollama ne répond pas ($OLLAMA_URL) — voir .ollama-serve.log"; exit 1; }
echo "Ollama OK ($OLLAMA_URL)"

# ── 2. Gateway Hermes Agent ─────────────────────────────────────────────────
HERMES_BIN="${HERMES_BIN:-$(command -v hermes || echo "$HOME/.local/bin/hermes")}"
HERMES_URL="${MARIA_HERMES_URL:-http://127.0.0.1:8642}"

if ! curl -fsS --max-time 2 "$HERMES_URL/health" >/dev/null 2>&1; then
  echo "Démarrage du gateway Hermes…"
  nohup "$HERMES_BIN" gateway > .hermes-gateway.log 2>&1 &
  for i in $(seq 1 45); do
    curl -fsS --max-time 2 "$HERMES_URL/health" >/dev/null 2>&1 && break
    sleep 1
  done
fi
curl -fsS --max-time 2 "$HERMES_URL/health" >/dev/null || { echo "ERREUR : le gateway Hermes ne répond pas ($HERMES_URL) — voir .hermes-gateway.log"; exit 1; }
echo "Gateway Hermes OK ($HERMES_URL)"

# ── 3. Proxy web (UI employés) ──────────────────────────────────────────────
HOST="${MARIA_HOST:-127.0.0.1}"
PORT="${MARIA_PORT:-8321}"
echo "Agent : http://$HOST:$PORT"
exec .venv/bin/uvicorn app:app --app-dir agent --host "$HOST" --port "$PORT"
