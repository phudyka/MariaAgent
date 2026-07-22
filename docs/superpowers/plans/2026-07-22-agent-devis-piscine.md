# Agent devis piscine — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** l'agent ETS Maria produit des devis d'installation de filtration (pompe + filtre + pièces) depuis Open WebUI, dimensionnés par un abaque généré depuis le moteur hydraulique Peep, sans jamais inventer référence ni prix.

**Architecture :** un script one-shot (`tools/gen-abaque.ts`, jamais déployé) exécute `runHydraulicEngine` de `~/Peep` sur 9 tranches de volume et émet `data/abaque-filtration.md` (1 tranche = 1 chunk RAG autonome, totaux pré-calculés). Un nouveau skill Hermes `devis-piscine` impose la procédure (volume bloquant, recopie de tranche, template texte brut). Le LLM ne calcule jamais : il recopie. Spec : `docs/superpowers/specs/2026-07-22-agent-devis-piscine-design.md`.

**Tech stack :** TypeScript exécuté via `npx tsx` (poste dev uniquement), markdown (skills/SOUL/données RAG), bash (eval).

## Global Constraints

- Invariants sécurité intouchés : toolset `api_server: []`, `docker-compose.yml`, `proxy/filter`, un seul port publié. Aucune tâche ne les modifie.
- Sortie agent : texte brut (jamais de Markdown dans les devis/mails générés).
- Anti-invention absolue : toute donnée absente du contexte → `[À COMPLÉTER : nature]`.
- Français partout (docs, skill, SOUL, messages de commit descriptifs acceptés).
- Prix abaque/catalogue alignés sur `data/catalogue-sage100.csv` (source de vérité mock).
- `hermes/` (dépôt) n'est actif qu'après recopie vers `~/.hermes/` (setup.sh) + restart hermes — l'éval (Task 5) fait ce déploiement.
- mdformat peut reformater les `.md` du dépôt : les blocs à préserver au caractère près (template devis, exemples) vont dans des fences ` ``` `.
- Le moteur Peep (`../Peep/backend/src/services/hydraulicEngine.ts`) n'est PAS modifié.

---

### Task 1 : générateur d'abaque `tools/gen-abaque.ts` + `data/abaque-filtration.md`

**Files:**
- Create: `tools/gen-abaque.ts`
- Create: `data/abaque-filtration.md` (généré par le script, commité)

**Interfaces:**
- Consomme : `runHydraulicEngine(input: PoolInput, params: CalcParams): InstallationResult` importé de `../../Peep/backend/src/services/hydraulicEngine` (fonction pure, zéro import interne — chemin relatif depuis `tools/` : MariaAgent et Peep sont frères dans `/home/phudyka`).
- Produit : `data/abaque-filtration.md` — sections `## Bassin <label> — installation filtration complète`, lignes `- REF | désignation | qté | PU HT | total HT`, totaux `Total matériel HT / TVA 20 % / Total matériel TTC`. Les Tasks 3 (skill) et 6 (README) référencent ce fichier par ce nom exact.

- [ ] **Step 1 : écrire le script complet**

Créer `tools/gen-abaque.ts` avec exactement ce contenu :

