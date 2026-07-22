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
