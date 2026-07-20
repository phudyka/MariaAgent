# Agent commercial local ETS Maria — démo RAG sécurisée

Agent de rédaction de mails commerciaux (réponse client, relance devis, mail
libre) pour ETS Maria (pisciniste, région niçoise, depuis 1937), **100 %
local** : modèle servi par Ollama, orchestré par Hermes, exposé aux employés
via Open WebUI, avec accès en lecture à des données d'entreprise mockées via
RAG. Aucune inférence externe, aucune donnée qui sort sans passer par un
canal contrôlé et audité.

Principe directeur : **on ne fait pas confiance au modèle, on contrôle ses
capacités au niveau de l'infrastructure.** Un mail client collé peut contenir
une injection de prompt ; même un modèle entièrement compromis ne doit avoir
**aucun chemin** pour exfiltrer des données.

## Stack

| Conteneur      | Rôle                                        | Réseau                        | Port publié |
|----------------|----------------------------------------------|-------------------------------|-------------|
| `ollama`       | Sert le modèle local (`qwen3:4b-instruct-2507-q4_K_M`), GPU | `net_internal`    | aucun       |
| `hermes`       | Gateway orchestrateur (API OpenAI-compatible) | `net_internal`                | aucun       |
| `open-webui`   | Interface employés, RAG natif + web search    | `net_internal`                | **3000**    |
| `egress-proxy` | Unique sortie internet (tinyproxy, allowlist) | `net_internal` + `net_egress` | aucun       |

**Un seul port est publié sur l'hôte : `open-webui` → `3000`**, derrière
`WEBUI_AUTH`. `hermes` n'est **jamais** exposé au LAN — Open WebUI le joint
en interne sur `net_internal`. Ollama n'est pas non plus publié.

Le métier (persona + règles anti-invention) vit dans `~/.hermes` :
`SOUL.md` + `skills/mails-commerciaux`. Aucun code proxy custom : le RAG est
natif Open WebUI.

## Sécurité par la topologie

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

Deux réseaux Docker :
- `net_internal` (`internal: true`) : **aucune route directe vers
  internet**. Héberge `ollama`, `hermes`, `open-webui`, et l'interface
  interne d'`egress-proxy`.
- `net_egress` (bridge, avec accès internet) : **seul** `egress-proxy` y est
  connecté.

**Invariants de sécurité (démontrables en RDV client) :**

1. **Aucun conteneur n'a d'egress direct.** L'unique chemin vers internet est
   `egress-proxy`, et il n'autorise que les domaines de l'allowlist
   (tinyproxy, ~10 lignes de conf). C'est du câblage, pas de la confiance.
2. `ollama` et `hermes` ne sont que sur `net_internal`. Leur seul usage
   d'internet est **via** `egress-proxy` (`HTTP_PROXY`), strictement
   allowlisté : `ollama` pour **pull le modèle** depuis le registre Ollama
   (setup), `hermes` n'en a **aucun** besoin. Toute destination hors
   allowlist est refusée → exfiltration impossible, même modèle retourné par
   une injection.
3. **Un seul port publié** : `open-webui:3000`, derrière `WEBUI_AUTH`.
   `hermes` n'est **pas** exposé au LAN — Open WebUI le joint par
   `net_internal`.
4. Données Maria montées en **lecture seule** (`:ro`).
5. Toolset du modèle inchangé : `[skills, todo, memory]`. **Aucun** tool
   `web`/`file`/`terminal` donné au modèle. Le web est fetché par Open WebUI,
   jamais par un tool que l'injection pourrait détourner.

## Données mock & RAG

Les données de démo (`data/`) mockent les sources réelles de l'entreprise,
un document par source, pensés pour le RAG :