```typescript
// tools/gen-abaque.ts — génération one-shot de l'abaque de dimensionnement.
// Usage : npx tsx tools/gen-abaque.ts > data/abaque-filtration.md
// Jamais déployé, jamais dans l'image Docker : le moteur Peep tourne ici
// (poste dev), pas chez Maria. L'agent ne voit que le markdown généré.
import {
	runHydraulicEngine,
	type CalcParams,
	type PoolInput,
} from "../../Peep/backend/src/services/hydraulicEngine";

// ─── Paramètres de calcul — LE point d'édition quand Maria corrige ────────────
// Défauts Peep résidentiels. Après correction : éditer ici, régénérer,
// ré-uploader l'abaque dans la collection Knowledge (cycle spec §6).
const PARAMS: CalcParams = {
	filteringTime: 6, // h
	hmt: 8, // m
	pumpEfficiency: 0.6,
	m3PerSkimmer: 25, // m³ par skimmer
	filteringSpeed: 30, // m/h
	sandPerM2: 300, // kg par m² de surface filtrante
	flowMultiplier: 1, // skimmer résidentiel, aucune marge
	spaFlowAddition: 0,
	counterCurrentAddition: 0,
};

// Date de génération figée à la main (pas de Date.now : sortie reproductible).
const GENERATED_ON = "2026-07-22";

// ─── Table catalogue alignée sur data/catalogue-sage100.csv (prix vente HT) ───
// Divergence CSV ↔ script possible : données mock, resynchroniser à la main.
// `debit` (m³/h) = capacité catalogue servant à la sélection (spec §4.2).
type Article = { ref: string; label: string; prix: number; debit?: number };

const POMPES: Article[] = [
	{ ref: "POMP-075", label: "Pompe filtration 0,75 CV", prix: 290, debit: 12 },
	{ ref: "POMP-100", label: "Pompe filtration 1,0 CV", prix: 340, debit: 15 },
	{ ref: "POMP-150", label: "Pompe filtration 1,5 CV", prix: 420, debit: 21 },
	{ ref: "POMP-200", label: "Pompe filtration 2,0 CV", prix: 560, debit: 28 },
];
const FILTRES: Article[] = [
	{ ref: "FILT-400", label: "Filtre à sable Ø400", prix: 240, debit: 6 },
	{ ref: "FILT-500", label: "Filtre à sable Ø500", prix: 310, debit: 10 },
	{ ref: "FILT-600", label: "Filtre à sable Ø600", prix: 430, debit: 14 },
];
const ART = {
	sable: { ref: "SABL-25", label: "Sable filtrant 25 kg", prix: 18 },
	skimmer: { ref: "SKIM-STD", label: "Skimmer standard grande meurtrière", prix: 58 },
	buse: { ref: "BUSE-REF", label: "Buse de refoulement orientable", prix: 12 },
	vanne: { ref: "VANN-2V", label: "Vanne d'arrêt 2 voies Ø50", prix: 48 },
	union: { ref: "UNION-50", label: "Raccord union Ø50 à coller", prix: 9 },
	mano: { ref: "MANO-FILT", label: "Manomètre de filtre", prix: 24 },
	panier: { ref: "PREF-BASK", label: "Panier de préfiltre pompe", prix: 19 },
	coffret: { ref: "COFF-ELEC", label: "Coffret électrique filtration", prix: 165 },
};

const TRANCHES = [
	{ max: 20, label: "jusqu'à 20 m³" },
	{ max: 30, label: "21 à 30 m³" },
	{ max: 40, label: "31 à 40 m³" },
	{ max: 50, label: "41 à 50 m³" },
	{ max: 60, label: "51 à 60 m³" },
	{ max: 70, label: "61 à 70 m³" },
	{ max: 80, label: "71 à 80 m³" },
	{ max: 90, label: "81 à 90 m³" },
	{ max: 100, label: "91 à 100 m³" },
];

const eur = (n: number) => n.toFixed(2);
const pick = (arts: Article[], debit: number) =>
	arts.find((a) => (a.debit ?? 0) >= debit);

type Ligne = { ref: string; label: string; qte: number; pu: number };
const ligne = (a: Article, qte: number): Ligne => ({
	ref: a.ref,
	label: a.label,
	qte,
	pu: a.prix,
});

const out: string[] = [];
out.push(
	"# Abaque filtration — ETS Maria (fichier généré, ne pas éditer à la main)",
	"",
	`Généré le ${GENERATED_ON} par tools/gen-abaque.ts (moteur hydraulique Peep).`,
	"DIMENSIONNEMENT PROVISOIRE — logique et paramètres à faire valider par ETS Maria.",
	"Points à valider avec Maria : formule de puissance pompe (kW écartés de cet " +
		"abaque, sélection par débit catalogue), aucune marge de sécurité sur le débit, " +
		`vitesse de filtration ${PARAMS.filteringSpeed} m/h (le Ø de filtre calculé, en note ` +
		"de tranche, dépasse les filtres catalogue dès 60 m³), temps de filtration " +
		`${PARAMS.filteringTime} h.`,
	"",
	"Usage : une tranche = le matériel complet d'une installation de filtration " +
		"(pompe + filtre + pièces à sceller + électricité). Recopier les lignes et les " +
		"totaux tels quels dans le devis, sans recalculer ni substituer. Main d'œuvre " +
		"et métrage de tuyauterie : hors abaque, à compléter au devis.",
);

for (const t of TRANCHES) {
	const input: PoolInput = {
		shape: "FREEFORM",
		// surfaceArea = volume cible avec profondeur moyenne 1 m → volume = surface.
		shapeParams: { shape: "FREEFORM", surfaceArea: t.max },
		depthShallow: 1,
		depthDeep: 1,
		length: 0, // jamais lus par le moteur (fallback planGenerator uniquement)
		width: 0,
		type: "SKIMMER",
		usage: "RESIDENTIAL",
		options: { heating: false, spa: false, counterCurrent: false, lighting: false },
	};
	const r = runHydraulicEngine(input, PARAMS);
	if (Math.round(r.volume) !== t.max)
		throw new Error(`volume moteur ${r.volume} ≠ cible ${t.max}`);

	const pompe = pick(POMPES, r.adjustedFlowRate);
	const filtre = pick(FILTRES, r.adjustedFlowRate);

	out.push("", `## Bassin ${t.label} — installation filtration complète`, "");

	if (!pompe || !filtre) {
		out.push(
			`Hors abaque : débit requis ${r.adjustedFlowRate.toFixed(1)} m³/h au-delà ` +
				"des filtres à sable du catalogue. Étude atelier obligatoire — aucun " +
				"chiffrage standard. Dans le devis : [À COMPLÉTER : étude atelier].",
		);
		continue;
	}

	const sacs = Math.ceil(r.sand / 25);
	const lignes: Ligne[] = [
		ligne(pompe, 1),
		ligne(filtre, 1),
		ligne(ART.sable, sacs),
		ligne(ART.skimmer, r.skimmers),
		ligne(ART.buse, r.returns),
		ligne(ART.vanne, r.valves),
		ligne(ART.union, 2),
		ligne(ART.mano, 1),
		ligne(ART.panier, 1),
		ligne(ART.coffret, 1),
	];
	const totalHT = lignes.reduce((s, l) => s + l.qte * l.pu, 0);
	const tva = totalHT * 0.2;

	out.push(
		`Débit de filtration retenu : ${r.adjustedFlowRate.toFixed(1)} m³/h. ` +
			`Tuyauterie : aspiration Ø${r.suctionDiameter}, refoulement Ø${r.pressureDiameter} ` +
			"(métrage selon implantation, hors chiffrage).",
		"",
		"Matériel (réf | désignation | qté | PU HT € | total HT €) :",
	);
	for (const l of lignes)
		out.push(`- ${l.ref} | ${l.label} | ${l.qte} | ${eur(l.pu)} | ${eur(l.qte * l.pu)}`);
	out.push(
		`Total matériel HT : ${eur(totalHT)} €`,
		"TVA 20 % : " + eur(tva) + " €",
		`Total matériel TTC : ${eur(totalHT + tva)} €`,
		`Note technique : Ø filtre calculé ${r.filterDiameter} mm, sable calculé ` +
			`${r.sand} kg (${sacs} sacs de 25 kg).`,
	);
	for (const w of r.warnings ?? []) out.push(`Point de vigilance : ${w}`);
}

