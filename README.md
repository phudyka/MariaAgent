# Agent commercial local — ETS Maria

Prototype d'agent IA **100 % local et hermétique** pour les Établissements Maria :
un assistant de rédaction de mails commerciaux (réponse client, relance de devis, mail libre),
appuyé sur une fiche entreprise, un extrait de catalogue au format Sage/Peep et une
base locale clients/devis. Aucune donnée ne quitte la machine : l'inférence tourne
sur un LLM local via Ollama.

**Le flux est à sélection, pas à rédaction** : l'employé choisit le client puis le
devis concerné (recherche, filtre par période) ; les références, dates et montants
sont assemblés côté serveur depuis la base — jamais retapés à la main. Le texte
libre ne subsiste que pour coller le message reçu (réponse client) et pour la
tâche « mail libre » (cas hors base : prospect, fournisseur…).

> Démo volontairement limitée à **une seule tâche propre** (les mails) pour valider
> l'approche avant d'élargir — voir [ROADMAP.md](ROADMAP.md).
> Déploiement chez Maria : voir [DEPLOY_MARIA.md](DEPLOY_MARIA.md).
>
> Conception de l'UX de sélection : voir
> [docs/superpowers/specs/2026-07-13-selection-ux-design.md](docs/superpowers/specs/2026-07-13-selection-ux-design.md).

## Architecture

