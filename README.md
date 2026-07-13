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

## Architecture

L'agent s'appuie sur [Hermes Agent](https://github.com/NousResearch/hermes-agent)
(Nous Research, MIT) : framework agent self-hosted et model-agnostic, configuré
ici sans aucun provider cloud (voir `hermes/config.yaml.example`).

```
Navigateur (poste employé)
        │ http://<machine>:8321
        ▼
FastAPI  agent/app.py ── sert l'UI (static/index.html, zéro ressource externe)
        │                ── /api/clients, /api/clients/{id}/documents : sélection
        │                ── /api/chat : SSE streaming (IDs client/devis, pas de texte)
        │  enrichit chaque demande : instruction de tâche (prompts.py)
        │            + fiche entreprise (data/entreprise.md)
        │            + client & devis sélectionnés (db.py — SQLite data/maria.db,
        │              seedée depuis les CSV mock format Sage par seed_db.py)
        │            + extraits catalogue pertinents (catalog.py, recherche lexicale)
        ▼ 127.0.0.1:8642 (/v1/chat/completions, clé API locale)
Gateway Hermes Agent ── system prompt : ~/.hermes/SOUL.md + skill mails-commerciaux
        │               ── mémoire persistante locale (SQLite)
        ▼
Ollama  127.0.0.1:11434 (OLLAMA_NO_CLOUD=1, contexte 64k)
        └─ qwen3:4b-instruct-2507-q4_K_M  (≈ 2,5 Go, GPU ou CPU)
```

## Démarrage rapide (machine de dev)

```bash
scripts/install_dev.sh                          # venv + dépendances Python
ollama pull qwen3:4b-instruct-2507-q4_K_M       # une seule fois
# Hermes Agent (une seule fois) : installeur officiel puis config du dépôt —
#   curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
#   cp hermes/config.yaml.example ~/.hermes/config.yaml   (+ clé : openssl rand -hex 24)
#   cp hermes/SOUL.md ~/.hermes/ && cp -r hermes/skills/mails-commerciaux ~/.hermes/skills/
scripts/run.sh                                  # démarre Ollama + gateway Hermes + l'agent
# → http://127.0.0.1:8321
```

## Structure

| Chemin | Rôle |
|---|---|
| `agent/app.py` | Serveur FastAPI : UI + API sélection + relais streaming vers le gateway Hermes |
| `agent/prompts.py` | Définition des 3 tâches + enrichissement par requête (blocs `<client>`/`<devis>`) |
| `agent/catalog.py` | Recherche lexicale dans le catalogue (sans embeddings) |
| `agent/db.py` | Base locale clients/devis (SQLite stdlib, lecture seule côté app) |
| `agent/seed_db.py` | Import des CSV mock → `data/maria.db` (`--force` pour régénérer) |
| `agent/tests/` | Tests pytest (DB, API, prompts) : `pytest agent/tests -q` |
| `agent/data/entreprise.md` | Fiche entreprise = source de vérité du modèle (**à compléter avec Kévin**) |
| `agent/data/catalogue_mock.csv` | Extrait catalogue mock, format import Sage/Peep (`;`) |
| `agent/data/*_mock.csv` | Clients, devis et lignes mock (format `;` façon export Sage) |
| `agent/data/maria.db` | Base SQLite générée (gitignorée, seed auto au démarrage) |
| `agent/static/index.html` | Interface web locale (aucune dépendance externe) |
| `hermes/` | Config Hermes versionnée : `config.yaml.example`, `SOUL.md`, skill `mails-commerciaux` (à copier dans `~/.hermes/`) |
| `scripts/run.sh` / `scripts/install_dev.sh` | Lancement (Ollama + gateway + proxy) / installation dev |
| `DEPLOY_MARIA.md` | Guide de redéploiement sur la VM Debian chez Maria |
| `ROADMAP.md` | Évolutions prévues (Sage 100, Peep, RAG, Mac mini M4…) |

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

## Garde-fous intégrés

- Le modèle n'a le droit de citer prix/références/délais **que** s'ils viennent de la fiche,
  du catalogue injecté ou du contexte saisi ; sinon il écrit `[À COMPLÉTER : …]`.
  Règles portées par `hermes/SOUL.md` + le skill `mails-commerciaux`, rappelées
  dans chaque requête (`prompts.py`).
- Aucun délai chiffré ni engagement ferme inventé (« sous 24 h »…).
- Bandeau UI : « l'assistant propose, l'humain décide » — la relecture avant envoi fait partie du process.
- `OLLAMA_NO_CLOUD=1` ; Hermes configuré sans provider cloud, gateway et Ollama en 127.0.0.1 ;
  côté UI, toolset Hermes réduit à `[skills, todo, memory]` (pas de terminal ni d'accès fichiers —
  un mail client collé peut contenir une injection de prompt).

## Limites connues (assumées pour la démo)

- Modèle 4B : français parfois maladroit sur les tournures longues → relecture humaine obligatoire.
- Catalogue et base clients/devis **mock** : aucune connexion à Sage dans cette version.
  Le seed (`seed_db.py`) est déjà un importeur CSV format Sage : le chantier « export
  Sage » (ROADMAP §2) consistera à remplacer les CSV mock par les exports réels.
- Pas de connexion à la boîte mail : l'employé copie le message reçu et recopie le brouillon.
- Une conversation à la fois (pas de comptes utilisateurs).