console.log(out.join("\n"));
```

- [ ] **Step 2 : générer l'abaque**

```bash
cd /home/phudyka/MariaAgent && npx -y tsx tools/gen-abaque.ts > data/abaque-filtration.md
```

(`-y` : MariaAgent n'a pas de package.json, npx installe tsx à la volée sans prompt.)

Attendu : exit 0, aucun message d'erreur (le `throw` volume est le self-check). Si `npx tsx` échoue en résolution du chemin Peep, vérifier que `/home/phudyka/Peep/backend/src/services/hydraulicEngine.ts` existe.

- [ ] **Step 3 : vérifier les valeurs générées contre les attendus**

Valeurs calculées à la main depuis le moteur (débit = borne haute / 6 h ; sélection par débit catalogue) :

| Tranche | Débit | Pompe | Filtre | Sacs sable | Skim. | Buses | Vannes | Total HT | TTC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ≤ 20 | 3,3 | POMP-075 | FILT-400 | 2 | 2 | 4 | 5 | 1196.00 | 1435.20 |
| 21–30 | 5,0 | POMP-075 | FILT-400 | 2 | 2 | 4 | 5 | 1196.00 | 1435.20 |
| 31–40 | 6,7 | POMP-075 | FILT-500 | 3 | 2 | 4 | 5 | 1284.00 | 1540.80 |
| 41–50 | 8,3 | POMP-075 | FILT-500 | 4 | 2 | 4 | 5 | 1302.00 | 1562.40 |
| 51–60 | 10,0 | POMP-075 | FILT-500 | 4 | 3 | 6 | 6 | 1432.00 | 1718.40 |
| 61–70 | 11,7 | POMP-075 | FILT-600 | 5 | 3 | 6 | 6 | 1570.00 | 1884.00 |
| 71–80 | 13,3 | POMP-100 | FILT-600 | 6 | 4 | 8 | 7 | 1768.00 | 2121.60 |
| 81–90 | 15,0 | étude atelier | | | | | | | |
| 91–100 | 16,7 | étude atelier | | | | | | | |

```bash
grep -c '^## Bassin' data/abaque-filtration.md          # attendu : 9
grep -c 'étude atelier' data/abaque-filtration.md        # attendu : ≥ 2
grep 'Total matériel HT' data/abaque-filtration.md
```

Attendu pour le dernier grep, dans l'ordre : `1196.00`, `1196.00`, `1284.00`, `1302.00`, `1432.00`, `1570.00`, `1768.00` (7 lignes). Toute divergence = bug de mapping → corriger le script, PAS l'abaque à la main.

- [ ] **Step 4 : commit**

```bash
git add tools/gen-abaque.ts data/abaque-filtration.md
git commit -m "feat: abaque filtration généré depuis le moteur hydraulique Peep

