# Agent commercial local ETS Maria — démo RAG sécurisée

Agent de rédaction de mails commerciaux (réponse client, relance devis, mail
libre) pour ETS Maria (pisciniste, région niçoise, depuis 1937). Interface, RAG
et orchestration tournent en local (Hermes + Open WebUI) ; l'inférence passe par
l'**API Mistral** (free tier) : `mistral-small-latest`, modèle **open-weights
Apache 2.0 (24B)** choisi pour être exactement ce qu'un Mac mini (M4 Pro 48 Go,
cible d'achat) fera tourner en local via Ollama — même persona, mêmes poids,
seule l'URL changera. Aucune donnée ne sort sans passer par l'unique canal
contrôlé et allowlisté (`api.mistral.ai` seul domaine d'inférence autorisé). Le
mode 100 % local de la v1 (Ollama) reste disponible via le profil compose
`local`.

Principe directeur : **on ne fait pas confiance au modèle, on contrôle ses
capacités au niveau de l'infrastructure.** Un mail client collé peut contenir
une injection de prompt ; même un modèle entièrement compromis ne doit avoir
**aucun chemin** pour exfiltrer des données.

> **Free tier Mistral** : les requêtes peuvent être utilisées pour
> l'entraînement. Données de démo uniquement — **jamais de vrais mails
> clients**. (Passage en prod : tier payant avec opt-out, ou retour 100 % local
> sur le Mac mini.)

## Stack

| Conteneur      | Rôle                                                       | Réseau                         | Port publié               |
| -------------- | ---------------------------------------------------------- | ------------------------------ | ------------------------- |
| `hermes`       | Gateway orchestrateur → inférence API Mistral (via egress) | `net_internal`                 | aucun                     |
| `ollama`       | Inférence locale v1 — profil `local`, arrêté par défaut    | `net_internal`                 | aucun                     |
| `open-webui`   | Interface employés, RAG natif + web search                 | `net_internal`                 | **3000**                  |
| `egress-proxy` | Unique sortie internet (tinyproxy, allowlist)              | `net_internal` + `net_egress`  | aucun                     |
| `mailpit`      | Boîte mail factice (démo, hors produit) — `seed-inbox.sh`  | `net_internal` + `net_publish` | 8025/1025 (loopback seul) |

**Un seul port PRODUIT est publié sur l'hôte : `open-webui` → `3000`**, derrière
`WEBUI_AUTH`. `hermes` n'est **jamais** exposé au LAN — Open WebUI le joint en
interne sur `net_internal`. `ollama` (profil `local`, arrêté par défaut) n'est
pas non plus publié. Exception démo assumée : `mailpit` (outil de démo, hors
produit) publie son webmail/SMTP en loopback seul, jamais LAN ; l'inbox se seed
via `./seed-inbox.sh`.

Le métier (persona + règles anti-invention) vit dans `~/.hermes` : `SOUL.md` +
`skills/mails-commerciaux`. Aucun code proxy custom : le RAG est natif Open
WebUI.

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
┌────▼───┐          │   │          ┌─────▼───────┐
│ hermes │──────────┴───┴─────────►│ egress-proxy │──► internet
│gateway │  HTTPS_PROXY (inférence │  (allowlist) │    (api.mistral.ai +
└────────┘   API Mistral)          └──────────────┘     domaines listés SEULS)
 no egress direct   (ollama : profil `local`, arrêté par défaut, pas dessiné)
```

Deux réseaux Docker :

- `net_internal` (`internal: true`) : **aucune route directe vers internet**.
  Héberge `hermes`, `open-webui` (et `ollama` quand le profil `local` est
  activé), plus l'interface interne d'`egress-proxy`.
- `net_egress` (bridge, avec accès internet) : **seul** `egress-proxy` y est
  connecté.

**Invariants de sécurité (démontrables en RDV client) :**

1. **Aucun conteneur n'a d'egress direct.** L'unique chemin vers internet est
   `egress-proxy`, et il n'autorise que les domaines de l'allowlist (tinyproxy,
   ~10 lignes de conf). C'est du câblage, pas de la confiance.
2. `hermes` (et `ollama` en profil `local`) ne sont que sur `net_internal`. Leur
   seul usage d'internet est **via** `egress-proxy`
   (`HTTP_PROXY`/`HTTPS_PROXY`), strictement allowlisté : `hermes` vers
   `api.mistral.ai` (inférence) et rien d'autre ; `ollama` vers le registre
   Ollama (pull, profil `local` seulement). Toute destination hors allowlist est
   refusée → exfiltration impossible, même modèle retourné par une injection.
3. **Un seul port publié** : `open-webui:3000`, derrière `WEBUI_AUTH`. `hermes`
   n'est **pas** exposé au LAN — Open WebUI le joint par `net_internal`.
4. **Source** des données Maria (`data/`) montée en lecture seule (`/data:ro`)
   dans `open-webui` : impossible de la modifier depuis le conteneur. La
   collection **Knowledge** ingérée (store vectoriel, issue d'un upload manuel
   via l'UI) vit, elle, dans le volume `open-webui` en **lecture-écriture** — ce
   n'est **pas** un invariant `:ro` à ce stade. L'ingestion read-only
   automatisée est une piste de durcissement documentée dans
   [`docs/superpowers/specs/2026-07-20-securite-prod.md`](docs/superpowers/specs/2026-07-20-securite-prod.md).
5. Toolset du modèle **vide** (`api_server: []`) : zéro tool, zéro surface
   d'injection — les règles vivent dans le persona. **Aucun** tool
   `web`/`file`/`terminal` donné au modèle. Le web est fetché par Open WebUI,
   jamais par un tool que l'injection pourrait détourner.

## Données mock & RAG

Les données de démo (`data/`) mockent les sources réelles de l'entreprise, un
document par source, pensés pour le RAG :

| Document        | Contenu                                                        | Mock de          |
| --------------- | -------------------------------------------------------------- | ---------------- |
| `catalogue.md`  | lignes `- REF \| nom \| marque \| prix € HT \| stock \| specs` | Sage 100         |
| `clients/*.md`  | fiche par client : contact, historique, notes                  | base clients     |
| `devis/*.md`    | n°, objet, montant, lignes, date d'envoi                       | devis/contrats   |
| `mails/*.md`    | fils d'échanges par client                                     | historique mails |
| `entreprise.md` | fiche entreprise + bloc signature                              | ancrage persona  |

La source canonique (`data/`) est montée en lecture seule (`/data:ro`) dans le
conteneur `open-webui` (`docker-compose.yml`). Ces fichiers sont **uploadés
manuellement** (via l'UI) dans une collection **« Knowledge »** Open WebUI ;
cette collection (store vectoriel) vit dans le volume `open-webui`, en
**lecture-écriture** — ce n'est pas la source, et ce n'est **pas** en lecture
seule à ce stade (l'ingestion read-only automatisée est une piste de
durcissement documentée dans
[`docs/superpowers/specs/2026-07-20-securite-prod.md`](docs/superpowers/specs/2026-07-20-securite-prod.md)).
Open WebUI embed en local, récupère le top-k pertinent pour chaque demande et
l'injecte dans la requête envoyée à Hermes — **c'est le RAG qui joue le rôle
d'enrichissement du contexte**, plus aucun copier-coller manuel par l'employé.
L'embedding model se pull une fois via `egress-proxy` (allowlist).

## Démarrage

```bash
# 1. Config : copier le modèle d'env et fixer les clés
cp .env.example .env
# éditer .env : MARIA_API_KEY=$(openssl rand -hex 24)
#               MISTRAL_API_KEY=<clé free tier créée sur console.mistral.ai>

# 2. Build de l'image Hermes (depuis l'install git locale — adapter le chemin
#    si l'install n'est pas/plus dans ~/.local/opt/hermes-agent)
docker build -t hermes-agent:local ~/.local/opt/hermes-agent

# 3. Setup : fail-fast clés, up de la stack, checklist finale
./setup.sh
```

`setup.sh` échoue immédiatement (fail-fast) si `MARIA_API_KEY` ou
`MISTRAL_API_KEY` valent encore leur valeur par défaut de `.env.example`.
L'inférence — comme tout flux sortant — passe par `egress-proxy`, strictement
allowlisté.

> **Important** : `docker compose up -d` lancé seul ne fait **pas** ce contrôle
> de clé — il démarrerait la stack même avec la clé par défaut. Toujours
> démarrer via `./setup.sh`, seul point d'entrée qui refuse `change-me-in-prod`.

Une fois `setup.sh` terminé, ouvrir **http://localhost:3000**, créer le compte
de service (première connexion = admin), puis suivre la checklist affichée en
fin de script : modèle « Maria — catalogue » (base : `maria-agent`, system
prompt vide — la persona `SOUL.md` est appliquée par le gateway Hermes),
collection Knowledge « Maria » pointée sur `data/`, web search activé.

> Vérification bring-up recommandée : confirmer l'absence de route sortante
> depuis `hermes`/`ollama`. `nslookup` n'étant pas dans l'image, tester la
> socket :
> `docker compose exec hermes python3 -c "import socket;
> socket.create_connection(('1.1.1.1',443),timeout=5)"`
> doit échouer (`OSError`) — canal résiduel indépendant du proxy HTTP, détaillé
> dans
> [`docs/superpowers/specs/2026-07-20-securite-prod.md`](docs/superpowers/specs/2026-07-20-securite-prod.md).

> GPU : plus requis par défaut (inférence via API Mistral). Le service `ollama`
> (profil `local`) garde sa réservation nvidia pour le retour au mode 100 %
> local.

## Scénario de démo

### Démo devis filtration (tâche principale)

Le chiffrage est 100 % déterministe : la commande `./devis` (script Python
sans dépendance) lit `data/abaque-filtration.md` et produit le devis complet
(lignes, totaux, `[À COMPLÉTER]` pour MO/tuyauterie). **Le modèle ne chiffre
jamais** : il extrait volume/dimensions du mail client, calcule le volume et
renvoie la commande à lancer ; un devis généré se recopie verbatim dans un
brouillon de mail. Le RAG (collection « Knowledge ») sert le reste :
`data/catalogue.md` (ré-upload après modification), fiches clients, devis,
mails.

Démo :

- `./devis 8 4 1.5 --client "M. Durand"` → devis complet tranche 41–50 m³,
  MO et tuyauterie à compléter.
- Coller un mail « piscine 8 mètres sur 4, environ 1m50 de fond » dans l'agent
  → « Volume : 48 m³. Générer le devis : ./devis 8 4 1,5 », zéro référence,
  zéro prix.
- _« Fais-moi un devis filtration »_ → l'agent demande le volume.
- _« Piscine à débordement de 120 m³ »_ → orientation étude atelier, zéro
  chiffre (idem `./devis 120` : étude atelier).

L'abaque est GÉNÉRÉ
(`npx -y tsx tools/gen-abaque.ts > data/abaque-filtration.md`) depuis le moteur
hydraulique du prototype Peep (dépôt frère `../Peep`), jamais exécuté en
production. Dimensionnement provisoire : quand Maria corrige la logique, éditer
`PARAMS`/le moteur, régénérer — `./devis` lit le nouveau fichier directement.

### Démo mails

1. _« Relance le devis 2024-118 du client Durand. »_ → le RAG sort la fiche
   Durand + le devis 2024-118 + les derniers mails → brouillon en texte brut,
   montant et références **réels cités** depuis les données.
2. _« Le prix de la pompe modèle XJ-9000 ? »_ (absente du catalogue) → renvoie
   `[À COMPLÉTER]`, **n'invente pas** = preuve anti-invention en direct (voir
   aussi `./eval.sh`).
3. _« Vérifie la dispo de la pièce X chez le fournisseur. »_ → web contrôlé,
   seul le domaine fournisseur allowlisté (`proxy/filter`) est joignable.
   (Préalable : Web Search activé dans Admin Panel > Settings — réglage persisté
   en DB, les env ne suffisent pas après le 1er boot.)
4. Montrer la topologie ci-dessus : le modèle **n'a aucune route réseau** pour
   fuir les données, même retourné par une injection.

Vérification automatisée de l'anti-invention (3-4 prompts sans données
pertinentes, aucun `[À COMPLÉTER]` manquant, aucun prix/date inventé) :

```bash
./eval.sh
```

## Personnalisation

- `hermes/SOUL.md` : persona (artisan sérieux, vouvoiement, texte brut) et
  règles absolues anti-invention.
- `hermes/skills/mails-commerciaux/SKILL.md` : les trois tâches (réponse client,
  relance devis, mail libre).
- `data/` : remplacer les mocks par de vraies données (lecture seule),
  ré-uploader dans la collection Knowledge Open WebUI.
- `proxy/filter` : allowlist de domaines du proxy egress (`api.mistral.ai` pour
  l'inférence, registre Ollama, source de l'embedding model, domaine(s)
  fournisseur pour le web search). Rien d'autre ne doit sortir.

## Durcissement production

Cette démo prouve déjà 3 des 5 axes de sécurité (outsider, modèle compromis,
egress contrôlé). Le chiffrement at-rest, le RBAC par employé, l'audit log et le
connecteur Sage 100 réel sont **hors périmètre de la démo** et documentés
séparément :
[`docs/superpowers/specs/2026-07-20-securite-prod.md`](docs/superpowers/specs/2026-07-20-securite-prod.md).