| Document        | Contenu                                                      | Mock de          |
|-----------------|---------------------------------------------------------------|------------------|
| `catalogue.md`  | lignes `- REF \| nom \| marque \| prix € HT \| stock \| specs` | Sage 100        |
| `clients/*.md`  | fiche par client : contact, historique, notes                 | base clients     |
| `devis/*.md`    | n°, objet, montant, lignes, date d'envoi                       | devis/contrats   |
| `mails/*.md`    | fils d'échanges par client                                     | historique mails |
| `entreprise.md` | fiche entreprise + bloc signature                              | ancrage persona  |

Ces fichiers sont chargés dans une collection **« Knowledge »** Open WebUI
(montée `:ro`). Open WebUI embed en local, récupère le top-k pertinent pour
chaque demande et l'injecte dans la requête envoyée à Hermes — **c'est le
RAG qui joue le rôle d'enrichissement du contexte**, plus aucun
copier-coller manuel par l'employé. L'embedding model se pull une fois via
`egress-proxy` (allowlist).

## Démarrage

```bash
# 1. Config : copier le modèle d'env et fixer une vraie clé
cp .env.example .env
# éditer .env : MARIA_API_KEY=$(openssl rand -hex 24)

# 2. Build de l'image Hermes (depuis l'install git locale)
docker build -t hermes-agent:local ~/.local/opt/hermes-agent

# 3. Setup : fail-fast clé, up de la stack, pull du modèle, checklist finale
./setup.sh
```

`setup.sh` échoue immédiatement (fail-fast) si `MARIA_API_KEY` vaut encore
sa valeur par défaut de `.env.example`. Le pull du modèle et les images
Docker passent par `egress-proxy`, strictement allowlisté.

Une fois `setup.sh` terminé, ouvrir **http://localhost:3000**, créer le
compte de service (première connexion = admin), puis suivre la checklist
affichée en fin de script : modèle `maria-agent` (system prompt =
`hermes/SOUL.md`), collection Knowledge « Maria » pointée sur `data/`, web
search activé.

> GPU : le `docker-compose.yml` réserve un device nvidia pour `ollama`. Sur
> CPU, retirer le bloc `deploy.resources` — le modèle 4B tournera en CPU.

## Scénario de démo

1. *« Relance le devis 2024-118 du client Durand. »* → le RAG sort la fiche
   Durand + le devis 2024-118 + les derniers mails → brouillon en texte
   brut, montant et références **réels cités** depuis les données.
2. *« Le prix de la pompe modèle XJ-9000 ? »* (absente du catalogue) →
   renvoie `[À COMPLÉTER]`, **n'invente pas** = preuve anti-invention en
   direct (voir aussi `./eval.sh`).
3. *« Vérifie la dispo de la pièce X chez le fournisseur. »* → web contrôlé,
   seul le domaine fournisseur allowlisté (`proxy/filter`) est joignable.
4. Montrer la topologie ci-dessus : le modèle **n'a aucune route réseau**
   pour fuir les données, même retourné par une injection.

Vérification automatisée de l'anti-invention (3-4 prompts sans données
pertinentes, aucun `[À COMPLÉTER]` manquant, aucun prix/date inventé) :

```bash
./eval.sh
```

## Personnalisation

- `hermes/SOUL.md` : persona (artisan sérieux, vouvoiement, texte brut) et
  règles absolues anti-invention.
- `hermes/skills/mails-commerciaux/SKILL.md` : les trois tâches (réponse
  client, relance devis, mail libre).
- `data/` : remplacer les mocks par de vraies données (lecture seule),
  ré-uploader dans la collection Knowledge Open WebUI.
- `proxy/filter` : allowlist de domaines du proxy egress (registre Ollama,
  source de l'embedding model, domaine(s) fournisseur pour le web search).
  Rien d'autre ne doit sortir.

## Durcissement production

Cette démo prouve déjà 3 des 5 axes de sécurité (outsider, modèle compromis,
egress contrôlé). Le chiffrement at-rest, le RBAC par employé, l'audit log
et le connecteur Sage 100 réel sont **hors périmètre de la démo** et
documentés séparément :
[`docs/superpowers/specs/2026-07-20-securite-prod.md`](docs/superpowers/specs/2026-07-20-securite-prod.md).
