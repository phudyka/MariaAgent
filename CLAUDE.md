# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

Réponds en français dans ce dépôt (projet francophone, ETS Maria).

## Ce qu'est ce dépôt

Démo d'**agent commercial sécurisé** : génération de devis d'installation de
filtration (dimensionnement par abaque pré-calculé) et, en secondaire,
brouillons de mails (réponse client, relance devis, mail libre) pour ETS Maria
(pisciniste). Interface/RAG/orchestration en local via Docker ; **inférence via
l'API Mistral** (free tier, `mistral-small-latest` 24B Apache 2.0) — modèle
choisi pour être exactement ce qu'un Mac mini (M4 Pro 48 Go, cible d'achat) fera
tourner en local via Ollama ; tester la cible 24 Go = `open-mistral-nemo` (12B),
bascule 1 ligne dans `~/.hermes/config.yaml`. `api.mistral.ai` est le seul
domaine d'inférence de l'allowlist. Mode 100 % local v1 : profil compose `local`
(ollama). Ce n'est pas du code applicatif : c'est de la **configuration
d'infrastructure** (compose, proxy, persona, données mock). Le « produit » est
la topologie sécurisée + le persona, pas un service qu'on développe. Free tier
Mistral = requêtes utilisables pour l'entraînement : données de démo seulement,
jamais de vrais mails clients.

Principe directeur, présent partout : **on ne fait pas confiance au modèle, on
contrôle ses capacités au niveau de l'infra.** Un mail client collé peut
contenir une injection de prompt ; même un modèle compromis ne doit avoir aucun
chemin réseau pour exfiltrer des données.

## Commandes

```bash
# Build de l'image Hermes (préalable, depuis l'install git locale)
docker build -t hermes-agent:local ~/.local/opt/hermes-agent

# SEUL point d'entrée pour démarrer : fail-fast clés (MARIA_API_KEY,
# MISTRAL_API_KEY), up, checklist. Plus aucun pull de modèle par défaut.
./setup.sh

# Éval anti-invention (4 cas : prix absent, délai non inventé, devis sans
# volume -> question, devis sans abaque -> zéro réf/prix de mémoire)
./eval.sh

# Régénérer l'abaque de dimensionnement (one-shot, poste dev — moteur Peep
# requis dans ../Peep ; jamais exécuté chez Maria), puis redéployer le SOUL
# (setup.sh concatène SOUL + abaque) et recharger hermes
npx -y tsx tools/gen-abaque.ts > data/abaque-filtration.md
./setup.sh && docker compose restart hermes

docker compose logs -f hermes          # logs d'un service
docker compose down                    # arrêt
```

**Ne jamais démarrer par `docker compose up -d` seul** — il saute le garde-fou
clés et démarrerait avec `MARIA_API_KEY=change-me-in-prod` ou une
`MISTRAL_API_KEY` placeholder. Toujours `./setup.sh`.

Retour au mode 100 % local (futur Mac mini) :
`COMPOSE_PROFILES=local docker
compose up -d`, `ollama pull <modèle>`, puis
repointer `~/.hermes/config.yaml` (provider `ollama`,
`base_url http://ollama:11434/v1`, `api_key ollama-local`).

Vérif d'étanchéité réseau (doit **échouer**, sinon fuite). `nslookup` n'est pas
dans l'image `hermes` — tester la socket sortante directement :

```bash
docker compose exec hermes python3 -c \
  "import socket; socket.create_connection(('1.1.1.1',443),timeout=5)"
# attendu : échec (OSError) = aucune route sortante = scellé
```

## Architecture (le non-évident)

Flux d'une requête employé :

```
employé :3000 → open-webui (embed + retrieve top-k RAG, injecte le contexte)
             → hermes:8642/v1 (gateway, persona + skills)
             → api.mistral.ai/v1 (inférence, via egress-proxy allowlisté)
```

La clé Mistral n'est **pas** dans `~/.hermes/config.yaml` : Hermes la dérive de
l'env `MISTRAL_API_KEY` (host-derived depuis `base_url`), injectée par compose
depuis `.env`. Les appels sortants d'Hermes respectent `HTTPS_PROXY`/`NO_PROXY`
→ tout passe par l'egress-proxy.

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
   est volontairement **vide** (`api_server: []`, voir
   `hermes/config.yaml.example`, `platform_toolsets.api_server`) : zéro tool,
   zéro surface — les règles métier vivent dans SOUL.md. Aucun tool
   `web`/`file`/`terminal` : une injection n'a rien à détourner. **Ne jamais
   élargir ce toolset.** (Maximum toléré : `[skills, todo, memory]`, et
   seulement si `~/.hermes/skills` ne contient que les skills du projet — un
   `~/.hermes` partagé avec un usage perso exposerait tous ses skills au
   modèle.)

