# Makefile — wrapper des commandes documentées (voir CLAUDE.md).
# ponytail: aucune logique ici, juste des raccourcis vers setup.sh/eval.sh/compose.
.DEFAULT_GOAL := help
SVC ?= hermes

help: ## Liste les cibles
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sort | awk -F':.*##' '{printf "  \033[36m%-12s\033[0m%s\n", $$1, $$2}'

build: ## Build l'image hermes-agent:local (préalable)
	docker build -t hermes-agent:local ~/.local/opt/hermes-agent

deploy: ## Démarrer la stack (SEUL point d'entrée : fail-fast clé + up + pull)
	./setup.sh

eval: ## Éval anti-invention (court-circuite le RAG)
	./eval.sh

logs: ## Suivre les logs d'un service (SVC=hermes par défaut)
	docker compose logs -f $(SVC)

ps: ## État des conteneurs
	docker compose ps

info: ## Rappels : URL et accès (seul port publié)
	@echo "Web UI   : http://localhost:3000  (Open WebUI, WEBUI_AUTH)"
	@echo "hermes   : interne seul (net_internal, non exposé) → API Mistral via egress"
	@echo "ollama   : profil 'local' (arrêté par défaut, retour 100 % local)"

down: ## Arrêter la stack
	docker compose down

seal-check: ## Vérif étanchéité réseau (la socket sortante doit échouer)
	@docker compose exec -T $(SVC) python3 -c "import socket; socket.create_connection(('1.1.1.1',443),timeout=5)" >/dev/null 2>&1 \
	  && { echo "FUITE : connexion sortante réussie (ne devrait PAS)"; exit 1; } \
	  || echo "OK : étanchéité confirmée (socket sortante refusée)"

.PHONY: help build deploy eval logs ps down seal-check info
