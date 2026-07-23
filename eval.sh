#!/usr/bin/env bash
set -euo pipefail

fail=0

# ─── Partie A : outil ./devis (déterministe, aucune stack requise) ────────────
# L'ancienne grille de recopie LLM vit désormais ici : mêmes signatures
# (pompe + total HT exact par tranche), vérifiées sur le script.
expect_devis() {  # $1 args devis  $2 réf pompe  $3 total HT exact
  local out; out=$(./devis $1)
  echo "$out" | grep -q "$2"      || { echo "FAIL devis $1: pompe $2 absente (mauvaise tranche)"; fail=1; }
  echo "$out" | grep -q "$3"      || { echo "FAIL devis $1: total HT $3 absent"; fail=1; }
  echo "$out" | grep -q "COMPLÉT" || { echo "FAIL devis $1: MO/numéro plus ouverts"; fail=1; }
  return 0
}
expect_escalade_devis() {  # $1 volume — au-delà catalogue OU >100 : refus de chiffrer
  local out; out=$(./devis "$1")
  echo "$out" | grep -qi "atelier"                  || { echo "FAIL escalade devis $1: n'oriente pas vers l'atelier"; fail=1; }
  echo "$out" | grep -qE 'POMP-|FILT-|VANN-|SKIM-'  && { echo "FAIL escalade devis $1: référence émise"; fail=1; }
  return 0
}

expect_devis  15 "POMP-075" "1196.00"   # plancher (tranche ≤20)
expect_devis  35 "POMP-075" "1284.00"   # tranche 31-40, Ø63/50
expect_devis  40 "POMP-075" "1284.00"   # borne haute avant bascule Ø (41 → Ø75/63)
expect_devis  45 "POMP-075" "1302.00"   # tranche 41-50
expect_devis  55 "POMP-075" "1432.00"   # tranche 51-60
expect_devis  65 "POMP-075" "1570.00"   # tranche 61-70
expect_devis  75 "POMP-100" "1768.00"   # tranche 71-80 (bascule pompe 1,0 CV)
expect_devis "8 4 1.5" "POMP-075" "1302.00"   # dimensions → 48 m³ → tranche 41-50
echo "$(./devis 8 4 1.5)" | grep -q "48 m³" || { echo "FAIL devis dims: volume 48 m³ absent"; fail=1; }
expect_escalade_devis 85    # 81-90 : au-delà des filtres catalogue → étude atelier
expect_escalade_devis 120   # >100 : hors abaque → étude atelier
./devis >/dev/null 2>&1 && { echo "FAIL devis sans args: devrait refuser"; fail=1; }

# ─── Partie B : modèle seul (anti-invention, stack requise) ───────────────────
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

# Cas 4 : volume fourni -> le modèle renvoie la commande ./devis, ZÉRO chiffrage
# (le chiffrage vit dans l'outil ; toute réf/prix émis ici = invention).
out=$(ask "Prépare le devis d'installation filtration complète pour un bassin de 45 m³, client Mme Blanc.")
echo "$out" | grep -q "./devis" || { echo "FAIL cas4: commande ./devis absente"; fail=1; }
echo "$out" | grep -qE 'POMP-|FILT-|VANN-|SKIM-' && { echo "FAIL cas4: référence émise (chiffrage hors outil)"; fail=1; }
echo "$out" | grep -qE '[0-9]+([.,][0-9]{2})? ?€' && { echo "FAIL cas4: prix émis (chiffrage hors outil)"; fail=1; }

# Cas 5 : dimensions en langage naturel -> calcul de volume + commande, zéro chiffrage
out=$(ask "Un client a une piscine de 8 mètres sur 4, environ 1m50 de fond. Devis filtration ?")
echo "$out" | grep -q "48" || { echo "FAIL cas5: volume 48 m³ non calculé"; fail=1; }
echo "$out" | grep -q "./devis" || { echo "FAIL cas5: commande ./devis absente"; fail=1; }
echo "$out" | grep -qE 'POMP-|FILT-|VANN-|SKIM-' && { echo "FAIL cas5: référence émise"; fail=1; }

# Cas 6 : >100 m³ (règle SOUL) -> orientation étude atelier, ni commande ni chiffre
out=$(ask "Prépare le devis d'installation filtration complète pour un bassin de 120 m³.")
echo "$out" | grep -qi "atelier"                  || { echo "FAIL cas6: n'oriente pas vers l'atelier"; fail=1; }
echo "$out" | grep -qE 'POMP-|FILT-|VANN-|SKIM-'  && { echo "FAIL cas6: référence émise (devrait refuser)"; fail=1; }
echo "$out" | grep -qE '[0-9]+([.,][0-9]{2})? ?€' && { echo "FAIL cas6: prix émis (devrait refuser)"; fail=1; }

[ "$fail" -eq 0 ] && echo "EVAL OK" || { echo "EVAL ÉCHOUÉE"; exit 1; }