L'agent s'appuie sur [Hermes Agent](https://github.com/NousResearch/hermes-agent)
(Nous Research, MIT) : framework agent self-hosted et model-agnostic, configuré
ici sans aucun provider cloud (voir `hermes/config.yaml.example`).

```
Poste employé
   ├─ Sélecteur guidé (http://<machine>:8321, étapes Tâche → Client → Devis)
   │     └─ bouton « Ouvrir dans Open WebUI » ──► POST /api/handoff
   │           → assemble le récap (db.py/catalog.py/prompts.py), renvoie texte
   │             prêt-à-coller + lien Open WebUI (ou conversation pré-remplie si JWT)
   └─ Open WebUI :3000 (peau chat façon ChatGPT/Claude : bulles, historique,
        thème clair/sombre, sélecteur de modèles = invocation des sous-agents)
             │ OPENAI_API_BASE_URL = http://127.0.0.1:8321/v1 (proxy ci-dessous)
             ▼
FastAPI  agent/app.py ── sert le sélecteur guidé (static/index.html allégé)
        │                ── /api/clients, /api/clients/{id}/documents : sélection
        │                ── /api/handoff : point d'entrée du sélecteur (IDs client/devis)
        │                ── /v1/models, /v1/chat/completions : endpoint OpenAI-compatible
        │                   pour Open WebUI (presets maria-general / maria-libre en direct)
        │  enrichit chaque demande : instruction de tâche (prompts.py)
        │            + fiche entreprise (data/entreprise.md)
        │            + client & devis sélectionnés (db.py — SQLite data/maria.db,
        │              seedée depuis les CSV mock format Sage par seed_db.py)
        │            + extraits catalogue pertinents (catalog.py, recherche lexicale)
        ▼ 127.0.0.1:8642 (/v1/chat/completions, clé API locale)
Gateway Hermes Agent ── system prompt : ~/.hermes/SOUL.md + skill mails-commerciaux
        │               ── mémoire persistante locale (SQLite)
        │               ── toolset api_server = [skills, todo, memory] (jamais étendu)
        ▼
Ollama  127.0.0.1:11434 (OLLAMA_NO_CLOUD=1, contexte 64k)
        └─ qwen3:4b-instruct-2507-q4_K_M  (≈ 2,5 Go, GPU ou CPU)
```

> L'UX de sélection guidée (client/devis par ID) **reste le seul point d'entrée** pour
> `reponse_client` et `relance_devis` : c'est elle qui préserve l'anti-hallucination.
> Open WebUI sert à la génération et à l'itération sur le brouillon (façon ChatGPT),
> pas au choix du dossier client — exactement comme on ne fait pas deviner un fichier
> précis par la conversation. Les presets « Réponse client » / « Relance devis » sont
> donc déclenchés via le sélecteur (`/api/handoff`), jamais saisis en texte libre.
> Voir `docs/plan-chat-multiagents.md` et `docs/openwebui-presets.md`.

### Chaîne d'enrichissement d'une requête

1. L'employé sélectionne une **tâche** (`reponse_client`, `relance_devis`, `mail_libre`).
2. L'UI n'envoie au serveur que des **IDs** (`client_id`, `document_id`) et, le cas échéant,
   le texte collé (mail reçu) ou la consigne libre. Aucune donnée métier en clair.
3. `app.py` valide la sélection par tâche et charge client/devis depuis `maria.db`.
4. `prompts.build_messages` assemble un message unique (rôle `user`) contenant :
   - l'instruction de tâche (depuis `prompts.TASKS`),
   - la fiche entreprise (`data/entreprise.md`),
   - le bloc `<client>` et éventuellement le bloc `<devis>` (lignes incluses),
   - les extraits catalogue (recherche lexicale sur le message, ou `by_refs` sur les
     lignes du devis sélectionné),
   - la demande de l'employé.
   Le system prompt appartient à Hermes (SOUL + skill + mémoire) ; l'enrichissement est
   préfixé au premier message pour rester dans le périmètre validé (pas de tool-calling).
5. Le message est relayé en streaming SSE vers le gateway Hermes (`/v1/chat/completions`),
   qui pilote Ollama. L'UI affiche le brouillon au fil de l'eau, avec les références
   catalogue utilisées (chips) et un bouton « Affiner » pour itérer.

## Démarrage rapide (machine de dev)

```bash
scripts/install_dev.sh                          # venv + dépendances Python (+ seed DB)
ollama pull qwen3:4b-instruct-2507-q4_K_M       # une seule fois
# Hermes Agent (une seule fois) : installeur officiel puis config du dépôt —
#   curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
#   cp hermes/config.yaml.example ~/.hermes/config.yaml   (+ clé : openssl rand -hex 24)
#   cp hermes/SOUL.md ~/.hermes/ && cp -r hermes/skills/mails-commerciaux ~/.hermes/skills/
scripts/run.sh                                  # démarre Ollama + gateway Hermes + l'agent
# → http://127.0.0.1:8321
```

`scripts/run.sh` démarre automatiquement Ollama (si absent), le gateway Hermes (si absent),
Open WebUI (si Docker disponible), puis le proxy uvicorn. Variables d'environnement utiles :
`OLLAMA_CONTEXT_LENGTH=65536`, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q4_0`
(voir section Configuration).

### Frontend de chat (Open WebUI)

Open WebUI (`http://127.0.0.1:3000`) fournit l'UX façon ChatGPT/Claude (bulles, streaming,
historique, thème, sélecteur de modèles). Il est branché en OpenAI-compatible sur le proxy
local (`http://127.0.0.1:8321/v1`) — aucun service externe, télémétrie coupée. Les sous-agents
sont des **presets Modèles** (Workspace > Models) : `Maria — Général`, `Maria — Mail libre`,
`Maria — Réponse client`, `Maria — Relance devis`. Création : voir `docs/openwebui-presets.md`.

Le sélecteur guidé (`http://127.0.0.1:8321`) reste l'entrée pour réponse/relance : il
assemble le contexte et le transmet à Open WebUI (coller une fois, ou conversation
pré-remplie si `MARIA_OPENWEBUI_JWT` est défini).

Pour la mise en production (VM Debian, services systemd, pare-feu), suivre
[DEPLOY_MARIA.md](DEPLOY_MARIA.md).

## Les trois tâches

| Tâche | Sélection requise | Texte requis | Comportement |
|---|---|---|---|
| `reponse_client` — Répondre à un client | client obligatoire, devis **optionnel** | message = mail reçu collé | réponse point par point, références depuis le catalogue |
| `relance_devis` — Relancer un devis | client + devis **obligatoires** | aucun (sélection pure) | relance courtoise, rappel numéro/objet/montant exacts |
| `mail_libre` — Mail libre | aucune | message = consigne libre | fournisseur, prospect, interne… hors base |

Chaque tâche est décrite dans `prompts.TASKS` (libellé, placeholder, instruction) et
dans le skill `hermes/skills/mails-commerciaux/SKILL.md`. Les règles anti-invention sont
portées par `hermes/SOUL.md` et rappelées dans chaque requête (`prompts.py`).

## Structure

