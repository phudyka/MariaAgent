# Plan v2 — UI façon ChatGPT/Claude + architecture multi-agents (ETS Maria)

> Corrige le plan v1 sur les deux points bloquants relevés en revue : (1) la sélection
> client/devis ne doit jamais reposer sur l'employé qui tape des IDs, (2) la délégation
> de l'agent « Général » vers un sous-agent doit être un mécanisme réel, pas une phrase
> qui décrit un comportement souhaité sans dire comment il s'obtient.

## 0. Décisions validées (v2)

- **Le sélecteur guidé actuel reste le seul point d'entrée pour `reponse_client` et
  `relance_devis`.** Recherche/clic, zéro ID retapé à la main — comme aujourd'hui. Ce
  n'est pas un renoncement à l'UX chat : c'est reconnaître que « façon ChatGPT/Claude »
  s'applique à la génération et à l'itération sur le brouillon, pas au choix d'un dossier
  client précis. Même ChatGPT/Claude ne font pas deviner un fichier précis par la
  conversation quand la précision compte — ils passent par un sélecteur.
- **Le sélecteur transmet son résultat à une conversation Open WebUI déjà ouverte** sur
  le bon preset, sans que l'employé retape rien. Deux mécanismes possibles, un plan A et
  un plan B de secours — tranchés par un spike technique avant d'écrire le code définitif
  (voir §4 étape 0 et §6 risque 1), pas par hypothèse comme dans le plan v1.
- **L'agent « Général » ne devine plus d'IDs à partir de texte libre.** Le plan v1
  proposait un parsing de type `[CLIENT:123][DEVIS:456]` extrait du message et un « appel
  interne » jamais conçu. En v2, Général a un rôle volontairement borné : (a) traiter en
  direct les demandes qui ne nécessitent aucune fiche (équivalent `mail_libre`), (b) pour
  tout le reste, renvoyer explicitement l'employé vers le sélecteur avec un lien. Zéro
  extraction d'ID depuis du texte libre, zéro nouveau tool-calling.
- **4 presets Open WebUI au lieu de 5** : on supprime « Récap » comme preset séparé — le
  récapitulatif n'est pas une tâche, c'est simplement le message d'ouverture que le
  sélecteur dépose dans la conversation (il existe déjà comme carte dans l'UI actuelle).
- **Pas de comptes Open WebUI par employé pour cette itération** : un compte de service
  unique. Cohérent avec la limite déjà assumée par le projet aujourd'hui (« une
  conversation à la fois, pas de comptes utilisateurs ») — à faire évoluer plus tard,
  c'est déjà dans ROADMAP §gouvernance/comptes.

## 1. Vérifications (reprises du plan v1, toujours valables)

- **Open WebUI** : licence « Open WebUI License » (BSD-3 + clause de branding depuis
  v0.6.6). Exception ≤ 50 utilisateurs/30j applicable à l'usage interne ETS Maria.
  `OPENAI_API_BASE_URL`/`OPENAI_API_KEY` = `MARIA_HERMES_URL`/`MARIA_HERMES_KEY` (proxy
  interposé, voir §2). `Workspace > Models` permet bien de créer des presets avec system
  prompt et tools restreints par modèle — confirmé par la doc actuelle.
- **Hermes Agent** : `delegate_task` existe et est stable, mais les « profils d'agent »
  nommés sont encore un issue non mergé en 2026 → **on ne s'appuie pas dessus**, les
  sous-agents restent modélisés côté proxy + presets Open WebUI. Toolset `api_server`
  reste `[skills, todo, memory]`, reconduit explicitement, jamais élargi.
- **Anti-injection/anti-hallucination** : couverts tant que l'assemblage des données
  reste par ID, déterministe, côté serveur — jamais laissé au modèle. C'est la base de
  toute la v2 (voir §3).

## 2. Architecture cible

