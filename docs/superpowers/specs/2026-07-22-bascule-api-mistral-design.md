# Bascule inférence : Ollama local (qwen3:4b) → API Mistral (free tier)

Date : 2026-07-22 (post-démo). Statut : appliqué.

## Problème

Le qwen3:4b local est trop petit : résultats incohérents, recopie les exemples
chiffrés. Le matériel cible (Mac mini) n'est pas encore acheté — et le M4 32 Go
n'est plus au catalogue Apple : reste M4 24 Go ou M4 Pro 48 Go.

## Décision

Inférence via **API Mistral free tier**, modèle `mistral-small-latest` (Mistral
Small 3.2, 24B dense, Apache 2.0) :

- Même modèle open-weights qu'un **M4 Pro 48 Go** fera tourner via Ollama — la
  phase API valide la qualité avant l'achat ; bascule finale = changer l'URL,
  mêmes poids, même persona.
- Tester la cible **24 Go** : `default: "open-mistral-nemo"` (12B), même clé, 1
  ligne dans `~/.hermes/config.yaml`.
- Fournisseur européen : cohérent avec le discours souveraineté tenu à Maria.
- Écartés : Groq (pas d'équivalent 24B), Google (souveraineté), OpenRouter :free
  (~50 req/j, fiabilité upstream variable).

## Ce qui change

| Fichier                                                | Changement                                                                                                                                                                                              |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `proxy/filter`                                         | + `^api\.mistral\.ai$` (seul domaine d'inférence)                                                                                                                                                       |
| `docker-compose.yml`                                   | hermes : env `MISTRAL_API_KEY` + `HTTP(S)_PROXY`/`NO_PROXY` ; ollama → `profiles: ["local"]` ; `depends_on: [ollama]` retiré                                                                            |
| `hermes/config.yaml.example` + `~/.hermes/config.yaml` | `model:` → provider `custom`, `base_url https://api.mistral.ai/v1`, `context_length 32768`, **pas d'api_key** (dérivée de l'env `MISTRAL_API_KEY`, host-derived) ; bloc `providers.ollama-local` retiré |
| `setup.sh`                                             | fail-fast `MISTRAL_API_KEY` (absente/vide/`change-me`) ; étape pull supprimée                                                                                                                           |
| `.env(.example)`                                       | + `MISTRAL_API_KEY`                                                                                                                                                                                     |

## Invariants préservés

- `net_internal` reste `internal: true` ; hermes n'a toujours **aucune route
  directe** (seal-check inchangé, doit échouer).
- L'inférence sort **uniquement** par l'egress-proxy allowlisté ; un seul
  domaine ajouté, regex ancrée.
- Toolset `api_server: []` inchangé. Un seul port produit publié inchangé.

## Risque assumé (à redire en RDV)

Free tier Mistral : les requêtes peuvent servir à l'entraînement. **Données de
démo uniquement, jamais de vrais mails clients.** Prod = tier payant opt-out ou
retour 100 % local sur le Mac mini (profil compose `local`).

## Reste à faire (utilisateur)

1. Créer la clé free tier : https://console.mistral.ai → API Keys.
2. La coller dans `.env` (`MISTRAL_API_KEY=`).
3. `./setup.sh` (recrée hermes avec les nouvelles env), puis `./eval.sh`.
