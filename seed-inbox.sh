#!/usr/bin/env bash
# Rejoue data/inbox/*.eml dans la boîte mail de démo (Mailpit).
# Idempotent : purge l'inbox avant d'envoyer. Ports loopback publiés par compose.
set -euo pipefail
cd "$(dirname "$0")"

UI="http://127.0.0.1:8025"
SMTP_HOST="127.0.0.1"
SMTP_PORT="1025"

# Attendre que Mailpit réponde (jusqu'à ~30 s)
for i in $(seq 1 30); do
  curl -sf "$UI/api/v1/info" >/dev/null 2>&1 && break
  if [ "$i" = 30 ]; then echo "ERREUR : Mailpit injoignable sur $UI (conteneur up ?)"; exit 1; fi
  sleep 1
done

# Purge (rejeu propre à chaque run)
curl -s -X DELETE "$UI/api/v1/messages" >/dev/null

# Envoi des .eml via SMTP réel
python3 - "$SMTP_HOST" "$SMTP_PORT" <<'PY'
import sys, glob, smtplib
from email import message_from_binary_file
host, port = sys.argv[1], int(sys.argv[2])
files = sorted(glob.glob("data/inbox/*.eml"))
if not files:
    print("Aucun .eml dans data/inbox/"); sys.exit(1)
s = smtplib.SMTP(host, port, timeout=10)
for p in files:
    with open(p, "rb") as f:
        s.send_message(message_from_binary_file(f))
    print("  envoyé:", p)
s.quit()
print(f"{len(files)} mails -> Mailpit")
PY

echo "Inbox de démo prête : $UI"
