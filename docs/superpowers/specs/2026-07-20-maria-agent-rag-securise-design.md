# Agent commercial local ETS Maria — démo RAG sécurisée

**Date :** 2026-07-20 **Statut :** design validé (sections 1-7), en attente de
relecture spec avant plan d'implémentation.

## Contexte et objectif

ETS Maria (pisciniste, région niçoise, depuis 1937) veut à terme un agent IA
hébergé **en local**, tournant à temps plein, avec accès **en lecture** à ses
données centralisées : catalogue Sage 100, base clients, mails, contrats, et le
maximum d'historique de l'entreprise. Rôle : aider aux tâches quotidiennes
(rédaction de mails commerciaux d'abord).

Cette spec couvre la **version démo (POC)** : un petit modèle tournant en local
sur la config de développement (GPU GTX 1080, 8 Go VRAM), qui **mocke** cet
usage tout en **écrivant en direct** pendant la démo. L'interface est **Open
WebUI uniquement** (aucune interface custom). Le setup doit être le plus léger
possible et la sécurité irréprochable : l'ajout de l'agent ne doit **jamais**
devenir la faille qui, interceptée, leake toutes les données de l'entreprise.

Décisions validées en brainstorming :

- **Accès aux données : RAG local** (recherche sémantique sur données mockées),
  le plus fiable sur un modèle 4B et extensible à tout l'historique.
- **Hermes conservé** (le gateway orchestrateur) : investissement réutilisé pour
  la version prod, plus efficace à terme. Ses failles actuelles sont corrigées.
- **Démo simple**, durcissement prod documenté à part (pas construit
  maintenant).
- **Web contrôlé activé** dès la démo.

Principe directeur (inspiré des meilleurs agents) : **on ne fait pas confiance
au modèle, on contrôle ses capacités au niveau de l'infrastructure.** Un mail
client collé peut contenir une injection de prompt ; même un modèle entièrement
compromis ne doit avoir **aucun chemin** pour exfiltrer des données.

## Section 1 — Architecture & isolation réseau

```
                :3000 (LAN employés, WEBUI_AUTH)
                      │  ingress : seul port publié
                ┌─────▼──────┐
                │ open-webui │  RAG natif (données Maria) + web search
                └──┬──────┬──┘
    net_internal   │      │   (open-webui n'a PAS d'accès internet direct)
  (internal:true)  │      │
     ┌─────────────┴┐   ┌─┴──────────────┐
     │              │   │                │
┌────▼───┐   ┌──────▼┐  │          ┌─────▼───────┐
│ ollama │   │hermes │  └─────────►│ egress-proxy │──► internet
│ (GPU)  │◄──│gateway│   HTTP_PROXY │  (allowlist) │    (domaines
└────────┘   └───────┘              └──────────────┘     autorisés SEULS)
 no egress    no egress
```

**Composants :**

| Conteneur      | Rôle                                       | Réseau                        | Port publié |
| -------------- | ------------------------------------------ | ----------------------------- | ----------- |
| `ollama`       | Sert le modèle local (GPU)                 | `net_internal`                | aucun       |
| `hermes`       | Gateway orchestrateur (OpenAI-compatible)  | `net_internal`                | aucun       |
| `open-webui`   | UI + RAG natif + web search                | `net_internal`                | `3000`      |
| `egress-proxy` | Unique sortie internet, allowlist domaines | `net_internal` + `net_egress` | aucun       |

**Réseaux :**

- `net_internal` : `internal: true` → **aucune route directe vers internet**.
  Héberge `ollama`, `hermes`, `open-webui`, et l'interface interne
  d'`egress-proxy`.
- `net_egress` : bridge avec accès internet. **Seul** `egress-proxy` y est
  connecté.

**Invariants de sécurité (démontrables en RDV client) :**

1. **Aucun conteneur n'a d'egress direct.** L'unique chemin vers internet est
   `egress-proxy`, et il n'autorise que les domaines de l'allowlist (tinyproxy,
   ~10 lignes de conf). C'est du câblage, pas de la confiance.
2. `ollama` et `hermes` ne sont que sur `net_internal`. Leur seul usage
   d'internet est **via** `egress-proxy` (`HTTP_PROXY`), strictement allowlisté
   : `ollama` pour **pull le modèle** depuis le registre Ollama (setup),
   `hermes` n'en a **aucun** besoin. Toute destination hors allowlist est
   refusée → exfiltration impossible, même modèle retourné par une injection.
3. **Un seul port publié** : `open-webui:3000`, derrière `WEBUI_AUTH`.
   `hermes:8642` n'est **plus** exposé au LAN — Open WebUI le joint par
   `net_internal`.
4. Données Maria montées en **lecture seule** (`:ro`).
5. Toolset du modèle inchangé : `[skills, todo, memory]`. **Aucun** tool
   `web`/`file`/`terminal` donné au modèle. Le web est fetché par Open WebUI,
   jamais par un tool que l'injection pourrait détourner.

**Allowlist du proxy** (démo) : registre Ollama (`registry.ollama.ai` + CDN),
source de l'embedding model, et le(s) domaine(s) fournisseur pour le web search.
Rien d'autre. `ollama pull` et le pull de l'embedding passent par ce seul canal.

`hermes` bind `0.0.0.0` **à l'intérieur** de son conteneur (nécessaire pour être
joignable par `open-webui` sur `net_internal`) : ce n'est pas une exposition,
car le port n'est **pas** publié sur l'hôte et le conteneur est sur un réseau
sans route internet.