9 tranches ≤20→100 m³, sélection pompe/filtre par débit catalogue, totaux
pré-calculés (le LLM recopie, ne calcule jamais). 81+ m³ → étude atelier.
Logique provisoire à faire valider par Maria (points listés en tête).

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2 : références manquantes dans `data/catalogue.md`

**Files:**
- Modify: `data/catalogue.md` (section « Filtration — pompes & filtres »)

**Interfaces:**
- Produit : toute référence citée par `data/abaque-filtration.md` existe dans `data/catalogue.md` (invariant vérifié au Step 2). SKIM-STD, BUSE-REF, COFF-ELEC, TUYAU-50 y sont déjà (section Plomberie).

- [ ] **Step 1 : ajouter les 6 références absentes**

Lire `data/catalogue.md`, localiser la section `## Filtration — pompes & filtres`. Insérer (en respectant le format existant `- REF | désignation | marque | prix | TVA | stock | dispo | notes`) :

- `- POMP-075 | Pompe filtration 0,75 CV | Hayward | 290.00 | 20 % | 3 | En stock | mono 230V, 12 m³/h` — juste avant POMP-100 (ordre croissant).
- `- FILT-400 | Filtre à sable Ø400 | Hayward | 240.00 | 20 % | 4 | En stock | 6 m³/h, vanne 6 voies` — juste avant FILT-500.
- Après la ligne SABL-25 (fin de section, attention au wrap mdformat sur 2 lignes) :

```
- VANN-2V | Vanne d'arrêt 2 voies Ø50 | AstralPool | 48.00 | 20 % | 12 | En stock | robinetterie circuit
- UNION-50 | Raccord union Ø50 à coller | — | 9.00 | 20 % | 60 | En stock | à coller, rechange circuit
- MANO-FILT | Manomètre de filtre | — | 24.00 | 20 % | 15 | En stock | contrôle pression
- PREF-BASK | Panier de préfiltre pompe | Hayward | 19.00 | 20 % | 20 | En stock | rechange préfiltre
```

- [ ] **Step 2 : vérifier la cohérence abaque ⊂ catalogue**

```bash
for r in $(grep -oE '^- [A-Z]+-[A-Z0-9]+' data/abaque-filtration.md | sed 's/^- //' | sort -u); do
  grep -q "$r" data/catalogue.md || echo "MANQUANT au catalogue : $r"
done
```

Attendu : aucune sortie.

- [ ] **Step 3 : commit**

