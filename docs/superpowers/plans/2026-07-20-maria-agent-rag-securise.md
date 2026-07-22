# Agent Maria RAG sécurisée — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Démo POC d'un agent commercial local pour ETS Maria : RAG local sur
données mockées, servi par Ollama, orchestré par Hermes, exposé via Open WebUI
uniquement, avec isolation réseau garantissant l'absence d'exfiltration.

**Architecture:** 4 conteneurs sur 2 réseaux docker. `ollama` + `hermes` +
`open-webui` sur `net_internal` (`internal: true`, aucune route internet
directe) ; `egress-proxy` (tinyproxy, allowlist) est le seul pont vers internet.
Le RAG est natif Open WebUI ; le modèle n'a aucun tool sortant. Seul le port
`open-webui:3000` est publié.

**Tech Stack:** Docker Compose, Ollama (qwen3:4b-instruct-2507-q4_K_M), Hermes
Agent (gateway OpenAI-compatible), Open WebUI (RAG + web search natifs),
tinyproxy (egress allowlist), Bash.

## Global Constraints

- Aucune inférence externe : tout le calcul (modèle, embeddings) est local.
- `context_length` = **65536** partout (minimum Hermes). Ollama :
  `OLLAMA_FLASH_ATTENTION=1` + `OLLAMA_KV_CACHE_TYPE=q4_0` pour tenir en 8 Go
  VRAM (GTX 1080).
- Toolset modèle = `[skills, todo, memory]` — jamais élargir à
  `web`/`file`/`terminal`.
- Un seul port publié sur l'hôte : `open-webui` → `3000`. `hermes:8642` jamais
  publié.
- Données Maria montées `:ro`.
- Le seul chemin internet est `egress-proxy`, `FilterDefaultDeny Yes` (allowlist
  stricte).
- Setup échoue si `MARIA_API_KEY` vaut encore `change-me-in-prod`.
- Français partout, texte brut pour les brouillons (règles `SOUL.md`
  conservées).
- Images pinnées (pas de `:latest` / `:main` flottant) pour la reproductibilité.

---

## File Structure

- `docker-compose.yml` (modifier) — 4 services, 2 réseaux, aucun port sauf 3000.
- `proxy/tinyproxy.conf` (créer) — proxy egress.
- `proxy/filter` (créer) — allowlist de domaines.
- `hermes/config.yaml.example` (modifier) — base_url, context, commentaires.
- `.env.example` (modifier) — clé + note fail-fast.
- `.gitignore` (modifier) — retirer réf morte `agent/`.
- `hermes/skills/mails-commerciaux/SKILL.md` (modifier) — wording RAG.
- `data/entreprise.md`, `data/catalogue.md`, `data/clients/*.md`,
  `data/devis/*.md`, `data/mails/*.md` (créer) — mocks Maria.
- `setup.sh` (créer) — fail-fast clé, up infra, pull modèle via proxy, checklist
  Open WebUI.
- `eval.sh` (créer) — mini-éval anti-invention.
- `README.md` (modifier) — réécriture cohérente.
- `docs/superpowers/specs/2026-07-20-securite-prod.md` (créer) — durcissement
  prod.

---

### Task 1: Topologie réseau sécurisée + egress-proxy

**Files:**

- Modify: `docker-compose.yml`
- Create: `proxy/tinyproxy.conf`, `proxy/filter`

**Interfaces:**

- Produces: réseaux `net_internal` (internal), `net_egress` (bridge) ; service
  `egress-proxy` joignable en `http://egress-proxy:8888` depuis `net_internal`.

- [ ] **Step 1: Créer `proxy/filter`** (allowlist de domaines, un motif par
      ligne)

```
^registry\.ollama\.ai$
\.ollama\.ai$
^ollama\.com$
huggingface\.co$
^cdn-lfs\.huggingface\.co$
# domaine fournisseur démo (web search) — à ajuster
^www\.hayward-pool\.fr$
```

- [ ] **Step 2: Créer `proxy/tinyproxy.conf`**

```
Port 8888
Listen 0.0.0.0
Timeout 600
FilterDefaultDeny Yes
Filter "/etc/tinyproxy/filter"
FilterExtended On
FilterURLs Off
Allow 0.0.0.0/0
LogLevel Info
```

