#!/usr/bin/env bash
set -euo pipefail
source .env

ask() {  # $1 = prompt ; renvoie le texte de la réponse
  docker compose exec -T open-webui python3 -c "
import json, urllib.request

payload = json.dumps({
    'model': 'maria-agent',
    'messages': [{'role': 'user', 'content': '''$1'''}],
}).encode()

req = urllib.request.Request(
    'http://hermes:8642/v1/chat/completions',
    data=payload,
    headers={
        'Authorization': 'Bearer $MARIA_API_KEY',
        'Content-Type': 'application/json',
    },
)
with urllib.request.urlopen(req) as resp:
    body = json.load(resp)
print(body['choices'][0]['message']['content'])
"
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