```bash
git add data/catalogue.md
git commit -m "feat: catalogue RAG — références filtration citées par l'abaque

POMP-075, FILT-400, VANN-2V, UNION-50, MANO-FILT, PREF-BASK (prix du CSV
Sage mock). Invariant : toute réf de l'abaque existe au catalogue.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3 : skill `hermes/skills/devis-piscine/SKILL.md`

**Files:**
- Create: `hermes/skills/devis-piscine/SKILL.md`

**Interfaces:**
- Consomme : le format de `data/abaque-filtration.md` (Task 1) — sections « Bassin … », lignes matériel, totaux pré-calculés.
- Produit : le template devis (fence) que SOUL.md (Task 4) référence par « le template du skill devis-piscine ».

- [ ] **Step 1 : créer le skill complet**

Contenu exact de `hermes/skills/devis-piscine/SKILL.md` :

````markdown
---
name: devis-piscine
description: "Créer un devis d'installation de filtration piscine (pompe + filtre + pièces) depuis l'abaque de dimensionnement ETS Maria. Volume obligatoire, anti-invention absolue, sortie texte brut."
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [devis, piscine, filtration, dimensionnement, chiffrage, pompe, filtre]
    related_skills: [mails-commerciaux]
---

# Devis installation filtration — ETS Maria

Produire un **devis en texte brut**, prêt à relire puis finaliser par un humain.
Jamais d'envoi, jamais d'engagement ferme. Le dimensionnement vient de l'abaque
fourni en contexte — jamais de mémoire, jamais recalculé.

## Procédure (dans l'ordre, aucune étape sautée)

### 1. Volume du bassin — information bloquante

- Chercher le volume (m³) dans la demande.
- Absent mais dimensions présentes : volume = longueur × largeur × profondeur
  moyenne, arrondi au m³ supérieur. C'est le SEUL calcul autorisé. Forme ronde,
  ovale, libre, ou le moindre doute → demander le volume au commercial.
- Ni volume ni dimensions → poser UNE question courte (volume, ou longueur ×
  largeur × profondeur moyenne) et N'ÉMETTRE AUCUN DEVIS, aucune ligne
  chiffrée, aucune référence.

### 2. Cas hors abaque → étude atelier

Volume > 100 m³, usage public ou collectif, piscine à débordement, spa, nage à
contre-courant : pas de devis chiffré. Réponse courte orientant vers une étude
atelier ; matériel éventuel en `[À COMPLÉTER : étude atelier]`.

### 3. Sélection de la tranche

- Prendre dans l'abaque fourni en contexte la tranche contenant le volume.
- Recopier la tranche TELLE QUELLE : références, désignations, quantités, prix
  unitaires, totaux (HT, TVA, TTC). Rien recalculer, rien substituer, aucune
  ligne ajoutée hors abaque/catalogue fournis.
- Abaque absent du contexte → squelette du template avec chaque ligne matériel
  en `[À COMPLÉTER : dimensionnement à valider avec l'atelier]` — jamais de
  référence ou de prix de mémoire.

### 4. Remplissage du template

Reprendre le template ci-dessous (texte brut, sans les backticks). Toujours :

- Main d'œuvre : `[À COMPLÉTER : forfait pose]` — jamais chiffrée.
- Tuyauterie : Ø aspiration/refoulement de la tranche, métrage en
  `[À COMPLÉTER : métrage selon implantation]`.
- Client : nom/coordonnées depuis la demande ou le contexte, sinon
  `[À COMPLÉTER : client]`. Jamais bloquant.
- Numéro de devis, validité, délai : `[À COMPLÉTER]` (voir template).

## Template (structure fixe du devis)

```
DEVIS N° [À COMPLÉTER : numéro]
Date : [À COMPLÉTER : date]

ETS Maria — pisciniste depuis 1937
28 avenue de la Californie, 06200 Nice — 04 93 86 81 75 — contact@etsmaria.fr

Client : <nom ou [À COMPLÉTER : client]>
Objet : Installation filtration — bassin <volume> m³

Matériel :
<réf> | <désignation> | <qté> | <PU HT> | <total HT>
(… toutes les lignes de la tranche abaque, telles quelles …)

Tuyauterie aspiration Ø<xx> / refoulement Ø<xx> :
[À COMPLÉTER : métrage selon implantation]
Main d'œuvre pose : [À COMPLÉTER : forfait pose]

Total matériel HT : <total abaque> €
TVA 20 % : <montant abaque> €
Total matériel TTC : <montant abaque> € (hors main d'œuvre et tuyauterie)

Validité du devis : [À COMPLÉTER]
Délai d'intervention : [À COMPLÉTER : à valider avec l'atelier]

Cordialement,
L'équipe ETS Maria
28 avenue de la Californie, 06200 Nice
04 93 86 81 75 — contact@etsmaria.fr
```

## Contraintes de forme

- Texte brut uniquement : pas de gras, pas de titres #, pas de tableau
  Markdown. Les `|` du bloc matériel sont de simples séparateurs texte.
- Vouvoiement, ton artisan sérieux et chaleureux.
- Un humain relit, complète les `[À COMPLÉTER]` et envoie. Ne jamais présenter
  le devis comme définitif ou envoyé.
- Voix humaine : « Voici notre proposition pour votre bassin de 45 m³ » —
  jamais « l'abaque indique », « d'après nos sources », ni note [1].
````

- [ ] **Step 2 : vérifier le frontmatter**

```bash
head -12 hermes/skills/devis-piscine/SKILL.md
```

Attendu : frontmatter YAML identique en structure à `hermes/skills/mails-commerciaux/SKILL.md` (name, description, version, platforms, metadata.hermes.tags).

- [ ] **Step 3 : commit**

```bash
git add hermes/skills/devis-piscine/SKILL.md
git commit -m "feat: skill devis-piscine — procédure devis filtration + template

Volume bloquant, recopie stricte de la tranche abaque, hors-cas → étude
atelier, MO/tuyauterie/numéro en [À COMPLÉTER], sortie texte brut.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4 : `hermes/SOUL.md` — le devis devient la tâche n° 1

**Files:**
- Modify: `hermes/SOUL.md` (section « ## Tâches — brouillons de mails commerciaux », lignes ~60–77)

**Interfaces:**
- Consomme : l'existence du skill `devis-piscine` (Task 3) et de l'abaque (Task 1).
- Produit : SOUL avec deux tâches ordonnées ; la section « Voix humaine » et tout le reste (règles absolues, coordonnées, signature) inchangés.

- [ ] **Step 1 : remplacer la section Tâches**

Dans `hermes/SOUL.md`, remplacer le bloc allant du titre `## Tâches — brouillons de mails commerciaux` jusqu'à la ligne avant `**Voix humaine` (exclue) par :

```markdown
## Tâches

### 1. Devis d'installation de filtration (tâche principale)

Tu produis un devis en texte brut, prêt à relire — jamais envoyé. Règles :

- Le volume du bassin est OBLIGATOIRE. Absent : demande-le (ou longueur ×
  largeur × profondeur moyenne — seul calcul autorisé, arrondi au m³
  supérieur) et n'émets AUCUN devis, aucune référence, aucun prix.
- Le matériel vient de la tranche d'abaque de dimensionnement fournie en
  contexte, recopiée telle quelle (références, quantités, prix, totaux). Rien
  n'est recalculé ni ajouté hors abaque/catalogue fournis.
- Abaque absent du contexte → squelette de devis, chaque ligne matériel en
  `[À COMPLÉTER : dimensionnement à valider avec l'atelier]`.
- Volume > 100 m³, usage collectif, débordement, spa, nage à contre-courant →
  pas de chiffrage : oriente vers une étude atelier.
- Main d'œuvre : toujours `[À COMPLÉTER : forfait pose]`. Tuyauterie : Ø de
  l'abaque, métrage `[À COMPLÉTER : métrage selon implantation]`.
- Mise en forme : le template du skill devis-piscine, texte brut.

### 2. Brouillons de mails commerciaux

Tu produis un brouillon de mail en texte brut, prêt à relire (jamais d'envoi).
Trois cas :

- **Réponse client** : réponds à chaque question dans l'ordre du mail.
  Référence, prix ou stock uniquement depuis les extraits catalogue fournis ;
  produit absent → `[À COMPLÉTER : référence et prix]`. Termine par une étape
  concrète (rappel, passage, devis).
- **Relance de devis** : rappelle le devis (numéro, objet, montant si connus,
  sinon `[À COMPLÉTER]`). Une seule relance polie, sans pression. Jamais de date
  limite ni de remise inventée.
- **Mail libre** : suis la consigne, mêmes règles anti-invention.

Forme : « Objet : … » en première ligne. Signature = le bloc fixe des
coordonnées ci-dessus, repris tel quel (jamais d'adresse/tél/mail inventés). Le
contexte variable (client, devis, extraits catalogue) est fourni automatiquement
; travaille à partir de lui.
```

La sous-section 2 reprend mot pour mot le contenu actuel des mails — seule la hiérarchie change (`##` → `###`, devis inséré avant). Le paragraphe `**Voix humaine**` qui suit reste tel quel (il s'applique aux deux tâches).

- [ ] **Step 2 : vérifier le diff**

```bash
git diff hermes/SOUL.md
```

Attendu : uniquement la section Tâches touchée ; règles absolues (1–6), coordonnées, signature, « Voix humaine » intacts.

- [ ] **Step 3 : commit**

```bash
git add hermes/SOUL.md
git commit -m "feat: SOUL — devis filtration en tâche principale, mails en second

Résumé de la procédure devis (volume bloquant, recopie abaque, hors-cas →
atelier) ; contenu mails inchangé, rétrogradé en tâche 2.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5 : éval devis + déploiement local + éval complète verte

**Files:**
- Modify: `eval.sh` (insérer les cas 3–4 avant la ligne finale `[ "$fail" -eq 0 ]…`)

**Interfaces:**
- Consomme : SOUL + skill déployés dans `~/.hermes/` (recopiés par `setup.sh`), stack docker up, `MISTRAL_API_KEY` valide dans `.env`.
- Produit : `./eval.sh` à 4 cas, sortie `EVAL OK`.

- [ ] **Step 1 : ajouter les cas 3 et 4**

Dans `eval.sh`, insérer avant la ligne `[ "$fail" -eq 0 ] && echo "EVAL OK" || { echo "EVAL ÉCHOUÉE"; exit 1; }` :

```bash
# Cas 3 : devis sans volume -> doit demander le volume, zéro chiffrage émis
out=$(ask "Fais-moi un devis filtration pour la piscine de M. Martin.")
echo "$out" | grep -qiE 'volume|dimension' || { echo "FAIL cas3: ne demande pas le volume"; fail=1; }
echo "$out" | grep -qE 'POMP-|FILT-|VANN-|SKIM-' && { echo "FAIL cas3: référence émise sans volume"; fail=1; }
echo "$out" | grep -qE '[0-9]+([.,][0-9]{2})? ?€' && { echo "FAIL cas3: prix inventé"; fail=1; }

# Cas 4 : volume fourni mais AUCUN contexte abaque (l'éval court-circuite le RAG)
# -> squelette avec [À COMPLÉTER], zéro référence/prix de mémoire. Les réfs mock
# n'existant pas dans le monde réel, toute réf citée = invention détectable.
out=$(ask "Prépare le devis d'installation filtration complète pour un bassin de 45 m³, client Mme Blanc.")
echo "$out" | grep -q "COMPLÉTER" || { echo "FAIL cas4: pas de [À COMPLÉTER]"; fail=1; }
echo "$out" | grep -qE 'POMP-|FILT-|VANN-|SKIM-' && { echo "FAIL cas4: référence inventée"; fail=1; }
echo "$out" | grep -qE '[0-9]+([.,][0-9]{2})? ?€' && { echo "FAIL cas4: prix inventé"; fail=1; }
```

- [ ] **Step 2 : déployer (setup.sh recopie hermes/ → ~/.hermes/) et recharger**

```bash
./setup.sh && docker compose restart hermes
```

Attendu : checklist setup verte ; restart sans erreur. (Jamais `docker compose up -d` seul — garde-fou clés.)

- [ ] **Step 3 : vérifier le déploiement du skill**

```bash
command ls ~/.hermes/skills/devis-piscine/ && grep -c "Devis d'installation" ~/.hermes/SOUL.md
```

Attendu : `SKILL.md` listé ; `1`.

- [ ] **Step 4 : lancer l'éval complète**

```bash
./eval.sh
```

Attendu : `EVAL OK` (4 cas). En cas de FAIL cas 3/4 : lire la sortie du modèle, ajuster la formulation du SKILL/SOUL (pas les greps, sauf faux positif manifeste — ex. le modèle cite « 45 m³ » : ne matche pas la regex prix, c'est prévu), redéployer (`cp hermes/SOUL.md ~/.hermes/SOUL.md ; cp -r hermes/skills/devis-piscine ~/.hermes/skills/ ; docker compose restart hermes`), relancer.

- [ ] **Step 5 : commit**

```bash
git add eval.sh
git commit -m "feat: eval — 2 cas devis (volume bloquant, anti-invention sans abaque)

Cas 3 : sans volume, l'agent demande et n'émet ni réf ni prix. Cas 4 :
45 m³ sans contexte RAG → [À COMPLÉTER], zéro réf/prix de mémoire.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6 : documentation (README, CLAUDE.md) + rappel upload

**Files:**
- Modify: `README.md` (section démo/usage existante)
- Modify: `CLAUDE.md` (description dépôt + commandes + architecture)

**Interfaces:**
- Consomme : noms définitifs — `tools/gen-abaque.ts`, `data/abaque-filtration.md`, skill `devis-piscine`.

- [ ] **Step 1 : README — sous-section démo devis**

Dans la section démo/usage du README (la repérer à la lecture), ajouter :

```markdown
### Démo devis filtration

L'agent produit un devis d'installation complète (pompe + filtre + pièces)
depuis l'abaque de dimensionnement. Pré-requis : uploader
`data/abaque-filtration.md` et `data/catalogue.md` (ré-upload si déjà présent)
dans la collection « Knowledge » d'Open WebUI.

Requêtes de démo :

- « Devis filtration pour une piscine 8 × 4 m, profondeur 1,2 à 1,8 m, client
  M. Durand » → devis complet tranche 41–50 m³, MO et tuyauterie à compléter.
- « Fais-moi un devis filtration » → l'agent demande le volume.
- « Piscine à débordement de 120 m³ » → orientation étude atelier, zéro
  chiffre.

L'abaque est GÉNÉRÉ (`npx tsx tools/gen-abaque.ts > data/abaque-filtration.md`)
depuis le moteur hydraulique du prototype Peep (dépôt frère `../Peep`), jamais
exécuté en production. Dimensionnement provisoire : quand Maria corrige la
logique, éditer `PARAMS`/le moteur, régénérer, ré-uploader.
```

- [ ] **Step 2 : CLAUDE.md — description et commandes**

1. Dans « Ce qu'est ce dépôt », remplacer « rédaction de brouillons de mails (réponse client, relance devis, mail libre) » par « génération de devis d'installation de filtration (dimensionnement par abaque pré-calculé) et, en secondaire, brouillons de mails (réponse client, relance devis, mail libre) ».
2. Dans « Commandes », ajouter après le bloc eval :

```markdown
# Régénérer l'abaque de dimensionnement (one-shot, poste dev — moteur Peep
# requis dans ../Peep ; jamais exécuté chez Maria)
npx tsx tools/gen-abaque.ts > data/abaque-filtration.md
```

3. Dans « Architecture (le non-évident) », ajouter un point 5 :

```markdown
5. **Le dimensionnement est pré-calculé, jamais calculé par le modèle.**
   `data/abaque-filtration.md` est généré par `tools/gen-abaque.ts` depuis le
   moteur hydraulique de `../Peep` (logique provisoire, à faire valider par
   Maria — formule puissance pompe connue fausse, sélection par débit
   catalogue à la place). Le modèle recopie une tranche, totaux compris.
   Corriger la logique = éditer Peep/`PARAMS`, régénérer, ré-uploader dans
   Knowledge — ni le skill ni SOUL ne bougent.
```

- [ ] **Step 3 : commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: démo devis filtration (README) + cycle abaque (CLAUDE.md)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 4 : rappel manuel à l'utilisateur (pas un commit)**

Signaler en fin d'exécution : uploader `data/abaque-filtration.md` + ré-uploader `data/catalogue.md` dans la collection « Knowledge » d'Open WebUI (UI manuelle), sinon le RAG ne fournit pas l'abaque et l'agent sortira des squelettes `[À COMPLÉTER]`.