- [ ] **Step 3: Réécrire `docker-compose.yml`** (topologie complète)

```yaml
# Agent commercial local ETS Maria — démo POC 100 % local.
# Sécurité par la topologie : ollama/hermes/open-webui sur net_internal
# (internal: true, aucune route internet directe). egress-proxy est le SEUL
# pont vers internet, restreint par allowlist. Un seul port publié : 3000.

services:
  ollama:
    image: ollama/ollama:0.6.8
    container_name: maria-ollama
    restart: unless-stopped
    environment:
      - OLLAMA_CONTEXT_LENGTH=65536
      - OLLAMA_FLASH_ATTENTION=1
      - OLLAMA_KV_CACHE_TYPE=q4_0
      # ollama pull passe par le seul canal egress autorisé (registre Ollama).
      - HTTP_PROXY=http://egress-proxy:8888
      - HTTPS_PROXY=http://egress-proxy:8888
      - NO_PROXY=localhost,127.0.0.1,hermes,open-webui
    volumes:
      - ollama_models:/root/.ollama
    networks: [net_internal]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  hermes:
    image: hermes-agent:local
    container_name: maria-hermes
    restart: unless-stopped
    depends_on: [ollama]
    volumes:
      - ~/.hermes:/opt/data
    environment:
      - HERMES_UID=1000
      - HERMES_GID=1000
      # Bind 0.0.0.0 DANS le conteneur (joignable par open-webui sur net_internal).
      # Aucun port publié + réseau sans egress => pas une exposition.
      - API_SERVER_HOST=0.0.0.0
      - API_SERVER_KEY=${MARIA_API_KEY:?MARIA_API_KEY manquante — copier .env.example vers .env}
    command: ["gateway", "run"]
    networks: [net_internal]

  open-webui:
    image: ghcr.io/open-webui/open-webui:v0.6.5
    container_name: maria-open-webui
    restart: unless-stopped
    depends_on: [hermes]
    ports:
      - "3000:8080" # SEUL port publié
    environment:
      - WEBUI_AUTH=true
      - ENABLE_COMMUNITY_FEATURES=false
      - WEBUI_BANNERS=false
      - OPENAI_API_BASE_URL=http://hermes:8642/v1
      - OPENAI_API_KEY=${MARIA_API_KEY:?MARIA_API_KEY manquante}
      # RAG natif : embeddings locaux.
      - RAG_EMBEDDING_ENGINE=
      - RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
      # Web contrôlé : recherche activée, sortie forcée par le proxy allowlist.
      - ENABLE_RAG_WEB_SEARCH=true
      - RAG_WEB_SEARCH_ENGINE=duckduckgo
      - HTTP_PROXY=http://egress-proxy:8888
      - HTTPS_PROXY=http://egress-proxy:8888
      - NO_PROXY=localhost,127.0.0.1,hermes,ollama
    volumes:
      - open-webui:/app/backend/data
    networks: [net_internal]

  egress-proxy:
    image: monokal/tinyproxy:latest
    container_name: maria-egress
    restart: unless-stopped
    command: ["ANY"]
    volumes:
      - ./proxy/tinyproxy.conf:/etc/tinyproxy/tinyproxy.conf:ro
      - ./proxy/filter:/etc/tinyproxy/filter:ro
    networks: [net_internal, net_egress] # SEUL service à toucher net_egress

networks:
  net_internal:
    internal: true
  net_egress:
    driver: bridge

volumes:
  ollama_models:
  open-webui:
```

- [ ] **Step 4: Vérifier la config compose**

Run: `docker compose config >/dev/null && echo OK` Expected: `OK` (pas d'erreur
de parsing). Note : `MARIA_API_KEY` doit être exportée ou dans `.env` (voir Task
2).

- [ ] **Step 5: Vérifier l'allowlist du proxy** (démarrer proxy seul)

```bash
echo "MARIA_API_KEY=test-key-$(openssl rand -hex 8)" > .env
docker compose up -d egress-proxy
# Domaine hors allowlist => refusé
docker compose exec egress-proxy sh -c "wget -qO- -e use_proxy=yes -e http_proxy=http://127.0.0.1:8888 http://example.com" ; echo "exit=$?"
```