| Chemin | Rôle |
|---|---|
| `agent/app.py` | Serveur FastAPI : UI + API sélection + relais streaming vers le gateway Hermes |
| `agent/prompts.py` | Définition des 3 tâches + enrichissement par requête (blocs `<client>`/`<devis>`) |
| `agent/catalog.py` | Recherche lexicale dans le catalogue (sans embeddings) |
| `agent/db.py` | Base locale clients/devis (SQLite stdlib, lecture seule côté app) |
| `agent/seed_db.py` | Import des CSV mock → `data/maria.db` (`--force` pour régénérer) |
| `agent/requirements.txt` | Dépendances Python (fastapi, uvicorn, httpx, + pytest en dev) |
| `agent/tests/` | Tests pytest (API, DB, prompts) : `pytest agent/tests -q` |
| `agent/data/entreprise.md` | Fiche entreprise = source de vérité du modèle (**à compléter avec Kévin**) |
| `agent/data/catalogue_mock.csv` | Extrait catalogue mock, format import Sage/Peep (`;`), 31 produits |
| `agent/data/clients_mock.csv` | 13 clients mock (format `;` façon export Sage) |
| `agent/data/documents_mock.csv` | 22 devis mock (12 mois) |
| `agent/data/document_lignes_mock.csv` | 62 lignes de devis, refs réelles du catalogue |
| `agent/data/maria.db` | Base SQLite générée (gitignorée, seed auto au démarrage) |
| `agent/static/index.html` | Interface web locale (aucune dépendance externe) |
| `agent/static/fonts/` | Polices auto-hébergées (DM Sans, JetBrains Mono) — zéro CDN |
| `hermes/` | Config Hermes versionnée : `config.yaml.example`, `SOUL.md`, skill `mails-commerciaux` (à copier dans `~/.hermes/`) |
| `scripts/run.sh` / `scripts/install_dev.sh` | Lancement (Ollama + gateway + proxy) / installation dev |
| `DEPLOY_MARIA.md` | Guide de redéploiement sur la VM Debian chez Maria |
| `ROADMAP.md` | Évolutions prévues (Sage 100, Peep, RAG, Mac mini M4…) |
| `docs/superpowers/` | Spec & plan de conception de l'UX de sélection |

### Schéma de la base locale

`db.py` crée trois tables SQLite (lecture seule côté application, écriture via `seed_db.py`) :

- **`clients`** : `id`, `code` (CT_Num Sage), `nom`, `contact`, `email`, `telephone`, `ville`, `type` ∈ {particulier, professionnel, collectivite}.
- **`documents`** : `id`, `numero` (DO_Piece Sage), `client_id`, `type` (défaut `devis`), `objet`, `date_emission`, `date_validite`, `statut` ∈ {DRAFT, SENT, ACCEPTED, REJECTED, EXPIRED}, `montant_ht` (somme figée des lignes), `notes`.
- **`document_lignes`** : `id`, `document_id`, `sage_ref` (→ catalogue), `designation` (snapshot), `quantite`, `prix_unitaire_ht` (snapshot).

Le catalogue (`catalogue_mock.csv`) reste la source de vérité produits : les lignes de
devis y référencent `sage_ref` et figent désignation + prix au moment du devis (comme Sage).

### Format des CSV mock

Séparateur `;` (format import Sage/Peep). En-têtes :

| Fichier | Colonnes |
|---|---|
| `clients_mock.csv` | `code;nom;contact;email;telephone;ville;type` |
| `documents_mock.csv` | `numero;client_code;type;objet;date_emission;date_validite;statut;notes` |
| `document_lignes_mock.csv` | `numero;sage_ref;quantite` (les colonnes optionnelles `designation`/`prix_unitaire_ht`, si présentes, priment — prévu pour les exports Sage réels) |
| `catalogue_mock.csv` | `sageRef;name;brand;category;sellPrice;stock;specs` |

