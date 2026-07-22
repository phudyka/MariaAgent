#!/usr/bin/env bash
set -euo pipefail
source .env

ask() {  # $1 = prompt ; renvoie le texte de la réponse
  docker compose exec -T open-webui python3 -c "
import json, urllib.request

payload = json.dumps({
    'model': 'maria-agent',
    'messages': [{'role': 'user', 'content': '''$1'''}],
    'temperature': 0,  # régression reproductible : un run vert doit le rester
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

# --- Grille de sélection de tranche (axe FIDÉLITÉ, pas justesse de l'abaque) ---
# Chaque tranche a une signature : pompe + total HT EXACT. On vérifie que pour un
# volume donné le modèle recopie la BONNE tranche, sans recalcul ni invention.
# NB : tranches ≤20 et 21-30 partagent le même total (1196.00) — matériel
# identique dans l'abaque (smell de génération à valider avec Maria, cf. Peep).
expect_devis() {  # $1 volume  $2 réf pompe  $3 total HT exact
  local out; out=$(ask "Prépare le devis d'installation filtration complète pour un bassin de $1 m³.")
  echo "$out" | grep -q "$2"      || { echo "FAIL devis ${1}m³: pompe $2 absente (mauvaise tranche)"; fail=1; }
  echo "$out" | grep -q "$3"      || { echo "FAIL devis ${1}m³: total HT $3 absent (recalcul/invention)"; fail=1; }
  echo "$out" | grep -q "COMPLÉT" || { echo "FAIL devis ${1}m³: MO/numéro plus ouverts"; fail=1; }
  return 0
}
expect_escalade() {  # $1 volume — au-delà catalogue OU >100 : refus de chiffrer
  local out; out=$(ask "Prépare le devis d'installation filtration complète pour un bassin de $1 m³.")
  echo "$out" | grep -qi "atelier"                  || { echo "FAIL escalade ${1}m³: n'oriente pas vers l'atelier"; fail=1; }
  echo "$out" | grep -qE 'POMP-|FILT-|VANN-|SKIM-'  && { echo "FAIL escalade ${1}m³: référence chiffrée émise (devrait refuser)"; fail=1; }
  echo "$out" | grep -qE '[0-9]+([.,][0-9]{2})? ?€' && { echo "FAIL escalade ${1}m³: prix émis (devrait refuser)"; fail=1; }
  return 0
}

expect_devis  15 "POMP-075" "1196.00"   # plancher (tranche ≤20)
expect_devis  35 "POMP-075" "1284.00"   # tranche 31-40, Ø63/50
expect_devis  40 "POMP-075" "1284.00"   # borne haute avant bascule Ø (41 → Ø75/63)
expect_devis  55 "POMP-075" "1432.00"   # tranche 51-60
expect_devis  65 "POMP-075" "1570.00"   # dernière avant bascule pompe
expect_devis  71 "POMP-100" "1768.00"   # bascule pompe 0,75 → 1,0 CV (tranche 71-80)
expect_escalade 85    # 81-90 : au-delà des filtres catalogue → étude atelier
expect_escalade 120   # >100 (règle SOUL) : pas de devis, orientation atelier

[ "$fail" -eq 0 ] && echo "EVAL OK" || { echo "EVAL ÉCHOUÉE"; exit 1; }
