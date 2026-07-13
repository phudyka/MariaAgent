#!/usr/bin/env bash
# Installation de l'environnement Python de l'agent (machine de dev).
# Prérequis : python3 >= 3.11, binaire ollama déjà installé (voir DEPLOY_MARIA.md pour la prod).
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r agent/requirements.txt

# Base clients/devis mock (SQLite) — idempotent, --force pour régénérer
.venv/bin/python agent/seed_db.py

echo
echo "Environnement prêt. Modèle requis : ${MARIA_MODEL:-qwen3:4b-instruct-2507-q4_K_M}"
echo "  ollama pull ${MARIA_MODEL:-qwen3:4b-instruct-2507-q4_K_M}"
echo "Puis : scripts/run.sh"