## API

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/` | Sélecteur guidé allégé (`static/index.html`) — entrée pour réponse/relance |
| `GET` | `/static/{path}` | Ressources statiques (polices, etc.) |
| `GET` | `/api/config` | Modèle, libellés/placeholders des tâches, taille catalogue |
| `GET` | `/api/health` | Santé : `hermes` (gateway), `ollama`, `model`, `model_ready`, `ready` |
| `GET` | `/api/clients?q=` | Recherche clients (code/nom/ville/contact, insensible accents), bornée ~50, avec `nb_documents` |
| `GET` | `/api/clients/{id}/documents?periode=` | Devis du client (lignes imbriquées), tri date décroissante ; `periode` ∈ {`3m`, `6m`, `12m`, ``} |
| `POST` | `/api/chat` | Génération (SSE). Corps : `task`, `message?`, `client_id?`, `document_id?`, `history[]` |
| `POST` | `/api/handoff` | Handoff du sélecteur → Open WebUI. Mêmes validations 422 que `/api/chat`. Renvoie `recap` (texte prêt-à-coller) + lien, ou `chat_url` si JWT configuré |
| `GET` | `/v1/models` | Liste des presets exposés à Open WebUI (`maria-general`, `maria-libre`, `maria-reponse`, `maria-relance`) |
| `POST` | `/v1/chat/completions` | OpenAI-compatible (Open WebUI). Servi en direct pour `maria-general`/`maria-libre` uniquement ; `maria-reponse`/`maria-relance` renvoient 400 (passer par `/api/handoff`) |

### Contrat `POST /api/chat`

- `task` ∈ {`reponse_client`, `relance_devis`, `mail_libre`}.
- `reponse_client` : `client_id` requis, `document_id` optionnel, `message` (mail reçu) requis.
- `relance_devis` : `client_id` **et** `document_id` requis, pas de `message`.
- `mail_libre` : `message` requis, aucun ID.
- `document_id` doit appartenir au `client_id` (sinon `422`).
- Réponse = flux SSE `text/event-stream` : événements `meta` (références catalogue),
  `delta` (texte), `done` (stats), `error`.

Exemples de validation (tests `agent/tests/test_api.py`) :

```bash
# Liste des clients
curl -s http://127.0.0.1:8321/api/clients | head
# Devis d'un client avec filtre période
curl -s "http://127.0.0.1:8321/api/clients/1/documents?periode=6m"
# Mail libre (SSE)
curl -s -N -X POST http://127.0.0.1:8321/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"task":"mail_libre","message":"Mail au fournisseur Zodiac pour prix pompe SP050"}'
```

## Configuration (variables d'environnement)

| Variable | Défaut | Rôle |
|---|---|---|
| `MARIA_MODEL` | `qwen3:4b-instruct-2507-q4_K_M` | Modèle Ollama (contrôle santé) |
| `MARIA_HOST` | `127.0.0.1` | `0.0.0.0` pour exposer sur le LAN |
| `MARIA_PORT` | `8321` | Port de l'UI |
| `MARIA_HERMES_URL` | `http://127.0.0.1:8642` | Adresse du gateway Hermes |
| `MARIA_HERMES_KEY` | *(lue dans `~/.hermes/config.yaml`)* | Clé API du gateway |
| `MARIA_HERMES_MODEL` | `maria-agent` | Nom de modèle exposé par le gateway |
| `MARIA_OLLAMA_URL` | `http://127.0.0.1:11434` | Adresse d'Ollama (contrôle santé) |

