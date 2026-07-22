# Agent devis piscine — design

Date : 2026-07-22 Statut : validé (brainstorming avec l'utilisateur, choix actés
ci-dessous)

## 1. Contexte & objectif

La démo mails a validé le prototype auprès d'ETS Maria. Le vrai besoin est la
**création de devis d'installation de filtration** (pompe + filtre + éléments
nécessaires à une installation complète). L'agent doit, depuis Open WebUI :

- dialoguer avec le commercial, poser une question si une info bloquante manque
  ;
- dimensionner l'installation depuis une logique métier fournie en contexte ;
- produire un devis texte brut suivant un template, sans jamais inventer
  référence, prix, stock ou délai.

La logique de dimensionnement « de Maria » existe déjà sous forme approchée : le
moteur hydraulique du prototype Peep
(`../Peep/backend/src/services/
hydraulicEngine.ts`, fonction pure
`runHydraulicEngine`). Cette logique est **provisoire** : Maria la corrigera
plus tard. Le design doit rendre la régénération triviale après correction.

Les mails restent une capacité secondaire (skill `mails-commerciaux` inchangé).

## 2. Décisions actées

| Sujet              | Décision                                                                                                      |
| ------------------ | ------------------------------------------------------------------------------------------------------------- |
| Template devis     | Modèle simple créé maintenant, remplacé plus tard par un vrai devis Maria                                     |
| Logique            | Hybride : skill (procédure) + abaque dans le RAG (données)                                                    |
| Source de l'abaque | Généré depuis le moteur Peep (option « abaque »), pas de service Peep à l'exécution                           |
| Périmètre pack     | Matériel complet ; main d'œuvre toujours en `[À COMPLÉTER : forfait pose]`                                    |
| Info bloquante     | Volume seul (ou dimensions pour le calculer). Le reste → `[À COMPLÉTER]`                                      |
| Éval               | 2 cas devis ajoutés à eval.sh                                                                                 |
| Stratégie produit  | Décision logiciel/centralisation (Peep UI, PDF, statuts) reportée après validation Maria. Hors périmètre ici. |

## 3. Architecture

Flux inchangé côté infra — aucun invariant sécurité touché :

```
employé :3000 → open-webui (RAG : abaque + catalogue + fiches)
             → hermes:8642 (SOUL + skills devis-piscine / mails-commerciaux)
             → api.mistral.ai (via egress-proxy)
```

- Toolset `api_server` reste `[]`. L'agent n'appelle jamais Peep : le moteur est
  exécuté **une fois, hors production**, par un script générateur.
- Répartition des rôles : le moteur calcule (déterminisme), l'agent dialogue et
  rédige (langage). Le LLM ne fait aucune arithmétique de dimensionnement ni de
  totaux : il recopie l'abaque.

## 4. Composants

### 4.1 Skill `hermes/skills/devis-piscine/SKILL.md` (nouveau)

Frontmatter Hermes identique au skill mails (name, description, tags : devis,
piscine, filtration, dimensionnement, chiffrage).

Procédure imposée :

1. **Volume.** Chercher le volume dans la demande. Absent mais dimensions
   présentes → volume = longueur × largeur × profondeur moyenne, arrondi au m³
   supérieur (seul calcul autorisé ; formes rondes/ovales ou doute → demander le
   volume). Ni volume ni dimensions → poser UNE question (volume ou L × l ×
   profondeur moyenne) et n'émettre aucun devis.
2. **Tranche.** Sélectionner dans l'abaque fourni en contexte la tranche
   contenant le volume. Abaque absent du contexte → squelette de devis avec
   `[À COMPLÉTER : dimensionnement à valider avec l'atelier]` sur chaque ligne
   matériel — jamais de référence ou prix de mémoire.
3. **Cas hors abaque.** Volume > 100 m³, usage public/collectif, spa,
   débordement, nage à contre-courant → pas de devis chiffré : réponse courte
   orientant vers une étude atelier, matériel en `[À COMPLÉTER]`.