Détail à câbler à l'implémentation : le web-search d'Open WebUI route soit via
`HTTP_PROXY=egress-proxy`, soit via un SearXNG local placé derrière le proxy —
le plus simple qui fonctionne sera retenu. L'invariant (seul le proxy sort,
allowlist) tient quel que soit le choix.

## Section 2 — Données mock & RAG

Régénérer des mocks riches (les anciens ont été supprimés au commit `32f48a1`),
sous forme de **documents pensés pour le RAG**, un par source de données Maria :

| Document        | Contenu                                                                         | Mock de          |
| --------------- | ------------------------------------------------------------------------------- | ---------------- |
| `catalogue.md`  | lignes `- REF \| nom \| marque \| prix € HT \| stock \| specs` (pièces piscine) | Sage 100         |
| `clients/*.md`  | fiche par client : contact, historique, notes                                   | base clients     |
| `devis/*.md`    | n°, objet, montant, lignes, date d'envoi                                        | devis/contrats   |
| `mails/*.md`    | fils d'échanges par client                                                      | historique mails |
| `entreprise.md` | fiche entreprise + bloc signature                                               | ancrage persona  |

- Chargés dans **une collection « Knowledge » Open WebUI**, montés `:ro`.
- Open WebUI embed en local, récupère le top-k, l'injecte dans la requête vers
  Hermes. **C'est le RAG qui remplace la couche d'enrichissement supprimée**
  (`agent/app.py`) — plus aucun copier-coller manuel par l'employé.
- L'embedding model se pull une fois via le proxy allowlist (ou est bundlé).

## Section 3 — Persona & règles anti-invention

Réutiliser l'existant, déjà bon :