Le modèle réel, le contexte (64k minimum) et la température sont configurés
côté Hermes : `~/.hermes/config.yaml` (modèle depuis `hermes/config.yaml.example`).
`run.sh` exporte aussi les variables Ollama : `OLLAMA_NO_CLOUD=1`,
`OLLAMA_CONTEXT_LENGTH=65536`, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q4_0`.

## Interface (UI)

Page unique `agent/static/index.html`, design system interne (palette « eau »),
polices auto-hébergées (aucun CDN). Cascade de sélection progressive à gauche,
panneau brouillon à droite :

1. **Tâche** : trois cartes (Répondre / Relancer / Mail libre).
2. **Client** : barre de recherche (debounce 200 ms), liste de sélection.
3. **Devis** : segmented de période (3m/6m/12m/tous), liste avec statut coloré
   (chips Peep + `EXPIRED` neutre), lignes dépliées à la sélection. Option
   « Aucun devis concerné » pour la réponse client.
4. **Message** : textarea (coller le mail reçu, ou consigne libre) — masqué pour `relance_devis`.
5. **Récap** : carte « Contexte transmis à l'agent » (client, devis, références exactes,
   montant) — l'employé vérifie d'un coup d'œil avant de générer.

Panneau droit : streaming SSE avec curseur, chips des références catalogue utilisées,
mise en surbrillance des `[À COMPLÉTER]` (en attente de saisie), boutons **Copier** /
**Nouveau**, **Affiner** (itération sur le même contexte), pastille de santé
(agent prêt / moteur IA arrêté / gateway arrêté / modèle non installé).
Raccourci : `Ctrl`+`Entrée` pour générer.

> Note : `index.html` référence `DESIGN_SYSTEM.md` ( guide de style non inclus dans le
> dépôt) — le design system complet vit dans le fichier de specs
> `docs/superpowers/specs/2026-07-13-selection-ux-design.md`.

## Garde-fous intégrés

- Le modèle n'a le droit de citer prix/références/délais **que** s'ils viennent de la fiche,
  du catalogue injecté ou du contexte saisi ; sinon il écrit `[À COMPLÉTER : …]`.
  Règles portées par `hermes/SOUL.md` + le skill `mails-commerciaux`, rappelées
  dans chaque requête (`prompts.py`).
- Aucun délai chiffré ni engagement ferme inventé (« sous 24 h »…).
- Brouillons en **texte brut** : aucune mise en forme Markdown (pas de gras, titres, tableaux).
- Bandeau UI : « l'assistant propose, l'humain décide » — la relecture avant envoi fait partie du process.
- `OLLAMA_NO_CLOUD=1` ; Hermes configuré sans provider cloud, gateway et Ollama en 127.0.0.1 ;
  côté UI, toolset Hermes réduit à `[skills, todo, memory]` (pas de terminal ni d'accès fichiers —
  un mail client collé peut contenir une injection de prompt).

## Tests

```bash
pytest agent/tests -q
```

Couverture (tests `TestClient` + DB seedée isolée dans `tmp_path`) :

- `test_db.py` : seed complet, recherche insensible aux accents, documents triés par date,
  montant = somme des lignes, filtre période, référence inconnue refusée (ValueError).
- `test_api.py` : liste/recherche clients, documents avec lignes, filtre période,
  validation `/api/chat` par tâche (422 sans client/devis/message, 422 si devis d'un autre client).
- `test_prompts.py` : contexte devis dans le 1er message, mail libre sans blocs structurés,
  ré-affichage du contexte à l'affinage, `by_refs` conserve l'ordre.

## Données mock vs production

Tout est **mock** et seedé depuis les CSV. Le remplacement par les données réelles
ne change **aucun code** : il suffit de remplacer les `*_mock.csv` (même format `;`)
et de relancer `python agent/seed_db.py --force`. Le catalogue suit le même principe.
Détail et chantiers Sage/Peep : [ROADMAP.md](ROADMAP.md) §1–§3.

## Limites connues (assumées pour la démo)

- Modèle 4B : français parfois maladroit sur les tournures longues → relecture humaine obligatoire.
- Catalogue et base clients/devis **mock** : aucune connexion à Sage dans cette version.
  Le seed (`seed_db.py`) est déjà un importeur CSV format Sage : le chantier « export
  Sage » (ROADMAP §2) consistera à remplacer les CSV mock par les exports réels.
- Pas de connexion à la boîte mail : l'employé copie le message reçu et recopie le brouillon.
- Une conversation à la fois (pas de comptes utilisateurs).
- `DESIGN_SYSTEM.md` référencé par l'UI n'est pas présent dans le dépôt (spec de design dans
  `docs/superpowers/` à la place).

## Déploiement & roadmap

- **Production (VM Debian 12, Hyper-V, CPU-only)** : [DEPLOY_MARIA.md](DEPLOY_MARIA.md)
  — services systemd (`ollama` → `hermes-gateway` → `maria-agent`), pare-feu ufw,
  recette, variante 100 % hors-ligne, dépannage.
- **Évolutions** : [ROADMAP.md](ROADMAP.md) — consolidation (fiche/ catalogue/ données réels),
  intégration Sage 100 (export puis passerelle), Peep (API REST), boîte mail IMAP/SMTP,
  RAG documentaire, nouvelles tâches, gouvernance/comptes, matériel (Mac mini M4).