```
Poste employé
   │
   ├─ Sélecteur (index.html allégé — étapes 1-3 seulement : Tâche → Client → Devis)
   │     └─ bouton "Générer" ──► POST agent/app.py /api/handoff
   │                              {task, client_id, document_id?, message?}
   │                                 │
   │                                 ├─ validations 422 identiques à l'actuel /api/chat
   │                                 │  (réutilise db.py tel quel)
   │                                 ├─ assemble le récap (prompts.py, INCHANGÉ)
   │                                 └─ Plan A (à valider par spike) : crée une
   │                                    conversation Open WebUI via son API interne,
   │                                    y dépose le récap comme 1er message, renvoie
   │                                    l'URL de cette conversation → redirection
   │                                    navigateur automatique.
   │                                    Plan B (filet de sécurité, toujours implémenté) :
   │                                    renvoie le récap en texte prêt-à-coller + un
   │                                    lien "Ouvrir Open WebUI" (nouvel onglet) ;
   │                                    l'employé colle une fois, aucune saisie d'ID.
   │
   └─ Open WebUI :3000 (accès direct, sans passer par le sélecteur, pour les cas
      qui n'ont besoin d'aucune fiche) :
         - preset "Maria — Mail libre" : invocation directe, aucun ID
         - preset "Maria — Général" : l'employé décrit son besoin en texte libre ;
           si ça nécessite un client/devis précis, l'agent répond en renvoyant vers
           le sélecteur (lien), il ne devine jamais

Open WebUI :3000
   │ OPENAI_API_BASE_URL = http://127.0.0.1:8321/v1  (proxy agent/app.py, NOUVEAU rôle)
   ▼
Proxy agent/app.py :8321
   ├─ GET  /v1/models            → 4 presets (maria-general, maria-libre,
   │                                 maria-reponse, maria-relance)
   ├─ POST /v1/chat/completions  → UNIQUEMENT pour maria-general / maria-libre
   │                                 (aucun parsing d'ID : ces presets n'en ont pas besoin)
   │                                 relaye en SSE vers le gateway Hermes, réémet au
   │                                 format OpenAI-compatible
   ├─ POST /api/handoff          → point d'entrée du sélecteur (voir ci-dessus),
   │                                 seul endroit où client_id/document_id transitent
   ├─ /api/clients, /api/clients/{id}/documents, /api/health : GARDÉS (utilisés par
   │    le sélecteur allégé et pour le debug/tests)
   └─ /  : sélecteur allégé (étapes 1-3 seulement, panneau de streaming maison retiré)
        ▼ 127.0.0.1:8642  Gateway Hermes (toolset [skills, todo, memory], INCHANGÉ) ▼ Ollama
```

### Presets Open WebUI

| Preset | Invocation | Rôle |
|---|---|---|
| `Maria — Général` | directe, depuis Open WebUI | Décrit un besoin en texte libre. Traite en direct si aucune fiche n'est nécessaire (≈ mail libre) ; sinon renvoie vers le sélecteur (lien), ne devine jamais un client/devis. |
| `Maria — Mail libre` | directe, depuis Open WebUI | `mail_libre` : fournisseur, prospect, hors base. Aucun ID. |
| `Maria — Réponse client` | uniquement via `/api/handoff` | `reponse_client`. Si invoqué sans contexte (accès direct par erreur), le system prompt lui fait dire explicitement « il me faut une fiche client, passe par le sélecteur » plutôt que d'improviser. |
| `Maria — Relance devis` | uniquement via `/api/handoff` | `relance_devis`, même garde-fou que ci-dessus si contexte absent. |

Chaque preset porte le même system prompt que `hermes/SOUL.md` + skill
`mails-commerciaux` (anti-invention, texte brut) — le proxy ré-injecte aussi
l'instruction de tâche (`prompts.TASKS`), comme aujourd'hui : double couche.

## 3. Couverture des contraintes non négociables

- **Anti-injection** : toolset Hermes `api_server` inchangé (`[skills, todo, memory]`).
  Le proxy n'expose toujours aucun tool-calling au modèle. Contrairement au plan v1, il
  n'y a **plus de parsing d'ID à partir d'un message utilisateur** — c'est ce point
  précis qui était le trou de sécurité/fiabilité le plus flou du plan v1 ; en v2, les IDs
  ne transitent que via `/api/handoff`, appelé par le sélecteur (interface contrôlée),
  jamais interprétés depuis du texte libre côté `/v1/chat/completions`.