- `hermes/SOUL.md` : persona (artisan sérieux, vouvoiement, texte brut) + règles
  absolues anti-invention (`[À COMPLÉTER : ...]` si donnée absente, jamais
  d'engagement ferme inventé, un humain relit et envoie). Posé en system prompt
  du modèle.
- `hermes/skills/mails-commerciaux/SKILL.md` : les trois tâches (réponse client,
  relance devis, mail libre).

Seul changement : le wording « l'interface de l'entreprise enrichit chaque
demande » (SKILL.md L48) devient « le RAG récupère les passages pertinents » —
la **logique anti-invention est identique**, seule la source du contexte change
(RAG au lieu du proxy supprimé).

## Section 4 — Durcissement production (documenté, non construit)

Fichier séparé `docs/superpowers/specs/2026-07-20-securite-prod.md` — threat
model + cible. **Non implémenté dans la démo.**

- **Insider (attaque de l'intérieur)** : comptes RBAC par employé (fin des
  comptes de service partagés), audit log (qui a requêté quoi), données en
  lecture seule.
- **Outsider (attaque de l'extérieur)** : isolation réseau + auth + zéro egress
  (déjà démontré en démo).
- **Modèle compromis** : capability control au niveau infra (déjà démontré en
  démo).
- **Chiffrement at-rest** : volume chiffré (LUKS / gocryptfs) ou réplica en
  lecture seule de Sage 100 ; secrets dans un gestionnaire (Docker secrets /
  Vault), pas dans `.env`.
- **Sage 100** : utilisateur DB en lecture seule + synchronisation planifiée
  vers l'index RAG ; **jamais** de chemin d'écriture.
- **Exploitation** : TLS de bout en bout, DLP sur le proxy egress,
  rétention/rotation des logs, backup/DR, monitoring.

La démo prouve déjà 3 des 5 axes (outsider, modèle compromis, egress contrôlé).
Ce document décrit comment finir.

## Section 5 — Setup (le plus léger, 1 commande)

- `docker-compose.yml` : `ollama` + `hermes` + `open-webui` + `egress-proxy` +
  les 2 réseaux.
- `.env` : `MARIA_API_KEY` ; le setup **échoue** (fail-fast) si la clé vaut
  encore `change-me-in-prod`.
- `setup.sh` : pull du modèle, seed de la collection Knowledge (API Open WebUI),
  pose du system prompt. Idempotent.
- `README.md` mis à jour (RAG, web contrôlé, topologie sécu, mocks).
- **Fixes de l'audit intégrés au passage** (voir Section 8).

## Section 6 — Scénario de démo

1. _« Relance le devis 2024-118 du client Durand. »_ → le RAG sort la fiche
   Durand + le devis 2024-118 + les derniers mails → brouillon en texte brut,
   montant et références **réels cités** depuis les données.
2. _« Le prix de la pompe Z ? »_ (absente des données) → renvoie
   `[À COMPLÉTER]`, **n'invente pas** = preuve anti-invention en direct.
3. _« Vérifie la dispo de la pièce X chez le fournisseur. »_ → web contrôlé,
   seul le domaine fournisseur allowlisté est joignable.
4. Montrer la topologie : le modèle **n'a aucune route réseau** pour fuir les
   données, même retourné par une injection.

## Section 7 — Vérification (mini-éval anti-invention)

`eval.sh` : 3-4 prompts **sans** données pertinentes → assert que
`[À COMPLÉTER]` apparaît et qu'aucun montant `€` ni date inventés ne sortent.
Frappe le gateway Hermes directement. C'est l'assurance-vie de la promesse
produit (« aucune invention »), pour un coût quasi nul. Aucun framework.

## Section 8 — Nettoyage cohérence (tout le repo)

Chaque incohérence relevée dans le repo, à corriger pendant l'implémentation.

| Fichier / ligne                                                         | Incohérence                                                                                                                    | Correction                                                                                                                                                                                                    |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `hermes/config.yaml.example:9`                                          | `base_url: 127.0.0.1:11434` → injoignable depuis le conteneur hermes vers le conteneur ollama                                  | `http://ollama:11434/v1`                                                                                                                                                                                      |
| `hermes/config.yaml.example:11` + `docker-compose.yml:46` + `README.md` | `context_length` incohérent : 65536 / 16384 / 32768 (3 valeurs)                                                                | aligner tout sur **65536** (minimum Hermes). `OLLAMA_CONTEXT_LENGTH=65536` + `OLLAMA_FLASH_ATTENTION=1` + `OLLAMA_KV_CACHE_TYPE=q4_0` pour tenir en 8 Go VRAM — à vérifier sur la GTX 1080 à l'implémentation |
| `hermes/config.yaml.example:2`                                          | commentaire « home de l'utilisateur qui lance le gateway » suppose un gateway sur l'hôte                                       | reformuler pour le déploiement conteneurisé                                                                                                                                                                   |
| `hermes/config.yaml.example:49-52`                                      | commentaires « multi-agents », « proxy `agent/app.py` », « assemblage déterministe côté serveur » → décrivent du code supprimé | réécrire : contexte injecté par le RAG Open WebUI, toolset modèle minimal                                                                                                                                     |
| `hermes/config.yaml.example:63`                                         | `host: 127.0.0.1` + commentaire « jamais 0.0.0.0 » contredit `API_SERVER_HOST=0.0.0.0` du compose                              | clarifier : bind `0.0.0.0` **dans** le conteneur, non publié, sur réseau sans egress                                                                                                                          |
| `docker-compose.yml:24-25`                                              | `ports: - "8642:8642"` expose le gateway au LAN                                                                                | **supprimer** (Open WebUI joint hermes par `net_internal`)                                                                                                                                                    |
| `docker-compose.yml` (réseaux)                                          | pas de réseau défini → bridge par défaut = `ollama`/`hermes` **ont internet** (chemin d'exfil)                                 | ajouter `net_internal` (`internal: true`) + `net_egress` + `egress-proxy`                                                                                                                                     |
| `docker-compose.yml:75`                                                 | `WEB_SEARCH: "false"`                                                                                                          | activer le web contrôlé + câbler le proxy                                                                                                                                                                     |
| `docker-compose.yml:33,78` + `.env.example:4`                           | clé par défaut `change-me-in-prod` sans garde-fou                                                                              | fail-fast au démarrage si inchangée                                                                                                                                                                           |
| `.gitignore:5`                                                          | `agent/data/maria.db` → dossier `agent/` supprimé                                                                              | retirer (ou pointer le nouveau chemin de données)                                                                                                                                                             |
| `hermes/skills/.../SKILL.md:48`                                         | « l'interface de l'entreprise enrichit chaque demande » → couche supprimée                                                     | reformuler vers le RAG                                                                                                                                                                                        |
| `README.md:11,43-49`                                                    | port 8642 présenté comme exposé ; section sécurité muette sur l'isolation réseau / egress / RAG                                | mettre à jour : hermes interne, topologie sécu, RAG, web contrôlé, mocks                                                                                                                                      |

`README.md:16` / `docker-compose.yml:14` « Aucun code proxy custom » **reste
vrai** (le RAG est natif Open WebUI) : à conserver.

## Ce qui est explicitement hors périmètre (YAGNI démo)

- Chiffrement at-rest, RBAC par employé, audit log, connecteur Sage 100 réel,
  secrets manager → **documentés** en Section 4, construits en prod.
- Interface custom → supprimée définitivement, Open WebUI uniquement.
