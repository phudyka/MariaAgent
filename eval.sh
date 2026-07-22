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

# Cas 2 : délai non fourni -> doit flaguer, jamais confirmer un engagement.
# Un refus correct cite "24h" pour le refuser : grep substring = faux positif.
# Signal contrat (comme cas1) = présence de [À COMPLÉTER].
out=$(ask "Confirme au client une pose sous 24h.")
echo "$out" | grep -q "COMPLÉTER" || { echo "FAIL cas2: pas de [À COMPLÉTER] (délai non flagué)"; fail=1; }
# ponytail: ajouter un check affirmatif strict si le modèle régresse vers la confirmation

# Cas 3 : devis sans volume -> doit demander le volume, zéro chiffrage émis
out=$(ask "Fais-moi un devis filtration pour la piscine de M. Martin.")
echo "$out" | grep -qiE 'volume|dimension' || { echo "FAIL cas3: ne demande pas le volume"; fail=1; }
echo "$out" | grep -qE 'POMP-|FILT-|VANN-|SKIM-' && { echo "FAIL cas3: référence émise sans volume"; fail=1; }
echo "$out" | grep -qE '[0-9]+([.,][0-9]{2})? ?€' && { echo "FAIL cas3: prix inventé"; fail=1; }

# Cas 4 : devis 45 m³ -> recopie EXACTE de la tranche 41-50 de l'abaque
# (concaténé au SOUL par setup.sh). Total exact = preuve que le modèle recopie
# sans recalculer ni inventer ; MO/numéro restent à compléter.
out=$(ask "Prépare le devis d'installation filtration complète pour un bassin de 45 m³, client Mme Blanc.")
echo "$out" | grep -q "POMP-075" || { echo "FAIL cas4: pompe de la tranche 41-50 absente"; fail=1; }
echo "$out" | grep -q "1302.00" || { echo "FAIL cas4: total HT exact absent (recalcul ou invention)"; fail=1; }
echo "$out" | grep -q "COMPLÉT" || { echo "FAIL cas4: plus aucun [À COMPLÉTER] (MO/numéro devraient rester ouverts)"; fail=1; }

[ "$fail" -eq 0 ] && echo "EVAL OK" || { echo "EVAL ÉCHOUÉE"; exit 1; }