- **Anti-hallucination** : inchangé — `db.py`/`catalog.py` restent les seules sources de
  données, assemblage déterministe par ID.
- **Texte brut** : inchangé — à valider visuellement que le rendu Open WebUI n'introduit
  pas de mise en forme Markdown non désirée dans ce qui sera copié-collé.
- **Validations 422** (devis d'un autre client, IDs requis selon la tâche) : portées par
  `/api/handoff`, qui reprend telles quelles les règles de l'actuel `/api/chat`.
- **Tests** : `test_api.py` étendu pour `/api/handoff` (mêmes cas 422 qu'aujourd'hui) et
  pour `/v1/models` + `/v1/chat/completions` côté `maria-general`/`maria-libre`
  uniquement — pas de test de parsing d'ID puisqu'il n'existe plus.
- **100 % local** : télémétrie et vérification de mise à jour d'Open WebUI coupées
  explicitement (`ENABLE_COMMUNITY_FEATURES=false` + toute autre bascule identifiée
  pendant le spike, à lister précisément plutôt que supposée complète).

## 4. Étapes d'implémentation

0. **Spike (avant tout code définitif)** : vérifier si l'API interne d'Open WebUI permet,
   pour un compte de service, de créer une conversation pré-remplie et d'en récupérer une
   URL stable pour redirection. Cette API n'est pas un contrat documenté/garanti par le
   projet (contrairement à l'endpoint OpenAI-compatible ou à `Workspace > Models`) — d'où
   le spike avant de s'engager dessus. Si ça marche de façon fiable → Plan A. Sinon →
   Plan B (texte prêt-à-coller) implémenté d'office, sans dépendre d'API non documentée.
1. **Docker Open WebUI** : `docker-compose.yml` + `.env` (`ghcr.io/open-webui/open-webui`,
   port 3000, volume `open-webui:/app/backend/data`, `WEBUI_AUTH=true` avec un compte de
   service unique, télémétrie/update-check désactivés selon la checklist du spike).
   Ajout à `run.sh`.
2. **Alléger `index.html`** : garder les étapes 1-3 (Tâche/Client/Devis + carte récap),
   retirer les étapes 4-5 (textarea de génération, panneau de streaming maison) au profit
   du bouton de handoff.
3. **`agent/app.py`** : nouvelle route `/api/handoff` (Plan A ou B selon le spike),
   `/v1/models` (4 presets), `/v1/chat/completions` limité à `maria-general`/
   `maria-libre`. Réutilise `db.py`, `catalog.py`, `prompts.py` sans les modifier (YAGNI).
4. **Presets Open WebUI** : créer les 4 presets avec leurs system prompts respectifs,
   y compris le garde-fou « pas de contexte → je renvoie vers le sélecteur » pour
   Réponse client/Relance devis.
5. **Tests + doc** : étendre `test_api.py`, mettre à jour README (nouvelle archi,
   démarrage Open WebUI) et ROADMAP (§multi-agents). Documenter le sélecteur allégé
   comme évolution de l'UX de sélection existante, pas comme sa suppression.

## 5. Hors périmètre (inchangé)

Sage 100 / Peep, RAG documentaire, comptes multi-utilisateurs, envoi réel — voir
`ROADMAP.md`.

## 6. Risques

1. **[Le plus important] Fiabilité du Plan A (API interne Open WebUI).** Non documentée
   officiellement, peut casser à une montée de version. Le spike (§4 étape 0) doit
   trancher tôt. Le Plan B reste implémenté même si le Plan A fonctionne, pour ne jamais
   dépendre d'un seul mécanisme fragile face à une mise à jour d'Open WebUI.
2. **Rendu Markdown vs texte brut** : le modèle produit du texte brut, mais Open WebUI
   peut mettre en forme l'affichage. À valider visuellement ; le copier-coller doit
   rester fidèle.
3. **Compte de service unique** : pas de traçabilité par employé dans cette itération —
   limite assumée, cohérente avec l'existant, à ajouter dans « Limites connues » du
   README plutôt que découverte plus tard.
4. **Presets Réponse client/Relance devis invoqués hors handoff** (accès direct par
   erreur ou curiosité) doivent avoir un comportement testé explicitement, pas juste
   décrit dans le system prompt.