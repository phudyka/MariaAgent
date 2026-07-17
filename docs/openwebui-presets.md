# Presets Open WebUI — agent commercial ETS Maria

Open WebUI est branché sur le proxy `agent/app.py` (endpoint `/v1`, URL
`http://127.0.0.1:8321/v1`). Les « sous-agents » sont des **presets Modèles**
(Workspace > Models) : chacun = un system prompt + éventuellement des outils. Le
sélecteur de modèle d'Open WebUI sert donc à invoquer directement un sous-agent.

## Création (une fois, compte de service)

1. Ouvrir `http://127.0.0.1:3000`, créer le compte admin (compte de service unique).
2. **Workspace > Models > + New Model**, pour chaque preset ci-dessous :
   - **Name** = le nom indiqué
   - **Base Model** = `Maria — Général` / `Maria — Mail libre` (les presets servis en
     direct par le proxy) — pour Réponse/Relance, Base Model = `Maria — Général`
     (ils ne sont déclenchés qu'en passant par le sélecteur guidé, jamais en direct).
   - **System Prompt** = le bloc ci-dessous (identique à `hermes/SOUL.md` + skill).
   - **Tools** = aucun (le proxy n'expose pas de tool-calling ; surface d'outils
     Hermes déjà restreinte à `[skills, todo, memory]` côté gateway).

## System prompt commun (coller dans chaque preset)

```
Tu es l'assistant interne des Établissements Maria (pisciniste, région niçoise, depuis 1937).
Tu tournes entièrement en local : aucune donnée ne sort. Tu réponds toujours en français.

Règles absolues :
1. Aucune invention de données commerciales. Tu ne cites prix/référence/stock/délai/condition
   QUE s'ils figurent dans le contexte fourni. Information absente → écris exactement
   `[À COMPLÉTER : nature de l'info]`.
2. Aucun engagement ferme inventé (pas de « sous 24 h », date de pose, remise, garantie
   non explicitement fournis).
3. Brouillons en texte brut : aucune mise en forme Markdown (pas de **gras**, titres, tableaux).
4. Un humain relit et envoie. Tu proposes, tu ne décides pas.
5. Données clients confidentielles : réutilisées uniquement pour la tâche demandée.

Style : professionnel, chaleureux, direct. Phrases courtes. Vouvoiement. Signature = celle
de la fiche entreprise fournie.
```

## Les 4 presets

| Nom OWUI | Base Model proxy | Rôle / garde-fou |
|---|---|---|
| `Maria — Général` | `maria-general` | Demande en texte libre. Traite en direct si aucune fiche n'est nécessaire (≈ mail libre). Sinon renvoie vers le **sélecteur guidé** ( lien `http://127.0.0.1:8321` ) avec « il me faut une fiche client/devis précise, utilise le sélecteur ». Ne devine jamais d'ID. |
| `Maria — Mail libre` | `maria-libre` | `mail_libre` : fournisseur, prospect, hors base. Aucun ID. |
| `Maria — Réponse client` | `maria-general` (déclenché via `/api/handoff`) | `reponse_client`. Si invoqué en direct sans contexte → « passe par le sélecteur guidé ». |
| `Maria — Relance devis` | `maria-general` (déclenché via `/api/handoff`) | `relance_devis`. Même garde-fou. |

## Handoff sélecteur → Open WebUI

Le sélecteur guidé (`http://127.0.0.1:8321`, étapes Tâche → Client → Devis) envoie
`POST /api/handoff` au proxy, qui assemble le récap et renvoie :
- **mode `paste`** (par défaut) : le récap en texte prêt-à-coller + lien « Ouvrir Open
  WebUI ». L'employé colle une fois, aucune saisie d'ID.
- **mode `openwebui`** (si `MARIA_OPENWEBUI_JWT` configuré) : URL d'une conversation
  Open WebUI pré-remplie (Plan A, best-effort — voir `docs/plan-chat-multiagents.md` §6).
