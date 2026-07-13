# Sélection client→devis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer la saisie libre par une sélection client → devis → refs, contexte assemblé côté serveur depuis une base SQLite mock format Sage.

**Architecture:** SQLite stdlib (`agent/db.py`) seedée depuis 3 CSV mock format Sage (`;`) ; 2 endpoints GET de lecture ; `/api/chat` accepte des IDs et assemble le contexte depuis la DB dans `prompts.py` ; UI mono-fichier (`index.html`) : cascade de sélection dans le panneau gauche, panneau droit (SSE/Affiner/Copier) intact.

**Tech Stack:** Python 3.14, FastAPI, sqlite3 (stdlib), pytest (nouveau, dev), vanilla JS/CSS tokens Peep v3.

## Global Constraints

- Hermétique : aucune ressource externe (fonts locales, pas de CDN), aucune dépendance runtime nouvelle — `sqlite3` stdlib uniquement ; `pytest` en dépendance dev.
- Design system Peep v3 (`DESIGN_SYSTEM.md`) : tokens existants du `:root` de `index.html`, statuts §7.6, `EXPIRED` en neutre `fg-3`.
- Garde-fous prompts inchangés (pas d'invention, `[À COMPLÉTER]`, texte brut).
- `catalog.py`/`catalogue_mock.csv` restent la source de vérité produits ; la DB référence `sage_ref`.
- Prototype fonctionnel après chaque task ; vérifier avec `pytest agent/tests -q` + serveur.
- Pas de commit git (le dépôt n'a pas de commit initial ; l'utilisateur n'a rien demandé côté git).
- Aujourd'hui = 2026-07-13 (les périodes 3m/6m/12m des mocks sont calées dessus).

---

### Task 1: DB SQLite + CSV mock + seed

**Files:**
- Create: `agent/db.py`, `agent/seed_db.py`
- Create: `agent/data/clients_mock.csv`, `agent/data/documents_mock.csv`, `agent/data/document_lignes_mock.csv`
- Create: `agent/tests/conftest.py`, `agent/tests/test_db.py`
- Modify: `agent/requirements.txt` (+`pytest>=8`), `.gitignore` (+`agent/data/maria.db`)

**Interfaces (Produces):**
- `db.connect() -> sqlite3.Connection` (row_factory=Row)
- `db.ensure_db() -> None` — seed auto si `maria.db` absente
- `db.search_clients(q: str = "", limit: int = 50) -> list[dict]` — clés : id, code, nom, contact, email, telephone, ville, type, nb_documents ; filtre insensible accents/casse sur code+nom+ville+contact (fold côté Python, volume minuscule)
- `db.get_client(client_id: int) -> dict | None`
- `db.client_documents(client_id: int, periode: str = "") -> list[dict]` — periode ∈ {"3m","6m","12m",""} ; tri date_emission DESC ; chaque doc embarque `lignes: list[dict]`
- `db.get_document(document_id: int) -> dict | None` — avec `lignes` et `client_id`
- `seed_db.seed(force: bool = False) -> None` + CLI `python agent/seed_db.py --force`

**Step 1 : CSV mock** (format `;`, en-têtes exacts ci-dessous). Lignes : désignation + prix résolus depuis `catalogue_mock.csv` au seed (colonnes optionnelles `designation`/`prix_unitaire_ht` prioritaires si présentes — chemin d'import Sage futur). `montant_ht` documents = somme des lignes, calculée au seed.

`clients_mock.csv` :
```csv
code;nom;contact;email;telephone;ville;type
CDURAN01;Durand Jean-Marc;Jean-Marc Durand;jm.durand@orange.fr;06 12 45 78 90;Nice;particulier
CMARTI01;Camping Les Martinets;Sophie Berthier;s.berthier@lesmartinets.fr;04 93 55 12 40;Antibes;professionnel
CHOTEL01;Hôtel Bellevue Riviera;Marc Fontana;direction@bellevue-riviera.com;04 93 88 27 61;Menton;professionnel
CLEROY01;Leroy Catherine;Catherine Leroy;cathleroy06@gmail.com;06 74 21 33 08;Cagnes-sur-Mer;particulier
CMAIRI01;Mairie de Vence — Services techniques;Paul Giordano;p.giordano@vence.fr;04 93 58 40 22;Vence;collectivite
CPISCI01;Aqua Bleu Services;Karim Haddad;contact@aquableu-services.fr;04 92 09 15 73;Saint-Laurent-du-Var;professionnel
CROSSI01;Rossi Antoine;Antoine Rossi;antoine.rossi@free.fr;06 61 08 44 27;Mougins;particulier
CRESID01;Résidence Les Palmiers (syndic);Isabelle Meunier;syndic@lespalmiers06.fr;04 93 20 71 15;Villeneuve-Loubet;professionnel
CBLANC01;Blanc Sylvie;Sylvie Blanc;sylvie.blanc06@laposte.net;06 88 90 12 35;Grasse;particulier
CGYMCL01;Gym Club Azur;Thomas Ricci;t.ricci@gymclubazur.fr;04 93 42 60 18;Biot;professionnel
CPETIT01;Petit Frédéric;Frédéric Petit;fred.petit@wanadoo.fr;06 45 32 19 76;Valbonne;particulier
CCAMPE01;Domaine du Grand Pin (camping);Nathalie Weber;accueil@domainegrandpin.fr;04 93 77 30 52;Cannes;professionnel
CNAVAR01;Navarro Élodie;Élodie Navarro;elodie.navarro@gmail.com;06 29 84 51 03;Nice;particulier
```
(CNAVAR01 : volontairement **zéro devis** → teste l'empty state + réponse client sans devis.)

`documents_mock.csv` :
```csv
numero;client_code;type;objet;date_emission;date_validite;statut;notes
DE00092;CDURAN01;devis;Remplacement pompe de filtration piscine 9x4;2025-08-14;2025-09-13;ACCEPTED;
DE00095;CMARTI01;devis;Rénovation filtration bloc technique bassin principal;2025-09-02;2025-10-02;ACCEPTED;
DE00097;CLEROY01;devis;Électrolyseur au sel + régulation pH;2025-09-18;2025-10-18;REJECTED;A trouvé moins cher en ligne
DE00099;CHOTEL01;devis;Hivernage bassin + bâche à bulles 10x5;2025-10-06;2025-11-05;ACCEPTED;
DE00101;CROSSI01;devis;Remplacement sable filtre D500 + vanne 6 voies;2025-10-21;2025-11-20;ACCEPTED;
DE00103;CMAIRI01;devis;Étude renouvellement filtration bassin municipal;2025-11-12;2026-01-11;EXPIRED;Budget reporté au prochain exercice
DE00105;CBLANC01;devis;Projecteur LED + coffret électrique filtration;2025-12-09;2026-01-08;EXPIRED;
DE00106;CPISCI01;devis;Lot skimmers + buses chantier neuf (revente pro);2026-01-15;2026-02-14;ACCEPTED;Remise pro appliquée en marge
DE00108;CRESID01;devis;Remise en état filtration piscine copropriété;2026-02-10;2026-03-12;REJECTED;Vote AG défavorable
DE00110;CPETIT01;devis;Robot électrique + bâche à bulles 8x4;2026-03-05;2026-04-04;ACCEPTED;
DE00111;CDURAN01;devis;Passage au verre filtrant + vanne 6 voies;2026-03-24;2026-04-23;EXPIRED;Client parti en déplacement longue durée
DE00113;CGYMCL01;devis;Régulation pH + électrolyseur bassin intérieur;2026-04-08;2026-06-07;REJECTED;Prestataire habituel retenu
DE00114;CCAMPE01;devis;Équipement complet filtration piscine mobil-home;2026-04-16;2026-06-15;ACCEPTED;
DE00115;CHOTEL01;devis;Remplacement robot + projecteurs terrasse bassin;2026-05-28;2026-07-27;SENT;Demande un délai de réflexion jusqu'à fin juin
DE00117;CLEROY01;devis;Rénovation local technique : pompe + filtre D400;2026-06-03;2026-08-02;SENT;
DE00118;CMARTI01;devis;Extension filtration pataugeoire + skimmers;2026-06-20;2026-08-19;SENT;Relance téléphonique du 05/07 restée sans réponse
DE00120;CROSSI01;devis;Bâche à bulles 500 microns 10x4,5;2026-06-26;2026-08-25;SENT;
DE00121;CMAIRI01;devis;Remplacement vannes + tubes réseau hydraulique;2026-06-05;2026-09-03;SENT;Passage en commission prévu le 15/09
DE00122;CBLANC01;devis;Électrolyseur eXO iQ 18 piscine 8x4;2026-07-01;2026-07-31;SENT;
DE00123;CPISCI01;devis;Lot tubes PVC pression chantier Villeneuve;2026-07-06;2026-08-05;SENT;
DE00124;CRESID01;devis;Coffret filtration + horloge + transfo;2026-07-08;2026-08-07;DRAFT;
DE00125;CDURAN01;devis;Entretien estival : sable + buses;2026-07-10;2026-08-09;DRAFT;
```

`document_lignes_mock.csv` (refs = `sageRef` réels du catalogue) :
```csv
numero;sage_ref;quantite
DE00092;PMP-HAY-SP075;1
DE00092;VNE-PVC-D50;2
DE00092;TUB-PVC-D50;4
DE00095;PMP-PEN-U220;1
DE00095;FLT-AST-D750;1
DE00095;VNE-AST-6V20;1
DE00095;TUB-PVC-D90;10
DE00097;ELC-ZOD-EXO;1
DE00097;REG-ZOD-PH;1
DE00099;BCH-SOL-500;50
DE00099;CFR-CCE-P;1
DE00101;SBL-SIL-25;4
DE00101;VNE-AST-6V15;1
DE00103;PMP-PEN-U220;2
DE00103;FLT-AST-D750;2
DE00103;VNE-AST-6V20;2
DE00103;TUB-PVC-D90;16
DE00105;PRJ-SEA-LED;2
DE00105;CFR-CCE-P;1
DE00106;SKM-HAY-SL;6
DE00106;BSE-HAY-RF;12
DE00106;TUB-PVC-D50;20
DE00106;VNE-PVC-D50;6
DE00108;PMP-DAB-E150;1
DE00108;FLT-AST-D600;1
DE00108;VNE-AST-6V20;1
DE00110;RBT-ZOD-CNX;1
DE00110;BCH-SOL-500;32
DE00111;VRF-VID-20;4
DE00111;VNE-AST-6V15;1
DE00113;ELC-ZOD-EXO;1
DE00113;REG-ZOD-PH;1
DE00114;PMP-HAY-SP050;1
DE00114;FLT-AST-D500;1
DE00114;SKM-AST-BE;2
DE00114;BSE-AST-RF;4
DE00114;TUB-PVC-D63;8
DE00114;VNE-PVC-D63;3
DE00115;RBT-ZOD-CNX;1
DE00115;PRJ-SEA-LED;4
DE00117;PMP-ESP-S025;1
DE00117;FLT-AST-D400;1
DE00117;VNE-PVC-D50;2
DE00117;TUB-PVC-D50;6
DE00118;PMP-HAY-SP033;1
DE00118;FLT-AST-D400;1
DE00118;SKM-AST-BE;2
DE00118;BSE-AST-RF;2
DE00118;TUB-PVC-D63;6
DE00120;BCH-SOL-500;45
DE00121;VNE-AST-6V20;2
DE00121;VNE-PVC-D63;8
DE00121;TUB-PVC-D75;12
DE00121;TUB-PVC-D90;8
DE00122;ELC-ZOD-EXO;1
DE00123;TUB-PVC-D50;30
DE00123;TUB-PVC-D63;20
DE00123;TUB-PVC-D75;10
DE00124;CFR-CCE-P;2
DE00124;PRJ-SEA-LED;2
DE00125;SBL-SIL-25;6
DE00125;BSE-HAY-RF;2
```

**Step 2 : tests d'abord** (`agent/tests/conftest.py` ajoute `agent/` au `sys.path` ; fixture `seeded_db(tmp_path, monkeypatch)` qui patch `db.DB_PATH` puis `seed_db.seed()`). Cas : 13 clients ; recherche "martinets" → CMARTI01 ; recherche "elodie" trouve Élodie (accents) ; CNAVAR01 → nb_documents 0 et liste vide ; DE00118 statut SENT avec 5 lignes prix > 0 ; `montant_ht == Σ quantite×prix` (±0,01) ; periode "3m" exclut DE00111 ; `get_document` porte `client_id` ; refus seed si ref inconnue du catalogue (ValueError). Lancer : `pytest agent/tests -q` → FAIL (modules absents).

**Step 3 : implémentation** `db.py` (SCHEMA du spec §Schéma, `connect`, requêtes ci-dessus, fold accents copié de `catalog._fold`) + `seed_db.py` (schéma, insert clients, documents avec résolution `client_code→id`, lignes avec résolution `numero→document_id` + lookup catalogue, `UPDATE documents SET montant_ht=…`, `argparse --force`).

**Step 4 : vérifier** `pytest agent/tests -q` → PASS ; `python agent/seed_db.py --force && sqlite3 agent/data/maria.db "SELECT COUNT(*) FROM documents"` → 22.

### Task 2: Endpoints GET clients/documents

**Files:** Modify: `agent/app.py` · Test: `agent/tests/test_api.py`

**Interfaces (Produces):**
- `GET /api/clients?q=` → JSON list (clés de `db.search_clients`)
- `GET /api/clients/{id}/documents?periode=` → JSON list (docs + lignes) ; 404 si client inconnu
- `db.ensure_db()` appelé dans `lifespan`

**Steps:** test d'abord (TestClient : 13 clients ; `?q=martinets` → 1 ; documents CMARTI01 → DE00118 présent avec lignes ; periode=3m filtre ; 404 client 999) → FAIL → implémentation (import `db`, 2 routes sync, `ensure_db()` en lifespan) → PASS. L'app démarre toujours : `uvicorn` boot + `curl /api/clients` manuel.

### Task 3: /api/chat structuré (IDs → contexte serveur)

**Files:** Modify: `agent/app.py`, `agent/prompts.py`, `agent/catalog.py` · Test: `agent/tests/test_api.py`, `agent/tests/test_prompts.py`

**Interfaces:**
- Consumes: `db.get_client`, `db.get_document`
- Produces:
  - `ChatRequest` : `message: str = ""` (max 8000), `client_id: int | None`, `document_id: int | None`
  - Validation 422 (detail français) : mail_libre sans message ; reponse_client sans client_id ou sans message ; relance_devis sans client_id/document_id ; document n'appartenant pas au client ; IDs inconnus
  - `catalog.by_refs(refs: list[str]) -> list[dict]` (ordre du devis conservé)
  - `prompts.build_messages(task_id, user_message, history, catalog_rows, client: dict | None = None, document: dict | None = None)` — blocs `<client>` et `<devis>` (dates JJ/MM/AAAA, montants `1 845,00 € HT`, statuts en clair : SENT→« envoyé, sans réponse à ce jour », DRAFT→« brouillon, non envoyé », EXPIRED→« expiré sans réponse »…, notes internes si présentes)
  - `message` vide en relance → message par défaut « Rédige la relance pour le devis ci-dessus. »
  - Instructions `relance_devis`/`reponse_client` réécrites pour référencer `<devis>`/`<client>` ; garde-fous conservés
  - SSE `meta.catalog_refs` = refs des lignes du devis si sélectionné, sinon recherche lexicale actuelle

**Steps:** tests d'abord (422 par cas ; `build_messages` : le premier message user contient `DE00118`, `Camping Les Martinets`, `1 pouce`-non, plutôt montant formaté et date `20/06/2026` ; mail_libre inchangé sans blocs) → FAIL → implémentation → PASS. Rétro-compat vérifiée : POST `{task:"mail_libre", message:"…"}` se comporte comme avant.

### Task 4: UI cascade de sélection (index.html)

**Files:** Modify: `agent/static/index.html`

**Interfaces (Consumes):** endpoints Task 2/3.

Structure panneau gauche (cascade, disclosure progressive) :
```
1 · TÂCHE      3 cartes .task actuelles (inchangé)
2 · CLIENT     search bar §7.14 (debounce 200 ms → /api/clients?q=)
               liste .pick-row : code mono · nom · ville · point type
               sélection → ligne compacte verte ✓ + bouton « Changer »
3 · DEVIS      segmented §7.9 : 3 mois / 6 mois / 12 mois / Tous
               liste .pick-row : numero mono · objet · date JJ/MM · chip statut §7.6 · montant .num
               sélection → lignes du devis dépliées (mini-table refs mono)
               reponse_client : mention « optionnel » + bouton ghost « Aucun devis concerné »
TEXTAREA       reponse_client : « Collez le message reçu du client » · mail_libre : placeholder actuel · relance : masqué
RÉCAP          carte brand-wash : client · devis · nb refs · montant — « Contexte transmis à l'agent »
[Générer]      activé selon règles de validation Task 3
```
- `mail_libre` : étapes 2–3 masquées (comportement actuel intact).
- Statut `EXPIRED` : chip neutre (`fg-3` / fond `bg-elevated`), ambre réservé à DRAFT.
- Empty state devis (CNAVAR01) : « Aucun devis pour ce client » + action selon tâche.
- POST non-200 : lire `detail` JSON → bandeau `.error` (plus de « HTTP 422 » brut).
- « Nouveau » : vide brouillon + historique, **conserve** la sélection client/devis (itération sur le même dossier) ; « Changer » client vide la sélection devis.
- Chips refs du panneau droit : alimentées par `meta.catalog_refs` (inchangé).
- Ctrl+Entrée conservé ; focus ring aqua partout ; `prefers-reduced-motion` déjà géré.

**Steps:** implémenter CSS (`.pick-row`, `.pick-row.sel`, `.status-chip` × 5, `.segmented`, `.recap`, `.step[hidden]`) puis JS (état `sel = {client, document}` ; `searchClients()`, `renderClients()`, `selectClient()`, `loadDocuments()`, `renderDocuments()`, `selectDocument()`, `updateRecap()`, `updateGenerateState()` ; `generate()` envoie `{task, message, client_id, document_id, history}`). Vérifier : serveur lancé, parcours complet au navigateur ou à défaut `curl` des endpoints + contrôle du HTML/JS (`node --check` sur le script extrait si node dispo) ; les 3 tâches génèrent (si Hermes/Ollama up).

### Task 5: Docs + seed dans les scripts

**Files:** Modify: `README.md`, `DEPLOY_MARIA.md`, `ROADMAP.md`, `scripts/install_dev.sh`

- README : architecture (SQLite + sélection), tableau structure (+`db.py`, `seed_db.py`, CSV mock, `maria.db` gitignorée), démarrage (seed auto au boot, `python agent/seed_db.py --force` pour régénérer), limites (« clients/devis mock »).
- DEPLOY_MARIA : étape seed (auto au premier démarrage ; `--force` après mise à jour des CSV), note « aucune dépendance système nouvelle : sqlite3 stdlib ».
- ROADMAP §1/§2 : l'importeur CSV→SQLite existe (`seed_db.py`) ; le palier export Sage = remplacer les CSV mock par les exports réels.
- `install_dev.sh` : seed après install des deps (idempotent).

**Verify final :** `pytest agent/tests -q` ; boot uvicorn ; parcours UI complet ; relance DE00118 générée de bout en bout si moteur up.