3. **`data/` est monté `:ro` mais n'est pas la base interrogée.** Les fichiers
   sont uploadés _manuellement_ via l'UI dans la collection « Knowledge » (store
   vectoriel dans le volume `open-webui`, en lecture-écriture). Modifier `data/`
   exige un ré-upload dans l'UI pour changer les réponses.

4. **`eval.sh` court-circuite le RAG** : il tape `hermes:8642` en direct depuis
   le conteneur `open-webui`, sans contexte injecté. Il teste donc le
   comportement anti-invention du modèle _seul_ (doit produire `[À COMPLÉTER]`,
   ne pas inventer prix/délai), pas la qualité du RAG.

5. **Le dimensionnement est pré-calculé, jamais calculé par le modèle.**
   `data/abaque-filtration.md` est généré par `tools/gen-abaque.ts` depuis le
   moteur hydraulique de `../Peep` (logique provisoire, à faire valider par
   Maria — formule puissance pompe connue fausse, sélection par débit catalogue
   à la place). Le modèle recopie une tranche, totaux compris. **L'abaque
   voyage dans le SOUL, pas dans le RAG** : `setup.sh` concatène
   `hermes/SOUL.md` + `data/abaque-filtration.md` vers `~/.hermes/SOUL.md` —
   choisir une tranche est un test d'intervalle numérique que le retrieval par
   embedding (all-MiniLM, anglais) rate systématiquement. Corriger la logique =
   éditer Peep/`PARAMS`, régénérer, relancer `./setup.sh` + `docker compose
   restart hermes`.

6. **Les SKILL.md ne sont pas injectés au modèle** avec le toolset `[]` :
   Hermes n'injecte qu'un index nom+description, le contenu se charge via le
   tool `skill_view` (désactivé ici). Toute règle métier opérationnelle doit
   vivre dans SOUL.md ; `hermes/skills/` reste documentation/source. De plus,
   l'image resynchronise ~70 skills bundled dans `~/.hermes/skills/` à chaque
   boot — ne pas s'étonner de leur présence.

7. **Réglages RAG persistés dans la DB Open WebUI** (volume `open-webui`,
   priment sur les env — les recréer si le volume saute) : template RAG neutre
   devis+mails, query generation avec calcul de volume (transforme « 8 × 4 m
   prof 1,5 » en « bassin de 48 m³ » avant retrieval), `chunk_size` 1500,
   hybrid search BM25 + reranker `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
   (multilingue, seul du cache HF à ~470 Mo — formats onnx/openvino/.bin
   purgés), `top_k_reranker` 5. Posés via l'API/DB le 2026-07-22 ; l'UI Admin >
   Settings > Documents les affiche. La collection ne contient **pas**
   l'abaque (SOUL seul, cf. point 5) : ses chunks saturés de réfs évincent
   catalogue.md du top-k reranké.

## Invariants de sécurité — ne pas casser

Ces propriétés sont le cœur de la démo. Toute modif du `docker-compose.yml`, du
`proxy/` ou de `config.yaml.example` doit les préserver :

- **Un seul port produit publié** : `open-webui:3000`, derrière `WEBUI_AUTH`.
  `hermes` et `ollama` ne sont **jamais** exposés à l'hôte/LAN. (Exception démo
  assumée : `mailpit` publie `8025`/`1025` en **loopback seul** — outil de démo
  hors produit ; aucune route internet directe, et comme tout service de
  `net_internal` il ne pourrait sortir que via l'egress-proxy allowlisté ; Maria
  ne s'y connecte pas, toolset figé.)
- **`net_internal` est `internal: true`** (aucune route internet directe).
  `egress-proxy` est le **seul** service sur `net_egress`, donc le seul chemin
  vers internet. Tout passe par lui via `HTTP_PROXY`.
- **`proxy/filter` est une allowlist** (`FilterDefaultDeny Yes`) :
  `api.mistral.ai` (inférence), registre Ollama, huggingface (embedding model),
  DuckDuckGo (web search), domaine(s) fournisseur. Ajouter un domaine = élargir
  la surface de fuite — le justifier. Regex **ancrées** (`^…$`) obligatoires.
- **Toolset `api_server` figé** à `[]` (cf. point 2).

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
