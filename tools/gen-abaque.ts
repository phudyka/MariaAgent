// tools/gen-abaque.ts — génération one-shot de l'abaque de dimensionnement.
// Usage : npx tsx tools/gen-abaque.ts > data/abaque-filtration.md
// Jamais déployé, jamais dans l'image Docker : le moteur Peep tourne ici
// (poste dev), pas chez Maria. L'agent ne voit que le markdown généré.
import {
  type CalcParams,
  type PoolInput,
  runHydraulicEngine,
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
  skimmer: {
    ref: "SKIM-STD",
    label: "Skimmer standard grande meurtrière",
    prix: 58,
  },
  buse: { ref: "BUSE-REF", label: "Buse de refoulement orientable", prix: 12 },
  vanne: { ref: "VANN-2V", label: "Vanne d'arrêt 2 voies Ø50", prix: 48 },
  union: { ref: "UNION-50", label: "Raccord union Ø50 à coller", prix: 9 },
  mano: { ref: "MANO-FILT", label: "Manomètre de filtre", prix: 24 },
  panier: { ref: "PREF-BASK", label: "Panier de préfiltre pompe", prix: 19 },
  coffret: {
    ref: "COFF-ELEC",
    label: "Coffret électrique filtration",
    prix: 165,
  },
};

const TRANCHES = [
  { min: 10, max: 20, label: "jusqu'à 20 m³" },
  { min: 21, max: 30, label: "21 à 30 m³" },
  { min: 31, max: 40, label: "31 à 40 m³" },
  { min: 41, max: 50, label: "41 à 50 m³" },
  { min: 51, max: 60, label: "51 à 60 m³" },
  { min: 61, max: 70, label: "61 à 70 m³" },
  { min: 71, max: 80, label: "71 à 80 m³" },
  { min: 81, max: 90, label: "81 à 90 m³" },
  { min: 91, max: 100, label: "91 à 100 m³" },
];

// Énumération explicite des volumes : seul pont lexical fiable entre une
// requête « bassin de 48 m³ » et sa tranche (l'embedding ne sait pas que
// 48 ∈ [41, 50]).
const volumes = (t: { min: number; max: number }) =>
  Array.from({ length: t.max - t.min + 1 }, (_, i) => t.min + i).join(", ");

// Exemples de bassins par tranche : pont lexical pour les requêtes en
// dimensions (« piscine 8 x 4 m prof 1,5 ») que l'embedding ne sait pas
// convertir en volume. Dimensions standard du marché × profondeurs moyennes.
const fr = (n: number) => String(n).replace(".", ",");
const exemples = new Map<number, string[]>();
for (const [L, l] of [
  [5, 3],
  [6, 3],
  [7, 3.5],
  [8, 4],
  [9, 4.5],
  [10, 5],
  [11, 5],
  [12, 6],
] as const) {
  for (const prof of [1.2, 1.5, 1.8] as const) {
    const vol = Math.ceil(L * l * prof);
    const t = TRANCHES.find((tr) => vol >= tr.min && vol <= tr.max);
    if (!t) continue;
    const list = exemples.get(t.max) ?? [];
    if (list.length < 3) {
      list.push(`${fr(L)} × ${fr(l)} m prof. ${fr(prof)} m (${vol} m³)`);
      exemples.set(t.max, list);
    }
  }
}

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

// Chaque tranche est émise comme UN bloc soudé (titre + corps sans ligne vide
// interne, ≤ ~900 caractères) : le text splitter d'Open WebUI (chunk 1000)
// garde ainsi 1 tranche = 1 chunk auto-porteur — un chunk « matériel » sans son
// titre de tranche est inexploitable par le modèle.
const out: string[] = [];
const notes: string[] = [];
out.push(
  "# Abaque filtration — ETS Maria (fichier généré, ne pas éditer à la main)",
  "",
  `Généré le ${GENERATED_ON} depuis le moteur Peep. DIMENSIONNEMENT PROVISOIRE ` +
    "— à faire valider par ETS Maria (voir notes en fin de fichier). Une " +
    "tranche = le matériel complet d'une installation de filtration piscine ; " +
    "recopier lignes et totaux tels quels dans le devis, sans recalculer.",
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
    options: {
      heating: false,
      spa: false,
      counterCurrent: false,
      lighting: false,
    },
  };
  const r = runHydraulicEngine(input, PARAMS);
  if (Math.round(r.volume) !== t.max) {
    throw new Error(`volume moteur ${r.volume} ≠ cible ${t.max}`);
  }

  const pompe = pick(POMPES, r.adjustedFlowRate);
  const filtre = pick(FILTRES, r.adjustedFlowRate);

  const debit = r.adjustedFlowRate.toFixed(1);

  if (!pompe || !filtre) {
    out.push(
      "",
      `## Bassin ${t.label} — installation filtration complète (devis type piscine)\n` +
        `Volume ${t.label}, débit requis ${debit} m³/h : au-delà des filtres à ` +
        "sable du catalogue. Étude atelier obligatoire — aucun chiffrage " +
        "standard. Dans le devis : [À COMPLÉTER : étude atelier].",
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

  // Bloc soudé : titre + corps liés par \n simples (aucune ligne vide interne).
  const ex = exemples.get(t.max);
  const bloc = [
    `## Bassin ${t.label} — installation filtration complète (devis type piscine)`,
    `Volumes couverts : ${volumes(t)} m³.`,
    ...(ex ? [`Exemples de bassins : ${ex.join(" ; ")}.`] : []),
    `Volume ${t.label} — débit ${debit} m³/h — aspiration Ø${r.suctionDiameter} / refoulement Ø${r.pressureDiameter}.`,
    `Matériel tranche ${t.label} (réf | désignation | qté | PU HT € | total HT €) :`,
    ...lignes.map(
      (l) => `- ${l.ref} | ${l.label} | ${l.qte} | ${eur(l.pu)} | ${eur(l.qte * l.pu)}`,
    ),
    `Totaux ${t.label} : matériel HT ${eur(totalHT)} € ; TVA 20 % ${eur(tva)} € ; TTC ${eur(totalHT + tva)} €.`,
  ].join("\n");
  // Limite d'hygiène : une tranche doit rester très en deçà du chunk_size
  // Open WebUI (3500) pour ne jamais être coupée.
  if (bloc.length > 1500) {
    throw new Error(`tranche ${t.label} : ${bloc.length} chars > 1500 (risque de coupe au chunking)`);
  }
  out.push("", bloc);

  notes.push(
    `- ${t.label} : Ø filtre calculé ${r.filterDiameter} mm, sable calculé ` +
      `${r.sand} kg (${sacs} sacs de 25 kg).` +
      (r.warnings?.length ? ` Vigilance : ${r.warnings.join(" ; ")}` : ""),
  );
}

out.push(
  "",
  "## Notes techniques (validation ETS Maria — hors devis)",
  "",
  "Points à valider : formule de puissance pompe (kW écartés, sélection par " +
    "débit catalogue), aucune marge de sécurité sur le débit, vitesse de " +
    `filtration ${PARAMS.filteringSpeed} m/h (le Ø de filtre calculé ci-dessous dépasse les ` +
    `filtres catalogue dès 60 m³), temps de filtration ${PARAMS.filteringTime} h. Main ` +
    "d'œuvre pose et métrage tuyauterie : jamais chiffrés ici, à compléter au " +
    "devis.",
  "",
  ...notes,
);

console.log(out.join("\n"));
