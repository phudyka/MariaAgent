# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

Réponds en français dans ce dépôt (projet francophone, ETS Maria).

## Ce qu'est ce dépôt

Démo d'**agent commercial local sécurisé** : rédaction de brouillons de mails
(réponse client, relance devis, mail libre) pour ETS Maria (pisciniste). Tout
tourne en local via Docker — aucune inférence externe. Ce n'est pas du code
applicatif : c'est de la **configuration d'infrastructure** (compose, proxy,
persona, données mock). Le « produit » est la topologie sécurisée + le persona,
pas un service qu'on développe.

Principe directeur, présent partout : **on ne fait pas confiance au modèle, on
contrôle ses capacités au niveau de l'infra.** Un mail client collé peut
contenir une injection de prompt ; même un modèle compromis ne doit avoir aucun
chemin réseau pour exfiltrer des données.

## Commandes

```bash
# Build de l'image Hermes (préalable, depuis l'install git locale)
docker build -t hermes-agent:local ~/.local/opt/hermes-agent

# SEUL point d'entrée pour démarrer : fail-fast clé, up, pull modèle, checklist
./setup.sh

# Éval anti-invention (2 cas : prix absent -> [À COMPLÉTER], délai non inventé)
./eval.sh

docker compose logs -f hermes          # logs d'un service
docker compose down                    # arrêt
```

**Ne jamais démarrer par `docker compose up -d` seul** — il saute le garde-fou
clé et démarrerait avec `MARIA_API_KEY=change-me-in-prod`. Toujours
`./setup.sh`.

Vérif d'étanchéité réseau (doit **échouer**, sinon fuite). `nslookup` n'est pas
dans l'image `hermes` — tester la socket sortante directement :

```bash
docker compose exec hermes python3 -c \
  "import socket; socket.create_connection(('1.1.1.1',443),timeout=5)"
# attendu : échec (OSError) = aucune route sortante = scellé
```

## Architecture (le non-évident)

Quatre conteneurs, deux réseaux. Flux d'une requête employé :

```
employé :3000 → open-webui (embed + retrieve top-k RAG, injecte le contexte)
             → hermes:8642/v1 (gateway, persona + skills) → ollama:11434 (modèle)
```

Points qui demandent de lire plusieurs fichiers pour être compris :

1. **Le métier vit hors du dépôt à l'exécution.** `hermes/SOUL.md` et
   `hermes/skills/` sont la _source_, mais `setup.sh` les **copie** dans
   `~/.hermes/`, seul répertoire monté dans le conteneur (`/opt/data`). Éditer
   `hermes/SOUL.md` dans le dépôt **n'a aucun effet** tant que `setup.sh` (ou un
   `cp` manuel) ne l'a pas recopié. `~/.hermes/config.yaml` n'est _pas_ écrasé
   s'il existe déjà (voir `setup.sh`) — le modifier demande une édition directe
   ou une suppression préalable.

2. **Le RAG n'est pas un tool du modèle.** C'est Open WebUI qui embed les
   données et injecte le contexte _avant_ d'appeler Hermes. Le toolset du modèle
   est volontairement `[skills, todo, memory]` (voir
   `hermes/config.yaml.example`, `platform_toolsets.api_server`). Aucun tool
   `web`/`file`/`terminal` : une injection n'a rien à détourner. **Ne jamais
   élargir ce toolset.**

3. **`data/` est monté `:ro` mais n'est pas la base interrogée.** Les fichiers
   sont uploadés _manuellement_ via l'UI dans la collection « Knowledge » (store
   vectoriel dans le volume `open-webui`, en lecture-écriture). Modifier `data/`
   exige un ré-upload dans l'UI pour changer les réponses.

4. **`eval.sh` court-circuite le RAG** : il tape `hermes:8642` en direct depuis
   le conteneur `open-webui`, sans contexte injecté. Il teste donc le
   comportement anti-invention du modèle _seul_ (doit produire `[À COMPLÉTER]`,
   ne pas inventer prix/délai), pas la qualité du RAG.

## Invariants de sécurité — ne pas casser

Ces propriétés sont le cœur de la démo. Toute modif du `docker-compose.yml`, du
`proxy/` ou de `config.yaml.example` doit les préserver :

- **Un seul port produit publié** : `open-webui:3000`, derrière `WEBUI_AUTH`.
  `hermes` et `ollama` ne sont **jamais** exposés à l'hôte/LAN. (Exception démo
  assumée : `mailpit` publie `8025`/`1025` en **loopback seul** — outil de démo
  hors produit, sur `net_publish` masquerade off = aucun egress ; Maria ne s'y
  connecte pas, toolset figé.)
- **`net_internal` est `internal: true`** (aucune route internet directe).
  `egress-proxy` est le **seul** service sur `net_egress`, donc le seul chemin
  vers internet. Tout passe par lui via `HTTP_PROXY`.
- **`proxy/filter` est une allowlist** (`FilterDefaultDeny Yes`) : registre
  Ollama, huggingface (embedding model), DuckDuckGo (web search), domaine(s)
  fournisseur. Ajouter un domaine = élargir la surface de fuite — le justifier.
  Regex **ancrées** (`^…$`) obligatoires.
- **Toolset `api_server` figé** à `[skills, todo, memory]` (cf. point 2).

## Persona & règles métier

`hermes/SOUL.md` (persona) et `hermes/skills/mails-commerciaux/SKILL.md`
imposent des **règles anti-invention absolues** : aucun prix / référence / stock
/ délai / engagement qui ne vienne du contexte fourni ; donnée manquante →
`[À COMPLÉTER : nature]`. Brouillons en **texte brut** (jamais de Markdown). Ces
règles sont le contrat que `eval.sh` vérifie — les modifier peut faire échouer
l'éval.

## Durcissement production (hors périmètre démo)

Chiffrement at-rest, RBAC, audit log, connecteur Sage 100 réel, ingestion RAG
read-only, blocage DNS résiduel : documentés dans
`docs/superpowers/specs/2026-07-20-securite-prod.md`. Ne pas les improviser ici.
