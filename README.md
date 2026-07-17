# Agent commercial local ETS Maria — démo POC

Agent de rédaction de mails commerciaux (réponse client, relance devis, mail
libre), **100 % local** : modèle servi par Ollama sur la machine, orchestré
par Hermes Agent, exposé via Open WebUI. Aucune inférence externe.

## Stack

| Conteneur     | Rôle                                              | Port |
|----------------|---------------------------------------------------|------|
| `hermes`      | Orchestrateur d'agents (API OpenAI-compatible)   | 8642 |
| `ollama`      | Sert le modèle local                             | 11434|
| `open-webui`  | Interface web pour les employés (compte unique)| 3000 |

Le métier (persona + règles anti-invention) vit dans `~/.hermes` :
`SOUL.md` + `skills/mails-commerciaux`. Aucun code proxy custom.

## Démarrage (1 commande)

```bash
# 1. Build de l'image Hermes (depuis l'install git locale, voir plus bas)
docker build -t hermes-agent:local ~/.local/opt/hermes-agent

# 2. Démarrer la stack
docker compose up -d

# 3. Récupérer le modèle (une fois ; ~2-4 Go)
docker compose exec ollama ollama pull qwen3:4b-instruct-2507-q4_K_M
```

Ouvrir **http://localhost:3000** → créer le compte de service → dans les
paramètres, le modèle `maria-agent` (Hermes) est déjà listé.

> GPU : le `docker-compose.yml` réserve un device nvidia. Sur CPU (POC),
> retirer le bloc `deploy.resources` — le modèle 4B tournera en CPU.

## Déploiement sur le Mac mini client

Même `docker-compose.yml` ; ajouter `platform: linux/arm64` et utiliser un
modèle plus gros (`qwen3:30b-a3b` ou `mistral-small3.2:24b` selon la RAM).
La clé d'API `MARIA_API_KEY` se passe via `.env` (jamais committée).

## Sécurité / garde-fous

- Toolset Hermes `api_server` = `[skills, todo, memory]` — aucun accès
  fichier/web/terminal pour les employés via l'UI.
- Les brouillons sont du **texte brut**, jamais d'envoi automatique
  (relecture humaine obligatoire, voir `SOUL.md`).
- Aucune donnée ne sort du réseau de l'entreprise.

## Personnalisation

- `SOUL.md` : persona et règles (ton, anti-invention).
- `~/.hermes/skills/mails-commerciaux/SKILL.md` : les trois tâches.
- `docker-compose.yml` : modèle, ports, GPU.