4. **Devis.** Remplir le template (§5) en recopiant la tranche : références,
   désignations, quantités, prix unitaires, totaux pré-calculés. Aucune ligne
   hors abaque/catalogue fournis. Main d'œuvre : toujours la ligne
   `[À COMPLÉTER : forfait pose]`. Tuyauterie : citer les diamètres de l'abaque,
   métrage en `[À COMPLÉTER : métrage selon implantation]`.
5. **Données client.** Nom/adresse repris de la demande ou du contexte CRM ;
   absents → `[À COMPLÉTER]`. Jamais bloquant.

Rappels transverses (répétés du SOUL) : texte brut, vouvoiement, anti-invention
absolue, signature maison fixe.

### 4.2 Générateur `tools/gen-abaque.ts` (nouveau)

Script one-shot exécuté sur le poste de dev
(`npx tsx tools/gen-abaque.ts >
data/abaque-filtration.md`). Jamais déployé,
jamais dans l'image Docker.

- Importe `runHydraulicEngine` et ses types depuis
  `../Peep/backend/src/services/hydraulicEngine.ts` (chemin relatif, dépôts
  frères).
- **Paramètres de calcul** : objet `CalcParams` unique en tête de script
  (résidentiel : filteringTime 6, hmt 8, pumpEfficiency 0.6, m3PerSkimmer 25,
  filteringSpeed 30, sandPerM2 300, flowMultiplier 1, spa/NCC 0 — alignés sur
  les défauts Peep). C'est LE point d'édition quand Maria corrige.
- **Grille** : 9 tranches — « jusqu'à 20 m³ » puis 21 → 100 m³ par pas de 10 ;
  le moteur est exécuté sur la borne haute de chaque tranche (via `FREEFORM`
  avec `surfaceArea = volume cible` et profondeurs 1/1 → profondeur moyenne 1,
  donc volume = surface — le moteur ne prend pas le volume en entrée directe).
  Type SKIMMER, usage RESIDENTIAL, options toutes à false.
- **Table catalogue interne au script** (réf, désignation, prix vente HT,
  capacité) alignée sur `data/catalogue-sage100.csv` — source des lignes et des
  prix de l'abaque. Divergence CSV ↔ script possible : assumée (données mock),
  notée en commentaire du script.
- **Mapping sorties moteur → références** :
  - Pompe : choisie **par débit** — plus petite pompe dont le débit catalogue ≥
    `adjustedFlowRate` (POMP-075 12 m³/h, POMP-100 15, POMP-150 21, POMP-200
    28). Au-delà → tranche marquée étude atelier. Le kW moteur (`pumpPower`)
    n'apparaît PAS dans l'abaque : la formule Peep sous-estime d'un facteur ~10
    (ρg absent : `(Q×HMT)/(3600×η)` au lieu de `(ρ·g·Q·H)/η`) et écraserait tout
    à 0,25 kW. Point à faire valider par Maria, listé en tête d'abaque. Le
    moteur n'est pas modifié.
  - Filtre : choisi **par débit** lui aussi — plus petit filtre dont le débit
    catalogue ≥ `adjustedFlowRate` (FILT-400 6 m³/h, FILT-500 10, FILT-600 14) ;
    au-delà → étude atelier. Le Ø calculé (`filterDiameter`) est cité en note de
    tranche mais ne pilote pas le choix : à 30 m/h il dépasse Ø600 dès 60 m³ et
    viderait 5 tranches sur 9 — incohérence Ø calculé ↔ réf choisie visible dans
    l'abaque, à arbitrer par Maria.
  - Sable : `sand` (kg) → sacs SABL-25 arrondis au supérieur.
  - Skimmers → SKIM-STD × n ; refoulements → BUSE-REF × n ; vannes (`valves`) →
    VANN-2V × n ; + 1 VANN-6V n'est PAS ajoutée (incluse dans les filtres
    catalogue) ; accessoires fixes : MANO-FILT ×1, PREF-BASK ×1, UNION-50 ×2,
    COFF-ELEC ×1.
  - Tuyauterie : Ø aspiration/refoulement cités en note de tranche, pas de ligne
    chiffrée (catalogue sans ces Ø ; métrage terrain).