Expected: échec (exit non nul) / réponse "Filtered" — example.com **bloqué**.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml proxy/
git commit -m "feat: topologie réseau isolée + egress-proxy allowlist"
```

---

### Task 2: Config Hermes & compose cohérents + fail-fast clé

**Files:**

- Modify: `hermes/config.yaml.example`, `.env.example`, `.gitignore`

**Interfaces:**

- Consumes: services de Task 1.
- Produces: gateway Hermes joignable en `http://hermes:8642/v1` avec
  `Authorization: Bearer $MARIA_API_KEY`.

- [ ] **Step 1: Corriger `hermes/config.yaml.example`**

  - L9 `base_url` → `"http://ollama:11434/v1"` (nom de service, pas 127.0.0.1).
  - L11 `context_length: 65536` — garder, commentaire : « aligné sur
    `OLLAMA_CONTEXT_LENGTH`, KV q4_0 + flash attention ».
  - L2 : reformuler « À copier vers `~/.hermes/config.yaml` (monté dans le
    conteneur hermes en `/opt/data`) ».
  - L49-52 : remplacer le bloc « multi-agents / proxy `agent/app.py` /
    assemblage déterministe » par :

```
# api_server = ce que voient les employés via Open WebUI. Le CONTEXTE métier
# (client, devis, catalogue, mails) est injecté par le RAG natif d'Open WebUI,
# pas par un tool donné au modèle. On ne donne AUCUN tool web/file/terminal au
# modèle : un mail client collé peut contenir une injection de prompt.
# Ne jamais élargir api_server à [terminal, file, web].
```

- L63 : `host: "0.0.0.0"` + commentaire :

```
host: "0.0.0.0"   # bind interne au conteneur (joignable par open-webui
                  # sur net_internal). Port NON publié + réseau sans
                  # egress => pas une exposition LAN.
```

- [ ] **Step 2: Mettre à jour `.env.example`**

```
# Clé d'API du gateway Hermes, partagée par Open WebUI et le gateway.
# Générer une vraie valeur : openssl rand -hex 24
# Le setup REFUSE de démarrer si la valeur reste 'change-me-in-prod'.
MARIA_API_KEY=change-me-in-prod
```

- [ ] **Step 3: Nettoyer `.gitignore`** — retirer la ligne `agent/data/maria.db`
      (dossier `agent/` supprimé). Ajouter `data/` reste versionné (mocks), mais
      ignorer un éventuel index : garder `.env`, `__pycache__/`, `*.log`,
      `*.pyc`, `.venv/`.

- [ ] **Step 4: Vérifier la cohérence (grep)**

Run:
`grep -rn "127.0.0.1:11434\|agent/\|multi-agent\|proxy agent" hermes/ .gitignore ; echo "exit=$?"`
Expected: aucune correspondance (`exit=1`).

- [ ] **Step 5: Commit**

```bash
git add hermes/config.yaml.example .env.example .gitignore
git commit -m "fix: config Hermes cohérente (base_url, context, bind), refs mortes retirées"
```

---

### Task 3: Données mock Maria (RAG)

**Files:**

- Create: `data/entreprise.md`, `data/catalogue.md`, `data/clients/durand.md`,
  `data/devis/2024-118.md`, `data/mails/durand-2024.md` (+ 2-3 autres
  clients/devis/mails pour le volume).

**Interfaces:**

- Produces: corpus RAG cohérent. **Le scénario de démo exige** : client « Durand
  », devis « 2024-118 », références catalogue citées dans le devis.

- [ ] **Step 1: `data/entreprise.md`** — fiche + bloc signature

```
# ETS Maria — pisciniste
Depuis 1937, région niçoise. Vente, installation, entretien de piscines.
Adresse : 12 avenue des Oliviers, 06000 Nice. Tél : 04 93 00 00 00.

Bloc signature (à reprendre dans les mails) :
Cordialement,
L'équipe ETS Maria
04 93 00 00 00 — contact@ets-maria.fr
```

- [ ] **Step 2: `data/catalogue.md`** — lignes
      `- REF | nom | marque | prix € HT | stock | specs`

