#!/usr/bin/env bash
set -euo pipefail

# 1. Garde-fou clé
[ -f .env ] || { echo "ERREUR : copier .env.example vers .env et fixer MARIA_API_KEY."; exit 1; }
if grep -q '^MARIA_API_KEY=change-me-in-prod$' .env; then
  echo "ERREUR : MARIA_API_KEY est encore 'change-me-in-prod'."
  echo "  Générer : openssl rand -hex 24, puis coller dans .env"
  exit 1
fi

# 2. Config Hermes en place (montée dans le conteneur)
mkdir -p "$HOME/.hermes/skills"
[ -f "$HOME/.hermes/config.yaml" ] || cp hermes/config.yaml.example "$HOME/.hermes/config.yaml"
cp hermes/SOUL.md "$HOME/.hermes/SOUL.md"
cp -r hermes/skills/mails-commerciaux "$HOME/.hermes/skills/"

# 3. Démarrer la stack
docker compose up -d

# 4. Pull du modèle (via egress-proxy, allowlist registre Ollama)
echo "Pull du modèle (une fois, ~2-4 Go)…"
docker compose exec ollama ollama pull qwen3:4b-instruct-2507-q4_K_M

cat <<'EOF'

=== Préconfiguration Open WebUI (http://localhost:3000) ===
1. Créer le compte de service (première connexion = admin).
2. Workspace > Models > créer "maria-agent" :
   - Base model : maria-agent (gateway Hermes, déjà listé)
   - System prompt : coller le contenu de hermes/SOUL.md
3. Workspace > Knowledge > "Maria" > uploader tout le dossier data/.
4. Rattacher la collection "Maria" au modèle "maria-agent".
5. Settings > Web Search : activé (déjà via env), moteur duckduckgo.
Prêt.
EOF