- **Totaux** : total matériel HT, TVA 20 %, TTC calculés par le script et écrits
  dans l'abaque (le LLM recopie).
- `warnings` du moteur → « points de vigilance » de la tranche s'il y en a.

### 4.3 Abaque `data/abaque-filtration.md` (généré, commité)

- En-tête : date de génération, paramètres utilisés, mention « dimensionnement
  provisoire — logique et paramètres à valider par ETS Maria (dont formule
  puissance pompe) », consigne d'usage (une tranche = une installation complète,
  recopier telle quelle).
- Une section `##` par tranche (= 1 chunk RAG autonome) : intitulé « Bassin 31 à
  40 m³ », lignes matériel `réf | désignation | qté | PU HT |
  total HT`,
  totaux, Ø tuyauterie, points de vigilance.
- Fichier uploadé manuellement dans la collection « Knowledge » (comme le reste
  de `data/`). Jamais le CSV brut (règle top-k existante).

### 4.4 `data/catalogue.md` (édité)

Ajouter les références citées par l'abaque et absentes aujourd'hui, prix du CSV,
notes techniques avec capacité : POMP-075 (290,00 — 12 m³/h), FILT-400 (240,00 —
6 m³/h), VANN-2V (48,00), UNION-50 (9,00), MANO-FILT (24,00), PREF-BASK (19,00).
Cohérence catalogue ↔ abaque : toute réf de l'abaque existe au catalogue.

### 4.5 `hermes/SOUL.md` (édité)

Section « Tâches » réécrite : le **devis d'installation filtration** devient la
tâche n° 1 (résumé de la procédure §4.1 : volume bloquant, abaque du contexte,
template, hors-cas → étude atelier), les brouillons de mails passent en n° 2
(contenu inchangé). Règles absolues, coordonnées, signature : inchangées. Le
template vit dans le skill (source unique) ; SOUL y renvoie.

### 4.6 `eval.sh` (édité — 2 cas ajoutés, style grep existant)

- **Cas 3 — devis sans volume** : « Fais-moi un devis filtration pour la piscine
  de M. Martin. » Attendu : demande le volume ou les dimensions
  (`grep -qiE 'volume|dimension'`), zéro référence (`POMP-|FILT-|VANN-`), zéro
  prix `€`.
- **Cas 4 — devis sans contexte** : « Devis filtration complète pour un bassin
  de 45 m³, client Mme Blanc. » (eval.sh court-circuite le RAG → aucun abaque
  injecté.) Attendu : `[À COMPLÉTER]` présent, zéro prix `€`, zéro référence
  catalogue — le squelette sans invention. Les réfs mock n'existant pas dans le
  monde réel, toute réf citée = invention détectable.

### 4.7 Docs (édités, léger)

README : section démo devis (exemples de requêtes, rappel upload
`abaque-filtration.md` + `catalogue.md` ré-uploadé dans Knowledge). CLAUDE.md :
description du dépôt (devis primaire, mails secondaire), mention du cycle de
régénération d'abaque.

## 5. Template devis (dans le skill, texte brut)

```
DEVIS N° [À COMPLÉTER : numéro]
Date : <date du jour si connue, sinon [À COMPLÉTER]>

ETS Maria — pisciniste depuis 1937
28 avenue de la Californie, 06200 Nice — 04 93 86 81 75 — contact@etsmaria.fr

Client : <nom ou [À COMPLÉTER : client]>
Objet : Installation filtration — bassin <volume> m³

Matériel :
<réf> | <désignation> | <qté> | <PU HT> | <total HT>
… (lignes de la tranche abaque, telles quelles)

Tuyauterie aspiration Ø<xx> / refoulement Ø<xx> :
[À COMPLÉTER : métrage selon implantation]
Main d'œuvre pose : [À COMPLÉTER : forfait pose]

Total matériel HT : <total abaque>
TVA 20 % : <montant abaque>
Total TTC (hors main d'œuvre et tuyauterie) : <montant abaque>

Validité du devis : [À COMPLÉTER]
Délai d'intervention : [À COMPLÉTER : à valider avec l'atelier]

Cordialement,
L'équipe ETS Maria
28 avenue de la Californie, 06200 Nice
04 93 86 81 75 — contact@etsmaria.fr
```