```
# Catalogue pièces (extrait)
- POMP-150 | Pompe filtration 1,5 CV | Hayward | 420.00 | 6 | mono 230V, 21 m³/h
- FILT-500 | Filtre à sable Ø500 | Hayward | 310.00 | 3 | 10 m³/h, vanne 6 voies
- LINER-75 | Liner 75/100e bleu | AstralPool | 28.00 | 40 | prix au m², uni
- ROBOT-PX | Robot nettoyeur PoolX | Zodiac | 890.00 | 2 | fond+parois, câble 15 m
```

- [ ] **Step 3: `data/clients/durand.md`**

```
# Client : Durand, Jean-Pierre
Contact : jp.durand@example.com — 06 12 34 56 78
Adresse : 8 chemin des Mimosas, 06600 Antibes
Piscine : 8x4 m, liner, installée 2019 par ETS Maria.
Notes : client fidèle, entretien annuel. Sensible au délai.
```

- [ ] **Step 4: `data/devis/2024-118.md`**

```
# Devis 2024-118
Client : Durand, Jean-Pierre
Objet : remplacement pompe de filtration + robot
Date d'envoi : 2024-05-14
Lignes :
- POMP-150 | Pompe filtration 1,5 CV | 420.00 € HT
- ROBOT-PX | Robot nettoyeur PoolX | 890.00 € HT
Total : 1310.00 € HT
Statut : envoyé, sans réponse.
```

- [ ] **Step 5: `data/mails/durand-2024.md`**

```
# Fil mail — Durand 2024
[2024-05-10] Durand : "Ma pompe fait du bruit et le fond reste sale, que proposez-vous ?"
[2024-05-14] ETS Maria : "Devis 2024-118 envoyé (pompe POMP-150 + robot ROBOT-PX)."
```

- [ ] **Step 6: Ajouter 2 clients + 2 devis + 1 mail supplémentaires** (même
      format, noms différents) pour donner du volume au RAG et éviter que la
      seule réponse plausible soit Durand.

- [ ] **Step 7: Vérifier les références croisées**

Run: `grep -rl "2024-118" data/ && grep -rl "POMP-150" data/` Expected: le devis
et le catalogue se répondent (au moins `data/devis/2024-118.md` et
`data/catalogue.md`).

- [ ] **Step 8: Commit**

```bash
git add data/
git commit -m "feat: données mock Maria pour le RAG (scénario Durand/2024-118)"
```

---

### Task 4: setup.sh + préconfiguration Open WebUI

**Files:**

- Create: `setup.sh`

**Interfaces:**

- Consumes: Tasks 1-3.
- Produces: stack démarrée, modèle pullé, checklist Open WebUI affichée.

- [ ] **Step 1: Écrire `setup.sh`**

```bash
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
```

- [ ] **Step 2: Rendre exécutable + smoke test infra**

```bash
chmod +x setup.sh
./setup.sh
```

Expected : garde-fou clé OK, `docker compose up` sain, pull réussi, checklist
affichée.

- [ ] **Step 3: Vérifier le gateway répond** (après pull)

Run:

```bash
source .env
docker compose exec open-webui sh -c \
  "wget -qO- --header='Authorization: Bearer $MARIA_API_KEY' http://hermes:8642/v1/models"
```

Expected : JSON listant `maria-agent`.

- [ ] **Step 4: Vérifier l'isolation** (ollama n'a pas d'egress direct)

Run:
`docker compose exec ollama sh -c "wget -qO- --timeout=5 http://example.com" ; echo "exit=$?"`
Expected : échec (pas de route directe ; seul le proxy sort, et example.com est
hors allowlist).

- [ ] **Step 5: Commit**

```bash
git add setup.sh
git commit -m "feat: setup.sh (fail-fast clé, up, pull, checklist Open WebUI)"
```

---

### Task 5: Mini-éval anti-invention + wording RAG

**Files:**

- Create: `eval.sh`
- Modify: `hermes/skills/mails-commerciaux/SKILL.md`

**Interfaces:**

- Consumes: gateway de Task 4.

- [ ] **Step 1: Corriger `SKILL.md`** (L46-51) — remplacer « L'interface de
      l'entreprise enrichit chaque demande » par :

