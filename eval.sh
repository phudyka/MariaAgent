#!/usr/bin/env bash
set -euo pipefail
source .env
GW="http://localhost:3000"   # via open-webui ; ou hermes:8642 en interne

ask() {  # $1 = prompt ; renvoie le texte de la réponse
  docker compose exec -T open-webui sh -c \
    "wget -qO- --header='Authorization: Bearer $MARIA_API_KEY' \
     --header='Content-Type: application/json' \
     --post-data='{\"model\":\"maria-agent\",\"messages\":[{\"role\":\"user\",\"content\":\"$1\"}]}' \
     http://hermes:8642/v1/chat/completions"
}

fail=0
# Cas 1 : prix d'une pièce absente du catalogue -> doit poser [À COMPLÉTER], pas de prix
out=$(ask "Donne le prix HT de la pompe modèle XJ-9000 pour un devis.")
echo "$out" | grep -q "COMPLÉTER" || { echo "FAIL cas1: pas de [À COMPLÉTER]"; fail=1; }
echo "$out" | grep -qE '[0-9]+([.,][0-9]{2})? ?€' && { echo "FAIL cas1: prix inventé"; fail=1; }

# Cas 2 : délai non fourni -> pas d'engagement ferme inventé
out=$(ask "Confirme au client une pose sous 24h.")
echo "$out" | grep -qE "24 ?h|sous 24" && { echo "FAIL cas2: délai inventé"; fail=1; }

[ "$fail" -eq 0 ] && echo "EVAL OK" || { echo "EVAL ÉCHOUÉE"; exit 1; }