Aucun Markdown dans la sortie agent (règle SOUL n° 3, les `|` sont du texte brut
aligné, pas un tableau).

## 6. Cycle de correction (quand Maria corrige la logique)

1. Corriger le moteur dans Peep et/ou l'objet `CalcParams` de
   `tools/gen-abaque.ts`.
2. `npx tsx tools/gen-abaque.ts > data/abaque-filtration.md`.
3. Ré-uploader l'abaque dans la collection Knowledge (remplacer l'ancien).
4. Skill, SOUL, template : intouchés.

## 7. Hors périmètre

- Vrai template devis Maria (attendu d'elle) ; vraie logique validée.
- Centralisation des devis, statuts, PDF, plan 2D — question « agent seul vs
  Peep UI + agent » à trancher après validation Maria.
- Connecteur Sage 100 réel, prod : `2026-07-20-securite-prod.md`.
- Correction du moteur hydraulique Peep (signalé, pas corrigé ici).

## 8. Critères d'acceptation

- `./eval.sh` : 4 cas verts (2 mails existants + 2 devis).
- Démo Open WebUI (abaque + catalogue uploadés) : « devis pour une piscine 8×4,
  profondeur 1,2 à 1,8 m, M. Durand » → devis complet conforme au template,
  tranche 41–50 m³, prix identiques à l'abaque, MO et tuyauterie en
  `[À COMPLÉTER]`.
- « Fais-moi un devis » sans volume → l'agent pose la question du volume.
- « Piscine à débordement 120 m³ » → orientation étude atelier, zéro chiffre.
- Invariants sécu intacts (compose, proxy, toolset `[]`).

## 9. Révision post-implémentation (2026-07-22, soir)

Deux hypothèses de la spec sont tombées à l'implémentation ; architecture
révisée en conséquence, critères §8 tous validés en bout en bout :

1. **Les SKILL.md ne parlent pas au modèle avec le toolset `[]`** : Hermes
   n'injecte qu'un index (nom + description), le contenu se charge via le tool
   `skill_view` — désactivé ici. Le skill `devis-piscine` reste comme
   source/documentation ; la procédure et le template opérationnels vivent
   dans `hermes/SOUL.md` (comme les règles mails l'ont toujours fait).
2. **Le RAG ne sait pas choisir une tranche** : sélectionner « 48 m³ » dans
   « 41 à 50 » est un test d'intervalle numérique ; l'embedding
   (all-MiniLM-L6-v2, anglais) classe toutes les tranches à distance quasi
   égale. Après trois itérations (chunks soudés ≤ 1 500 chars, énumération des
   volumes couverts, exemples de bassins générés, query generation avec calcul
   de volume — conservés), la décision : **l'abaque voyage dans le SOUL** —
   `setup.sh` concatène `hermes/SOUL.md` + `data/abaque-filtration.md` vers
   `~/.hermes/SOUL.md` (~3 k tokens, coût négligeable, fiabilité totale). Le
   RAG garde catalogue, clients, devis, mails.
3. Réglages persistés dans la DB Open WebUI (priment sur les env) : template
   RAG neutre devis+mails, query generation calculant le volume avant
   retrieval, `chunk_size` 1500.
4. `eval.sh` cas 4 renforcé : « bassin de 45 m³ » doit produire la **recopie
   exacte** de la tranche 41–50 (POMP-075, total 1302.00 €) avec les
   `[À COMPLÉTER]` restants — teste la recopie sans recalcul, plus fort que le
   squelette initialement spécifié.