```
## Ce que le RAG fournit

Le RAG (recherche sémantique Open WebUI sur les données de l'entreprise)
injecte automatiquement les passages pertinents : fiche entreprise, fiche
client, devis, extraits catalogue, historique mails. Travailler exclusivement
à partir de ces éléments — ne rien inventer, ne pas chercher d'autres sources.
```

- [ ] **Step 2: Écrire `eval.sh`** (anti-invention : donnée absente =>
      `[À COMPLÉTER]`, aucun `€` inventé)

```bash
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
```

- [ ] **Step 3: Rendre exécutable + lancer**

```bash
chmod +x eval.sh
./eval.sh
```

Expected : `EVAL OK`. (Si un 4B échoue par intermittence, c'est le signal
documenté « modèle plus gros en prod » — noter, ne pas masquer.)

- [ ] **Step 4: Commit**

```bash
git add eval.sh hermes/skills/mails-commerciaux/SKILL.md
git commit -m "feat: mini-éval anti-invention + wording RAG dans le skill"
```

---

### Task 6: README + doc durcissement prod

**Files:**

- Modify: `README.md`
- Create: `docs/superpowers/specs/2026-07-20-securite-prod.md`

- [ ] **Step 1: Réécrire `README.md`** — sections : Stack (3+1 conteneurs, seul
      3000 publié), Sécurité par la topologie (schéma + les 5 invariants),
      Données mock & RAG, Démarrage (`cp .env.example .env` → éditer clé →
      `./setup.sh`), Scénario de démo, Personnalisation (`SOUL.md`, `data/`,
      allowlist proxy). Retirer toute mention de `8642` exposé au LAN et du
      proxy custom.

- [ ] **Step 2: Créer `docs/superpowers/specs/2026-07-20-securite-prod.md`** —
      reprendre la Section 4 de la spec : threat model (insider / outsider /
      modèle compromis), chiffrement at-rest (LUKS/gocryptfs), RBAC + audit,
      connecteur Sage 100 read-only + sync RAG, secrets manager, TLS/DLP/backup.
      Marquer clairement : **non implémenté dans la démo**.

- [ ] **Step 3: Vérifier l'absence de réfs mortes dans tout le repo**

Run:

```bash
grep -rn -E "8642:8642|127\.0\.0\.1:11434|agent/app\.py|WEB_SEARCH: \"false\"|enrichit chaque demande|change-me-in-prod" \
  --include='*.md' --include='*.yml' --include='*.example' --include='.gitignore' . | grep -v '\.venv' | grep -v 'docs/superpowers'
```

Expected : aucune correspondance (les refs mortes de l'audit ont disparu ; les
specs/plans qui les _citent_ sont exclus).

- [ ] **Step 4: Commit**

```bash
git add README.md docs/superpowers/specs/2026-07-20-securite-prod.md
git commit -m "docs: README cohérent + doc durcissement prod"
```

---

## Self-Review

**Spec coverage :**

- S1 (archi/réseau) → Task 1 (+ config bind Task 2). ✓
- S2 (données mock + RAG) → Task 3 + Task 4 (Knowledge). ✓
- S3 (persona anti-invention) → SOUL réutilisé (Task 4 checklist) + wording
  SKILL Task 5. ✓
- S4 (durcissement prod) → Task 6 Step 2. ✓
- S5 (setup léger) → Task 4. ✓
- S6 (scénario démo) → data Task 3 + README Task 6. ✓
- S7 (mini-éval) → Task 5. ✓
- S8 (nettoyage cohérence, 12 items) → Tasks 1/2/5/6 + grep de vérif Task 6
  Step 3. ✓

**Placeholder scan :** allowlist domaine fournisseur marquée « à ajuster »
(légitime, dépend du fournisseur réel) ; noms d'env vars Open WebUI
(`ENABLE_RAG_WEB_SEARCH`, `RAG_WEB_SEARCH_ENGINE`, `RAG_EMBEDDING_MODEL`) et
tags d'images à **confirmer contre les images pinnées** au démarrage (Task 4
Step 2 les exerce). Pas de TODO/TBD.

**Type consistency :** `MARIA_API_KEY`, service names (`ollama`, `hermes`,
`open-webui`, `egress-proxy`), ports (`8642` interne, `3000` publié, `8888`
proxy, `11434` ollama) cohérents entre toutes les tâches.
