# Spec — Refonte UX rédaction : sélection plutôt que saisie libre

Date : 2026-07-13 · Statut : validé (3 questions tranchées avec Pierre)

## Objectif

Remplacer le prompt texte libre par une sélection de données structurées :
client → devis → références catalogue. L'agent génère le mail depuis ces
données assemblées **côté serveur** (l'UI n'envoie que des IDs), pour
supprimer les erreurs de saisie (mauvaise ref, mauvais client, date mal
tapée) et accélérer l'usage.

## Décisions validées

1. **Mail libre conservé** en 3e tâche (textarea seul, comme aujourd'hui) —
   couvre prospects hors base, fournisseurs, partenaires.
2. **Devis optionnel** pour « Réponse client » (client seul suffit) ;
   **obligatoire** pour « Relance devis ».
3. **Mock : devis uniquement** (pas de contrats d'entretien). La colonne
   `type` existe dans le schéma pour les ajouter plus tard sans migration.

Ambiguïtés tranchées au design :

- Deux devis à la même date : la liste identifie par `numero` + objet +
  montant ; la date n'est jamais la clé de sélection.
- « Réponse client » : le textarea change de rôle — on y colle uniquement le
  mail reçu ; le contexte (qui, quel devis, quelles refs) vient de la
  sélection. « Relance devis » : zéro texte, pure sélection.

## Données

### Choix : SQLite stdlib + seed depuis CSV mock format Sage

- `sqlite3` de la stdlib : zéro dépendance nouvelle (contexte hermétique).
- Le **catalogue reste dans `catalogue_mock.csv`** (`catalog.py` inchangé) :
  source de vérité produits. Les lignes de devis référencent `sage_ref` et
  figent désignation + prix au moment du devis (comme Sage réel).
- Seed = importeur CSV `;` : le jour du chantier Sage (ROADMAP §2, palier
  export), on remplace les CSV mock par les exports réels, même importeur.

### Schéma

```sql
CREATE TABLE clients (
  id        INTEGER PRIMARY KEY,
  code      TEXT UNIQUE NOT NULL,     -- CT_Num Sage (ex: CDUPON01)
  nom       TEXT NOT NULL,
  contact   TEXT, email TEXT, telephone TEXT, ville TEXT,
  type      TEXT CHECK(type IN ('particulier','professionnel','collectivite'))
);

CREATE TABLE documents (
  id            INTEGER PRIMARY KEY,
  numero        TEXT UNIQUE NOT NULL,   -- DO_Piece Sage (ex: DE00042)
  client_id     INTEGER NOT NULL REFERENCES clients(id),
  type          TEXT NOT NULL DEFAULT 'devis',
  objet         TEXT NOT NULL,
  date_emission TEXT NOT NULL,          -- ISO 8601
  date_validite TEXT,
  statut        TEXT CHECK(statut IN ('DRAFT','SENT','ACCEPTED','REJECTED','EXPIRED')),
  montant_ht    REAL NOT NULL,          -- somme des lignes, figée au seed
  notes         TEXT
);

CREATE TABLE document_lignes (
  id               INTEGER PRIMARY KEY,
  document_id      INTEGER NOT NULL REFERENCES documents(id),
  sage_ref         TEXT NOT NULL,       -- AR_Ref → catalogue_mock.csv
  designation      TEXT NOT NULL,       -- snapshot
  quantite         REAL NOT NULL,
  prix_unitaire_ht REAL NOT NULL        -- snapshot
);
```

### Fichiers

| Fichier | Rôle |
|---|---|
| `agent/data/maria.db` | DB SQLite, **gitignorée**, régénérable |
| `agent/data/clients_mock.csv` | ~12 clients, format `;` |
| `agent/data/documents_mock.csv` | ~25 devis sur 12 mois (en-têtes) |
| `agent/data/document_lignes_mock.csv` | lignes, refs réelles du catalogue |
| `agent/db.py` | connexion, schéma, requêtes, seed auto si DB absente |
| `agent/seed_db.py` | import CSV → SQLite (exécutable seul : `python seed_db.py --force`) |

Mock : statuts variés dont plusieurs `SENT` vieux de 2–6 semaines (scénario
relance), montants cohérents avec les prix du catalogue, quantités réalistes
(tubes par barres, sable par sacs).

## API

```
GET  /api/clients?q=                       → [{id, code, nom, contact, ville, type, nb_documents}]
GET  /api/clients/{id}/documents?periode=  → [{id, numero, objet, date_emission, statut,
                                               montant_ht, lignes:[{sage_ref, designation,
                                               quantite, prix_unitaire_ht}]}]
POST /api/chat  { task, message?, client_id?, document_id?, history }
```

- `periode` ∈ {`3m`, `6m`, `12m`, vide = tous}.
- Validation `/api/chat` par tâche : `relance_devis` → `client_id` +
  `document_id` requis ; `reponse_client` → `client_id` requis, `document_id`
  optionnel, `message` = mail reçu ; `mail_libre` → `message` requis,
  pas d'IDs. `document_id` doit appartenir au `client_id` (422 sinon).
- Le serveur assemble le contexte (fiche client + devis + lignes) depuis la
  DB dans `prompts.py` — l'UI ne transmet jamais ces données en texte.
- L'événement SSE `meta` continue d'exposer les refs (chips UI) : refs des
  lignes du devis sélectionné, sinon recherche lexicale actuelle.

## UI (design system Peep v3)

Layout 420px / 1fr conservé. Panneau droit intact : SSE, chips refs,
Affiner, Copier, pastille santé. Panneau gauche → cascade à disclosure
progressive :

```
1 · TÂCHE      (Répondre) (Relancer) (Mail libre)
2 · CLIENT     [🔍 Rechercher…]                      ← §7.14 search bar
   CMART02 · Camping Les Martinets · Fréjus  ✓       ← sélection verte + barre aqua
3 · DEVIS      [période : segmented 3m/6m/12m/tous]  ← §7.9
   DE00042 · Rénov. filtration · 12/05  ●ENVOYÉ  1 845,00 €   ← chip §7.6, .num mono
     └ lignes dépliées : ref mono · désignation · qté · PU
[textarea « message reçu » — réponse client uniquement]
═══ RÉCAP CONTEXTE TRANSMIS À L'AGENT ═══            ← carte brand-wash §7.4
[            Générer le brouillon            ]
```

- Étapes masquées tant que la précédente n'est pas choisie ; en « mail
  libre », les étapes 2–3 disparaissent, textarea seul (comportement actuel).
- En « réponse client », l'étape 3 porte la mention « optionnel » +
  action « Aucun devis concerné ».
- **Élément signature** : la carte récap (client, devis, refs exactes,
  montant) avant génération — l'employé voit ce que l'agent reçoit.
- Statuts : exactement le `statusConfig` Peep §7.6 + `EXPIRED` (neutre
  `fg-3`, l'ambre reste réservé à `DRAFT`).
- Recherche client : filtre côté serveur (`q` sur code/nom/ville), debounce
  200 ms, liste bornée (~50).

## Prompts

`prompts.py` gagne un bloc `CONTEXTE CLIENT/DEVIS` structuré (généré depuis
la DB) inséré comme le bloc catalogue actuel. Les instructions de
`relance_devis` et `reponse_client` sont réécrites pour référencer ces
données (« le devis ci-dessous », plus de « si le numéro manque »
quand un devis est sélectionné). Garde-fous inchangés (pas d'invention,
`[À COMPLÉTER]`).

## Incréments (prototype fonctionnel à chaque étape)

1. `db.py` + CSV mock + seed — testable en CLI, l'app existante tourne toujours.
2. Endpoints `GET /api/clients*` — testables au curl, UI inchangée.
3. `POST /api/chat` accepte les IDs (rétro-compatible : `message` seul marche encore).
4. UI cascade de sélection + carte récap.
5. Docs : README (structure, seed), DEPLOY_MARIA (étape seed), ROADMAP (§2 : pointer l'importeur).

## Hors périmètre

Connexion Sage réelle, écriture dans la DB depuis l'UI, comptes
utilisateurs, contrats d'entretien (colonne `type` prête).
