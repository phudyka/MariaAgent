# Design System — Peep by ETS Maria
> SaaS interne de devis hydraulique piscine · Dark mode natif · **Version 3.0**

Ce document est la **source de vérité visuelle** de Peep. Il est dérivé directement
du logo (grenouille bleu→vert, dégradé « eau », courbe chartreuse) et calibré pour
l'app réelle : React 18 · TailwindCSS · HeroUI · Framer Motion · Lucide.

---

## 1. Philosophie

Peep outille les commerciaux d'ETS Maria (**depuis 1937**) sur un travail technique :
dimensionner une piscine et bâtir un devis fiable en quelques secondes. L'interface
doit incarner **trois qualités**, dans cet ordre :

1. **Confiance technique** — la donnée chiffrée est le héros. Lisibilité, alignement,
   tabulaire. Rien ne « flotte », rien n'est décoratif sans raison.
2. **Calme opérationnel** — dark mode profond, surfaces sobres, contrastes maîtrisés.
   Un commercial passe des heures dessus : zéro fatigue, zéro bruit visuel.
3. **Signature de marque** — la couleur n'arrive jamais par hasard. Le **dégradé eau**
   et la **courbe Peep** rappellent le logo aux moments forts (login, états actifs,
   accents), sans jamais polluer la grille de travail.

> **Le mantra** : *l'app est sombre et silencieuse ; la marque est l'eau qui s'allume.*

### Les trois motifs hérités du logo

| Motif | Origine logo | Rôle dans l'UI |
|-------|--------------|----------------|
| **Le dégradé eau** | Bleu de la grenouille → cyan « ee » → vert « ep » | Réservé aux moments signature (login, logo, hero, barre active). Jamais en aplat de fond de travail. |
| **La courbe Peep** | Le trait chartreuse sous le mot | Soulignement d'accent, séparateur héroïque, indicateur d'onglet/étape active. Toujours fin, toujours rare. |
| **L'émeraude** | Le « ep » vert vif | Couleur **d'action** : boutons primaires, succès, sélection. C'est la couleur la plus présente après les neutres. |

---

## 2. Système de couleurs

### 2.1 Principes

- **Fond quasi-noir bleuté** comme scène absolue (`--bg-base`).
- **Vert émeraude** = action, succès, marque (couleur la plus utilisée hors neutres).
- **Bleu azur** = information, liens, navigation secondaire.
- **Aqua/cyan** = couleur-pont « eau » : focus, sélection, accents interactifs, data-viz.
- **Lime/chartreuse** = accent **signature uniquement** (courbe, hero) — jamais fonctionnel.
- **Ambre** = strictement fonctionnel : surcharges manuelles & avertissements.
- Contraste minimum **4.5:1** sur tout texte ; **3:1** sur les éléments graphiques porteurs de sens.
- **Maximum 2 couleurs sémantiques** simultanées sur un même écran de travail.

### 2.2 Échelle neutre — « Ink » (fond + texte)

Bleu-undertone subtil sur tous les neutres : c'est ce qui relie le dark mode à la
marque sans le saturer.

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-base` | `#070B12` | Fond application (la scène) |
| `--bg-surface` | `#0C131F` | Cartes, panneaux, sidebar |
| `--bg-elevated` | `#131D2C` | Dropdowns, popovers, lignes surélevées |
| `--bg-overlay` | `#1C2A3B` | Hover de surface, sélection douce |
| `--bg-subtle` | `#24344A` | Inputs, séparateurs visibles, pistes de slider |
| `--line-subtle` | `#16202E` | Séparateurs internes (lignes de table) |
| `--line-base` | `#1F2D3F` | Bordure standard cartes/inputs |
| `--line-strong` | `#2B3C52` | Bordure visible, hover de bordure |
| `--fg` | `#ECF1F7` | Texte principal (blanc cassé cool — jamais `#fff` pur) |
| `--fg-2` | `#9DB0C4` | Texte secondaire, labels |
| `--fg-3` | `#647A91` | Placeholders, métadonnées |
| `--fg-4` | `#3B4859` | Désactivé |
| `--fg-inverse` | `#06140E` | Texte sur fond vert/lime/aqua vif |

### 2.3 Brand — Bleu azur (`info`)

Dérivé du bleu de la grenouille / du « P ». Navigation secondaire, liens, statut **ENVOYÉ**.

| Token | Hex |
|-------|-----|
| `--blue-300` | `#63B6EA` |
| `--blue-400` | `#2F9DDF` |
| `--blue-500` | `#1B86CF` ← référence logo |
| `--blue-600` | `#1670B2` |
| `--blue-700` | `#125A91` |
| `--blue-950` | `#0A2236` (fond de badge info) |

### 2.4 Brand — Aqua / Cyan (`aqua`) · la couleur-pont « eau »

Le cœur du dégradé du logo (le « ee »). C'est la nouveauté v3 : une couleur
**interactive et data** distincte du vert-succès et du bleu-lien. Focus rings,
sélection active, jauges hydrauliques, surbrillance d'eau.

| Token | Hex |
|-------|-----|
| `--aqua-300` | `#4FD0DE` |
| `--aqua-400` | `#25B8CB` |
| `--aqua-500` | `#14A5B8` ← référence logo |
| `--aqua-600` | `#0E8A9B` |
| `--aqua-700` | `#0B6E7C` |
| `--aqua-950` | `#06262C` |

### 2.5 Brand — Vert émeraude (`primary` / `success`)

Le « ep » du logo. **Couleur d'action.** Boutons primaires, états actifs, succès.

| Token | Hex |
|-------|-----|
| `--green-300` | `#5AD895` |
| `--green-400` | `#2FC773` |
| `--green-500` | `#18B55F` ← action principale |
| `--green-600` | `#139A50` (hover) |
| `--green-700` | `#0F7E41` (pressed) |
| `--green-950` | `#062B19` (fond de badge success) |

### 2.6 Brand — Lime / Chartreuse (`lime`) · signature uniquement

La courbe sous le logo. **Jamais une couleur fonctionnelle.** Réservée à : la courbe
Peep, le hero de login, un soulignement d'accent rare. Si tu hésites à l'utiliser,
ne l'utilise pas.

| Token | Hex |
|-------|-----|
| `--lime-300` | `#CDEB52` |
| `--lime-400` | `#B8DD2A` |
| `--lime-500` | `#A2CC14` ← référence courbe logo |
| `--lime-600` | `#86A90E` |

### 2.7 Sémantique fonctionnelle — Ambre & Rouge

**Ambre** = surcharge manuelle + avertissement (jamais décoratif). **Rouge** = danger.

| Ambre | Hex | | Rouge | Hex |
|-------|-----|---|-------|-----|
| `--amber-300` | `#FCD34D` | | `--red-300` | `#FCA5A5` |
| `--amber-400` | `#FBBF24` | | `--red-400` | `#F87171` |
| `--amber-500` | `#F59E0B` | | `--red-500` | `#EF4444` |
| `--amber-600` | `#D97706` | | `--red-600` | `#DC2626` |
| `--amber-950` | `#3A1E04` | | `--red-950` | `#3A0A0A` |

### 2.8 Dégradés & lueurs signature

```css
/* Le dégradé eau — signature Peep. Login, logo, barre active, hero. */
--gradient-brand:        linear-gradient(115deg, #1B86CF 0%, #14A5B8 48%, #18B55F 100%);

/* Variante « pleine énergie » avec la pointe chartreuse — hero / onboarding uniquement */
--gradient-brand-vivid:  linear-gradient(115deg, #1B86CF 0%, #14A5B8 38%, #18B55F 78%, #A2CC14 100%);

/* Lavis très doux — fonds de carte signature, halos, en-tête de section */
--gradient-brand-wash:   linear-gradient(115deg, rgba(27,134,207,.14) 0%, rgba(20,165,184,.12) 50%, rgba(24,181,95,.14) 100%);

/* Sheen de surface — micro-highlight haut de carte pour donner du relief */
--gradient-sheen:        linear-gradient(180deg, rgba(255,255,255,.045) 0%, rgba(255,255,255,0) 60%);

/* Lueurs (glow) */
--glow-primary: 0 0 0 1px rgba(24,181,95,.30), 0 10px 30px -8px rgba(24,181,95,.40);
--glow-aqua:    0 0 28px -6px rgba(20,165,184,.50);
--focus-ring:   0 0 0 3px rgba(20,165,184,.32);   /* focus = aqua, distinct du vert succès */
```

### 2.9 Bloc `:root` complet (à coller dans `index.css`)

```css
:root {
  /* Fonds */
  --bg-base:#070B12; --bg-surface:#0C131F; --bg-elevated:#131D2C;
  --bg-overlay:#1C2A3B; --bg-subtle:#24344A;
  /* Lignes */
  --line-subtle:#16202E; --line-base:#1F2D3F; --line-strong:#2B3C52;
  /* Texte */
  --fg:#ECF1F7; --fg-2:#9DB0C4; --fg-3:#647A91; --fg-4:#3B4859; --fg-inverse:#06140E;
  /* Bleu */
  --blue-300:#63B6EA; --blue-400:#2F9DDF; --blue-500:#1B86CF; --blue-600:#1670B2; --blue-700:#125A91; --blue-950:#0A2236;
  /* Aqua */
  --aqua-300:#4FD0DE; --aqua-400:#25B8CB; --aqua-500:#14A5B8; --aqua-600:#0E8A9B; --aqua-700:#0B6E7C; --aqua-950:#06262C;
  /* Vert */
  --green-300:#5AD895; --green-400:#2FC773; --green-500:#18B55F; --green-600:#139A50; --green-700:#0F7E41; --green-950:#062B19;
  /* Lime */
  --lime-300:#CDEB52; --lime-400:#B8DD2A; --lime-500:#A2CC14; --lime-600:#86A90E;
  /* Ambre */
  --amber-300:#FCD34D; --amber-400:#FBBF24; --amber-500:#F59E0B; --amber-600:#D97706; --amber-950:#3A1E04;
  /* Rouge */
  --red-300:#FCA5A5; --red-400:#F87171; --red-500:#EF4444; --red-600:#DC2626; --red-950:#3A0A0A;
  /* Dégradés & lueurs : voir §2.8 */
}
```

### 2.10 Mapping Tailwind + HeroUI (`tailwind.config.cjs`)

On expose **deux familles** : des tokens **sémantiques custom** (lisibilité du code)
et le **mapping HeroUI** (composants @heroui/react).

```js
// theme.extend.colors
colors: {
  // — Custom sémantique (utilise les vars : bg-app, bg-surface, text-fg, border-line…) —
  app:        'var(--bg-base)',
  surface:  { DEFAULT:'var(--bg-surface)', elevated:'var(--bg-elevated)', overlay:'var(--bg-overlay)', subtle:'var(--bg-subtle)' },
  line:     { DEFAULT:'var(--line-base)', subtle:'var(--line-subtle)', strong:'var(--line-strong)' },
  fg:       { DEFAULT:'var(--fg)', 2:'var(--fg-2)', 3:'var(--fg-3)', 4:'var(--fg-4)', inverse:'var(--fg-inverse)' },
  aqua:     { 300:'#4FD0DE',400:'#25B8CB',500:'#14A5B8',600:'#0E8A9B',700:'#0B6E7C',950:'#06262C' },
  lime:     { 300:'#CDEB52',400:'#B8DD2A',500:'#A2CC14',600:'#86A90E' },

  // — HeroUI sémantique —
  primary:    { DEFAULT:'#18B55F', foreground:'#06140E', 300:'#5AD895',400:'#2FC773',500:'#18B55F',600:'#139A50',700:'#0F7E41' },
  secondary:  { DEFAULT:'#1B86CF', foreground:'#ECF1F7', 300:'#63B6EA',400:'#2F9DDF',500:'#1B86CF',600:'#1670B2',700:'#125A91' },
  background:  '#070B12',
  foreground:  '#ECF1F7',
  default:    { 100:'#0C131F',200:'#131D2C',300:'#1C2A3B',400:'#24344A',500:'#3B4859',600:'#647A91',700:'#9DB0C4' },
  success:    { DEFAULT:'#18B55F', foreground:'#06140E' },
  warning:    { DEFAULT:'#F59E0B', foreground:'#06140E' },
  danger:     { DEFAULT:'#EF4444', foreground:'#ECF1F7' },
  focus:       '#14A5B8',   // aqua : focus distinct du vert succès
},
backgroundImage: {
  'brand':       'var(--gradient-brand)',
  'brand-vivid': 'var(--gradient-brand-vivid)',
  'brand-wash':  'var(--gradient-brand-wash)',
  'sheen':       'var(--gradient-sheen)',
},
```

> Les exemples de composants ci-dessous utilisent les **classes sémantiques**
> (`bg-surface`, `text-fg-2`, `border-line`). C'est volontaire : le code reste lisible
> et un changement de token se propage partout.

---

## 3. Typographie

### Polices

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
```

| Rôle | Police | Pourquoi |
|------|--------|----------|
| Interface / corps | **DM Sans** | Géométrique chaleureuse, chiffres tabulaires nets, excellente en petite taille |
| Données / refs / prix | **JetBrains Mono** | Toute valeur chiffrée d'un outil technique mérite le monospace : alignement vertical des colonnes |

```js
fontFamily: {
  sans: ['DM Sans','ui-sans-serif','system-ui'],
  mono: ['JetBrains Mono','ui-monospace','monospace'],
},
// Active les chiffres tabulaires partout sur les données :
// className="font-mono tabular-nums" ou utilitaire global .num
```

```css
/* index.css — chiffres alignés sur toutes les données */
.num { font-family: 'JetBrains Mono', ui-monospace, monospace; font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
```

### Échelle typographique

| Token | Taille / LH | Graisse | Usage |
|-------|-------------|---------|-------|
| `text-2xs` | 10 / 1.4 | 600 | Micro-labels, uppercase tracking |
| `text-xs` | 12 / 1.5 | 400–500 | Métadonnées, badges, légendes |
| `text-sm` | 13 / 1.5 | 400–500 | Corps secondaire, inputs, labels |
| `text-base` | 15 / 1.6 | 400 | Corps principal |
| `text-lg` | 17 / 1.4 | 600 | En-têtes de section |
| `text-xl` | 20 / 1.3 | 700 | Titres de carte |
| `text-2xl` | 24 / 1.2 | 700 | Titres de page |
| `text-3xl` | 30 / 1.15 | 800 | Hero / login |
| `text-4xl` | 38 / 1.1 | 800 | KPI géant (dashboard) |

**Règles**
- `font-medium` (500) → labels & éléments d'interface.
- `font-semibold` (600) → en-têtes de section, en-têtes de colonne.
- `font-bold` (700) → titres de page.
- Micro-labels uppercase : `text-2xs font-semibold uppercase tracking-[0.12em] text-fg-3`.
- `.num` (mono tabulaire) → **toute** référence, valeur de calcul, prix, dimension, quantité.
- `text-wrap: balance` sur les titres ; `text-wrap: pretty` sur les paragraphes.

---

## 4. Spacing, grille & rayons

### Échelle d'espacement (base 4px)

`2 · 4 · 6 · 8 · 12 · 16 · 20 · 24 · 32 · 40 · 48 · 64`
Densité d'un outil métier : **gaps serrés** (12–16) dans les formulaires, **respirations**
(24–32) entre blocs. Padding de page `p-6` (24px), padding de carte `p-5` (20px).

> Toujours composer en **flex/grid + `gap`**, jamais en marges inline. Une rangée de
> boutons, de chips, d'icônes = `flex items-center gap-2`.

### Rayons (radius)

| Token | Valeur | Usage |
|-------|--------|-------|
| `rounded-md` | 8px | Chips, petits badges, tags |
| `rounded-lg` | 10px | **Inputs, boutons, selects** |
| `rounded-xl` | 14px | **Cartes, dropdowns, popovers** |
| `rounded-2xl` | 18px | Modales, carte de login, panneaux hero |
| `rounded-full` | — | Avatars, dots, pills de statut, toggles |

```js
// tailwind borderRadius extend
borderRadius: { lg:'10px', xl:'14px', '2xl':'18px' }
```

---

## 5. Élévation, ombres & profondeur

Dark mode → la profondeur vient de **la surface qui s'éclaircit** + **une ombre portée**
+ un **hairline supérieur** (highlight de 1px). On évite les ombres colorées sauf le glow primaire.

```css
/* index.css */
--shadow-e1: 0 1px 2px rgba(0,0,0,.40), 0 1px 3px rgba(0,0,0,.30);                 /* carte */
--shadow-e2: 0 8px 24px -8px rgba(0,0,0,.60), 0 2px 6px rgba(0,0,0,.40);           /* dropdown, popover */
--shadow-e3: 0 30px 60px -12px rgba(0,0,0,.70), 0 12px 24px -8px rgba(0,0,0,.50);  /* modale */
--hairline:  inset 0 1px 0 rgba(255,255,255,.045);                                /* highlight haut */
```

| Niveau | Surface | Ombre | Quand |
|--------|---------|-------|-------|
| 0 | `bg-app` | — | Scène / fond de page |
| 1 | `bg-surface` + `--hairline` | `e1` | Cartes, sidebar, table |
| 2 | `bg-elevated` + `--hairline` | `e2` | Dropdowns, popovers, toasts |
| 3 | `bg-elevated` + `--hairline` | `e3` | Modales, command palette |

> **Glow vert** (`--glow-primary`) : réservé au bouton primaire au survol et au CTA hero.
> **Glow aqua** (`--glow-aqua`) : éléments « eau » actifs (jauge sélectionnée, plan focus).

---

## 6. Motion

Mouvement **bref et net** — c'est un outil de production, pas une vitrine.

```css
--ease-out:      cubic-bezier(.16, 1, .3, 1);    /* entrées, snap */
--ease-standard: cubic-bezier(.4, 0, .2, 1);     /* transitions d'état */
--dur-micro: 120ms;   /* hover, press */
--dur-base:  180ms;   /* défaut */
--dur-over:  240ms;   /* overlays, dropdowns */
--dur-page:  320ms;   /* transitions de route */
```

**Règles** : couleurs/fonds en `--dur-micro`. Apparitions de panneaux en `--dur-over` +
léger `translateY(4px)→0`. **Jamais > 320ms** sur une interaction fréquente. Respecter
`prefers-reduced-motion` (couper transforms & spinners, garder les fades).

```css
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition-duration: .01ms !important; } }
```

---

## 7. Composants

### 7.1 Button

`inline-flex items-center gap-2`, hauteur fixe, `font-medium`, transitions systématiques.

```ts
type ButtonVariant = 'primary' | 'secondary' | 'aqua' | 'danger' | 'ghost' | 'outline'
type ButtonSize    = 'xs' | 'sm' | 'md' | 'lg'
```

| Variant | Fond | Texte | Hover | Bordure |
|---------|------|-------|-------|---------|
| `primary` | `bg-primary` | `text-fg-inverse` | `bg-primary-600` + `--glow-primary` | — |
| `secondary` | `bg-surface-elevated` | `text-fg` | `bg-surface-overlay` | `border-line` |
| `aqua` | `bg-aqua-500/12` | `text-aqua-300` | `bg-aqua-500/18` | `border-aqua-500/30` |
| `danger` | `bg-danger` | `text-white` | `bg-red-700` | — |
| `ghost` | `transparent` | `text-fg-2` | `bg-surface-elevated text-fg` | — |
| `outline` | `transparent` | `text-primary-400` | `bg-primary/10` | `border-primary/40` |

| Size | Hauteur | Padding | Texte |
|------|---------|---------|-------|
| `xs` | `h-7` | `px-2.5` | `text-xs` |
| `sm` | `h-8` | `px-3` | `text-sm` |
| `md` | `h-9` | `px-4` | `text-sm` |
| `lg` | `h-11` | `px-6` | `text-base` |

```tsx
// primary · md
className="inline-flex items-center justify-center gap-2 h-9 px-4 rounded-lg bg-primary text-fg-inverse text-sm font-semibold
           shadow-[var(--hairline)] transition-all duration-[120ms] ease-[cubic-bezier(.16,1,.3,1)]
           hover:bg-primary-600 hover:shadow-[var(--glow-primary)] active:bg-primary-700
           focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]
           disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
```

> Le **CTA hero** (login, action principale de page vide) peut porter le `bg-brand`
> (dégradé eau) + `text-white` — c'est le seul endroit où le dégradé devient un bouton.

### 7.2 Input

```tsx
// Base
className="h-9 w-full rounded-lg bg-app/60 border border-line px-3 text-sm text-fg
           placeholder:text-fg-3 transition-all duration-[120ms]
           focus:outline-none focus:border-aqua-500 focus:shadow-[var(--focus-ring)]"

// État surchargé (valeur manuelle) — ambre fonctionnel
className="h-9 w-full rounded-lg bg-amber-950/30 border border-amber-500/60 px-3 text-sm text-amber-300
           focus:outline-none focus:border-amber-400 focus:shadow-[0_0_0_3px_rgba(245,158,11,.25)]"

// Input numérique (dimensions, prix) → mono tabulaire
className="... text-right font-mono tabular-nums"
```

- **Label** : `text-2xs font-semibold text-fg-3 uppercase tracking-[0.12em] mb-1.5`
- **Helper** : `text-xs text-fg-3 mt-1`
- **Erreur** : `text-xs text-red-400 mt-1` + `border-red-500/60`
- **Unité suffixée** (m³, kW, mm) : adornment `text-xs text-fg-3 font-mono` à droite, non éditable.

### 7.3 Select (HeroUI)

```tsx
classNames={{
  trigger: "bg-app/60 border-line hover:border-line-strong data-[focus=true]:border-aqua-500 data-[focus=true]:shadow-[var(--focus-ring)] rounded-lg h-9",
  value: "text-fg text-sm",
  popoverContent: "bg-surface-elevated border border-line rounded-xl shadow-[var(--shadow-e2)]",
  listboxItem: "data-[hover=true]:bg-surface-overlay data-[selected=true]:bg-primary/12 data-[selected=true]:text-primary-300",
}}
```

### 7.4 Card

Unité de composition. `rounded-xl`, `bg-surface`, hairline, bordure subtile.

```tsx
// Standard
<div className="rounded-xl bg-surface border border-line p-5 shadow-[var(--shadow-e1),var(--hairline)]">

// Avec header
<div className="rounded-xl bg-surface border border-line overflow-hidden shadow-[var(--shadow-e1),var(--hairline)]">
  <div className="px-5 py-4 border-b border-line flex items-center justify-between">
    <h3 className="text-sm font-semibold text-fg">Titre</h3>
  </div>
  <div className="p-5">…</div>
</div>

// Carte signature (accent eau) — en-tête de section / résultats hydrauliques
<div className="relative rounded-xl border border-line p-5 overflow-hidden
                bg-surface bg-[image:var(--gradient-brand-wash)]">
  {/* courbe Peep en filigrane optionnelle, voir §8 */}
</div>

// Carte accent latéral (bord coloré porteur de sens)
<div className="rounded-xl bg-surface border border-line border-l-2 border-l-primary p-5">
```

### 7.5 Stat / KPI Card (dashboard)

Composant SaaS clé pour l'accueil — chiffre héroïque mono, libellé discret, delta optionnel.

```tsx
<div className="rounded-xl bg-surface border border-line p-5 shadow-[var(--hairline)]">
  <div className="flex items-center justify-between">
    <p className="text-2xs font-semibold uppercase tracking-[0.12em] text-fg-3">Devis acceptés</p>
    <FileCheck size={16} className="text-aqua-400" />
  </div>
  <p className="mt-3 font-mono tabular-nums text-4xl font-bold text-fg">128</p>
  <div className="mt-2 flex items-center gap-1.5 text-xs">
    <TrendingUp size={13} className="text-primary-400" />
    <span className="font-mono text-primary-400">+12%</span>
    <span className="text-fg-3">vs. mois dernier</span>
  </div>
</div>
```

### 7.6 Badge / Chip de statut

`rounded-full`, `text-xs font-medium`, `px-2.5 py-0.5`. Un point coloré précède le libellé.

```tsx
const statusConfig = {
  DRAFT:    { label:'BROUILLON', dot:'bg-amber-400', classes:'bg-amber-950/50 text-amber-300 border border-amber-500/25' },
  SENT:     { label:'ENVOYÉ',    dot:'bg-blue-400',  classes:'bg-blue-950/50  text-blue-300  border border-blue-500/25'  },
  ACCEPTED: { label:'ACCEPTÉ',   dot:'bg-green-400', classes:'bg-green-950/50 text-green-300 border border-green-500/25' },
  REJECTED: { label:'REFUSÉ',    dot:'bg-red-400',   classes:'bg-red-950/50   text-red-300   border border-red-500/25'   },
}
// <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${c.classes}`}>
//   <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} /> {c.label}
// </span>
```

### 7.7 Champ surchargé (override badge)

Indicateur d'une valeur écrasée manuellement (cœur métier de Peep).

```tsx
<div className="relative">
  <input className="field-overridden h-9 w-full rounded-lg px-3 text-sm font-mono text-right" />
  <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-amber-400 ring-2 ring-app" />
</div>
```

```css
/* index.css */
.field-overridden { @apply border border-amber-500/60 bg-amber-950/25 text-amber-300; }
```

### 7.8 Table (lignes de devis)

```tsx
<div className="rounded-xl border border-line overflow-hidden">
  <table className="w-full">
    <thead>
      <tr className="bg-surface border-b border-line">
        <th className="px-4 py-3 text-left text-2xs font-semibold text-fg-3 uppercase tracking-[0.1em]">Désignation</th>
        <th className="px-4 py-3 text-right …">Qté</th>{/* numériques alignés à droite */}
      </tr>
    </thead>
    <tbody>
      {/* Ligne */}
      <tr className="border-b border-line-subtle hover:bg-surface-overlay transition-colors duration-[120ms]">
        <td className="px-4 py-3 text-sm text-fg-2">…</td>
        <td className="px-4 py-3 text-right text-sm font-mono tabular-nums text-fg">…</td>
      </tr>
      {/* Ligne sélectionnée */}
      <tr className="border-b border-line-subtle bg-primary/[0.06] border-l-2 border-l-primary">
      {/* Ligne masquée (visible=false) */}
      <tr className="opacity-40"><td className="line-through text-fg-3">…</td></tr>
    </tbody>
  </table>
</div>
```

- **Valeurs numériques** : toujours `font-mono tabular-nums`, alignées à droite.
- **Total** : ligne pied `border-t border-line-strong`, libellé `text-fg-2`, montant `text-lg font-bold font-mono text-fg`.

### 7.9 Tabs & Segmented control

```tsx
// Tabs — souligné par la courbe (indicateur aqua/dégradé)
<div className="flex gap-1 border-b border-line">
  <button className="relative px-3 py-2.5 text-sm font-medium text-fg-2 hover:text-fg">
    Onglet
    {/* actif : */}
    <span className="absolute -bottom-px inset-x-2 h-0.5 rounded-full bg-aqua-500" />
  </button>
</div>

// Segmented (toggle de vue : Liste / Grille) — piste sombre, sélection surélevée
<div className="inline-flex p-0.5 rounded-lg bg-app border border-line">
  <button className="px-3 h-7 rounded-[7px] text-xs font-medium text-fg-2">Liste</button>
  <button className="px-3 h-7 rounded-[7px] text-xs font-medium bg-surface-elevated text-fg shadow-[var(--hairline)]">Grille</button>
</div>
```

### 7.10 Switch / Toggle (options piscine)

```tsx
// Off
<button className="w-9 h-5 rounded-full bg-surface-subtle transition-colors duration-[120ms] relative">
  <span className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-fg-2 transition-transform" />
</button>
// On → vert primaire, pastille blanche translatée
<button className="w-9 h-5 rounded-full bg-primary relative">
  <span className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white translate-x-4" />
</button>
```

### 7.11 Modal

```tsx
// Overlay
<div className="fixed inset-0 z-50 bg-black/65 backdrop-blur-[3px] flex items-center justify-center p-4">
// Conteneur
<div className="relative w-full max-w-lg rounded-2xl bg-surface-elevated border border-line p-6 shadow-[var(--shadow-e3),var(--hairline)]">
  <div className="flex items-start justify-between mb-6">
    <h2 className="text-lg font-bold text-fg">Titre</h2>
    <button className="p-1 rounded-lg text-fg-3 hover:text-fg hover:bg-surface-overlay transition-colors"><X size={18} /></button>
  </div>
  {/* corps */}
  <div className="flex justify-end gap-3 mt-6 pt-5 border-t border-line">
    <Button variant="ghost">Annuler</Button>
    <Button variant="primary">Confirmer</Button>
  </div>
</div>
```

### 7.12 Tooltip

```tsx
classNames={{ content: "bg-surface-elevated text-fg text-xs border border-line-strong rounded-lg shadow-[var(--shadow-e2)] px-3 py-1.5" }}
```

### 7.13 Jauge / Meter (résultats hydrauliques)

Visualise une valeur calculée dans sa plage (charge pompe, vitesse filtration). Piste
aqua = nominal, ambre = surchargé, rouge = hors plage.

```tsx
<div className="h-1.5 w-full rounded-full bg-surface-subtle overflow-hidden">
  <div className="h-full rounded-full bg-aqua-500" style={{ width: `${pct}%` }} />
</div>
<div className="mt-1 flex justify-between text-2xs font-mono text-fg-3">
  <span>0</span><span className="text-aqua-300">{value} m³/h</span><span>max</span>
</div>
```

### 7.14 Command / Search bar

```tsx
<div className="flex items-center gap-2 h-9 rounded-lg bg-app border border-line px-3 focus-within:border-aqua-500 focus-within:shadow-[var(--focus-ring)]">
  <Search size={15} className="text-fg-3" />
  <input className="flex-1 bg-transparent text-sm text-fg placeholder:text-fg-3 focus:outline-none" placeholder="Rechercher un devis, un client…" />
  <kbd className="text-2xs font-mono text-fg-3 px-1.5 py-0.5 rounded bg-surface-elevated border border-line">⌘K</kbd>
</div>
```

---

## 8. La courbe Peep (motif signature)

Le trait chartreuse du logo devient un **élément réutilisable**. Toujours fin (1.5–2px),
toujours rare, jamais sous un texte de travail.

```tsx
// SVG inline — soulignement hero / séparateur de section
<svg viewBox="0 0 320 12" className="w-full h-3" preserveAspectRatio="none" aria-hidden="true">
  <path d="M2 9 C 90 1, 230 1, 318 6" fill="none" stroke="url(#peepCurve)" strokeWidth="2" strokeLinecap="round" />
  <defs>
    <linearGradient id="peepCurve" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0"   stop-color="#1B86CF" />
      <stop offset="0.5" stop-color="#14A5B8" />
      <stop offset="1"   stop-color="#A2CC14" />
    </linearGradient>
  </defs>
</svg>
```

**Usages autorisés** : sous le titre de login, comme séparateur d'en-tête de page hero,
comme indicateur d'onglet/étape actif (version courte). **Interdit** : en décoration de
fond répétée, sous des libellés de formulaire, dans les tables.

---

## 9. Layout & navigation

### Structure

```
┌──────────────────────────────────────────────────────┐
│ SIDEBAR (240px)        │  MAIN                        │
│ bg-surface             │  bg-app                      │
│ border-r border-line   │  flex-1                      │
│  Logo + wordmark       │  TopBar (titre + actions)    │
│  ───────────────       │  ──────────────────────────  │
│  Navigation            │  Page content · p-6          │
│  ───────────────       │                              │
│  User (bas)            │                              │
└──────────────────────────────────────────────────────┘
```

**Mobile** : drawer latéral déclenché par hamburger dans un topbar pleine largeur.

### Sidebar

```tsx
<aside className="hidden md:flex flex-col w-60 h-screen bg-surface border-r border-line flex-shrink-0">
  {/* Logo (sur fond noir du logo → s'intègre nativement) */}
  <div className="px-5 py-5 border-b border-line">
    <img src={peepLogo} alt="Peep" className="h-8" />
  </div>

  <nav className="flex-1 py-3 overflow-y-auto">
    <p className="px-4 pt-2 pb-2 text-2xs font-semibold text-fg-4 uppercase tracking-[0.14em]">Navigation</p>

    {/* Item inactif */}
    <a className="flex items-center gap-3 mx-2 px-3 py-2.5 rounded-lg text-sm text-fg-2 hover:text-fg hover:bg-surface-overlay transition-colors duration-[120ms]">
      <Icon size={16} className="flex-shrink-0" /> Libellé
    </a>

    {/* Item ACTIF — barre verticale aqua + teinte primaire */}
    <a className="relative flex items-center gap-3 mx-2 px-3 py-2.5 rounded-lg text-sm font-medium text-primary-300 bg-primary/[0.10] border border-primary/20">
      <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-full bg-gradient-to-b from-aqua-400 to-primary-500" />
      <Icon size={16} className="flex-shrink-0 text-primary-400" /> Libellé
    </a>
  </nav>

  {/* User */}
  <div className="mt-auto border-t border-line p-4">
    <div className="flex items-center gap-3">
      <div className="w-8 h-8 rounded-full grid place-items-center text-xs font-semibold text-fg-inverse bg-brand">JD</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-fg truncate">Jean Dupont</p>
        <p className="text-xs text-fg-3 truncate">Commercial</p>
      </div>
      <button className="p-1.5 rounded-lg text-fg-3 hover:text-red-400 hover:bg-red-950/30 transition-colors"><LogOut size={15} /></button>
    </div>
  </div>
</aside>
```

### TopBar de page

```tsx
<div className="flex items-center justify-between px-6 py-4 border-b border-line">
  <div>
    <h1 className="text-xl font-bold text-fg">Titre de page</h1>
    <p className="text-sm text-fg-3 mt-0.5">Sous-titre ou fil d'Ariane</p>
  </div>
  <div className="flex items-center gap-2">{/* actions */}</div>
</div>
```

### Grilles

```tsx
// Dashboard — bandeau de KPI
<div className="grid grid-cols-2 lg:grid-cols-4 gap-4">

// Nouveau devis — split saisie / résultats
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
  <div className="lg:col-span-1 space-y-4">{/* dimensions + options */}</div>
  <div className="lg:col-span-2 space-y-4">{/* résultats + plan */}</div>
</div>

// Paramètres — 2 colonnes
<div className="grid grid-cols-1 md:grid-cols-2 gap-6">
```

---

## 10. Data-viz & plan 2D hydraulique

L'app génère un **plan SVG** d'installation. Ses couleurs sont normalisées ici pour
rester cohérentes avec la marque et lisibles sur fond sombre comme sur fond papier (PDF).

| Élément | Couleur app (dark) | Couleur PDF (papier) | Token |
|---------|--------------------|-----------------------|-------|
| Contour bassin / eau | `--aqua-500` `#14A5B8` | `#0E8A9B` | `plan-water` |
| Tuyau aspiration | `--blue-500` `#1B86CF` | `#125A91` | `plan-suction` |
| Tuyau refoulement | `--green-500` `#18B55F` | `#0F7E41` | `plan-return` |
| Pompe | `--green-400` `#2FC773` | `#0F7E41` | `plan-pump` |
| Filtre à sable | `--aqua-400` `#25B8CB` | `#0E8A9B` | `plan-filter` |
| Skimmer | `--blue-400` `#2F9DDF` | `#1670B2` | `plan-skimmer` |
| Refoulement (buse) | `--lime-500` `#A2CC14` | `#86A90E` | `plan-nozzle` |
| Vanne | `--fg-2` `#9DB0C4` | `#475569` | `plan-valve` |
| Cotes / annotations | `--fg-3` `#647A91` | `#94A3B8` | `plan-dim` |

- Fond du plan dans l'app : `bg-app`, grille `--line-subtle` à 24px.
- **Palette catégorielle** (graphes, répartition coûts du devis) :
  `#18B55F` · `#1B86CF` · `#14A5B8` · `#A2CC14` · `#F59E0B` · `#9DB0C4` (dans cet ordre).
- Trait de plan : `stroke-width` 2 (structure), 1.5 (tuyaux), 1 (cotes). Jamais de remplissage saturé : aplats à `/10`–`/15`.

---

## 11. Page de connexion

Le seul écran qui **assume pleinement la marque** : dégradé eau, courbe Peep, halos.

```tsx
<div className="relative min-h-screen bg-app flex items-center justify-center p-6 overflow-hidden">

  {/* Halos « eau » en fond — bleu + vert, jamais agressifs */}
  <div className="pointer-events-none absolute -top-40 -right-32 w-[520px] h-[520px] rounded-full bg-aqua-500/10 blur-[120px]" />
  <div className="pointer-events-none absolute -bottom-40 -left-32 w-[520px] h-[520px] rounded-full bg-primary/10 blur-[120px]" />

  <div className="relative w-full max-w-sm">
    <div className="text-center mb-8">
      <img src={peepLogo} alt="Peep" className="h-14 mx-auto mb-2" />
      {/* Courbe Peep sous le logo (voir §8) */}
      <p className="text-sm text-fg-3 mt-3">Outil de devis hydraulique · ETS&nbsp;Maria</p>
    </div>

    <div className="rounded-2xl bg-surface border border-line p-8 shadow-[var(--shadow-e3),var(--hairline)]">
      <h2 className="text-xl font-bold text-fg mb-6">Connexion</h2>
      {/* champs… */}
      <Button variant="primary" className="w-full bg-brand text-white hover:shadow-[var(--glow-aqua)]">Se connecter</Button>
    </div>

    <p className="text-center text-xs text-fg-4 mt-6">ETS Maria © {year} · Depuis 1937</p>
  </div>
</div>
```

---

## 12. Stepper (wizard de création en 4 étapes)

```tsx
<div className="flex items-center">
  {steps.map((s, i) => (
    <div key={i} className="flex items-center">
      <div className={cn(
        "w-8 h-8 rounded-full grid place-items-center text-xs font-semibold border-2 transition-all duration-[180ms]",
        isComplete && "bg-primary border-primary text-fg-inverse",
        isCurrent  && "bg-transparent border-aqua-500 text-aqua-300 shadow-[var(--focus-ring)]",
        isPending  && "bg-transparent border-line text-fg-4",
      )}>
        {isComplete ? <Check size={14} /> : i + 1}
      </div>
      {i < steps.length - 1 && (
        <div className={cn("h-0.5 w-16 transition-colors duration-[180ms]",
          isComplete ? "bg-gradient-to-r from-primary to-aqua-500" : "bg-line")} />
      )}
    </div>
  ))}
</div>
```

---

## 13. Indicateur de sauvegarde automatique

```tsx
// En cours
<div className="flex items-center gap-1.5 text-xs text-fg-3"><RefreshCw size={12} className="animate-spin" /> Enregistrement…</div>
// Enregistré
<div className="flex items-center gap-1.5 text-xs text-primary-400"><Check size={12} /> Enregistré</div>
// Non sauvegardé
<div className="flex items-center gap-1.5 text-xs text-amber-400"><AlertCircle size={12} /> Modifications non sauvegardées</div>
```

---

## 14. États & feedback

### Empty state

```tsx
<div className="flex flex-col items-center justify-center py-16 text-center">
  <div className="w-16 h-16 rounded-2xl bg-surface-elevated border border-line grid place-items-center mb-4 shadow-[var(--hairline)]">
    <FileText size={28} className="text-fg-3" />
  </div>
  <h3 className="text-base font-semibold text-fg mb-1">Aucun devis</h3>
  <p className="text-sm text-fg-3 mb-5 max-w-xs">Créez votre premier devis pour commencer.</p>
  <Button variant="primary" size="sm"><Plus size={15} /> Nouveau devis</Button>
</div>
```

### Loading skeleton

```tsx
<div className="rounded-xl bg-surface border border-line p-5 space-y-3">
  <div className="h-4 w-1/3 rounded bg-surface-elevated animate-pulse" />
  <div className="h-3 w-2/3 rounded bg-surface-elevated animate-pulse" />
  <div className="h-3 w-1/2 rounded bg-surface-elevated animate-pulse" />
</div>
```

### Toast

```tsx
// Succès — glass + accent vert
<div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-surface-elevated/90 backdrop-blur-md border border-primary/30 text-primary-300 text-sm shadow-[var(--shadow-e2)]">
  <Check size={16} /> Devis enregistré avec succès
</div>
// Erreur
<div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-surface-elevated/90 backdrop-blur-md border border-red-500/30 text-red-300 text-sm shadow-[var(--shadow-e2)]">
  <AlertCircle size={16} /> Une erreur est survenue
</div>
```

---

## 15. Icônes

**Librairie** : Lucide React. Trait `1.75`, couleur **toujours `currentColor`** (jamais codée en dur).

| Contexte | Taille |
|----------|--------|
| Navigation sidebar | `16` |
| Boutons avec texte | `15` |
| Actions inline (table) | `14` |
| Décoratives / section | `18–20` |
| Hero (login, états vides) | `28–40` |

| Icône | Usage |
|-------|-------|
| `LayoutDashboard` | Dashboard |
| `FileText` / `FileCheck` | Devis / devis accepté |
| `BookOpen` | Catalogue |
| `Users` | Utilisateurs |
| `Settings2` | Paramètres |
| `LogOut` | Déconnexion |
| `Plus` | Créer |
| `Search` | Recherche / ⌘K |
| `Eye` / `EyeOff` | Visibilité ligne / mot de passe |
| `Trash2` · `Pencil` · `X` | Supprimer · éditer · fermer |
| `RefreshCw` | Recalculer / chargement |
| `Download` | Export PDF |
| `TrendingUp` | Delta KPI |
| `Check` · `AlertCircle` | Succès · avertissement |
| `ChevronDown` | Select / accordéon |
| `Waves` · `Flame` · `Wind` · `Lightbulb` | Spa · chauffage · contre-courant · éclairage |
| `Droplets` · `Gauge` | Branding hydraulique · jauge débit |

---

## 16. Règles d'application (DO / DON'T)

### ✅ À faire
- Fond `--bg-base` pour l'app, `--bg-surface` pour les surfaces — profondeur par **surface + ombre + hairline**.
- **Vert émeraude `#18B55F`** pour toute action primaire, état actif, succès.
- **Bleu azur `#1B86CF`** pour liens, info, statut ENVOYÉ.
- **Aqua `#14A5B8`** pour le focus, la sélection, les jauges et le « plan eau ».
- **Lime `#A2CC14`** UNIQUEMENT pour la courbe / le hero signature.
- Le **dégradé eau** réservé aux moments forts (login, logo, CTA hero, barre active).
- **`.num` (mono tabulaire)** sur toute valeur chiffrée, référence, prix, dimension.
- Bordures subtiles `border-line` systématiques ; `rounded-lg` contrôles, `rounded-xl` cartes.
- Composer en **flex/grid + `gap`**.

### ❌ À éviter
- Fond blanc/gris clair dans l'app — **dark mode permanent** (le PDF papier est la seule exception).
- Lime ou dégradé eau en aplat de fond de travail, en décoration répétée, sous des libellés.
- Plus de **2 couleurs sémantiques** simultanées sur un écran de travail.
- `text-white` pur → préférer `text-fg`.
- Ombres colorées hors `--glow-primary` / `--glow-aqua`.
- Animations > 320ms sur interactions fréquentes ; ignorer `prefers-reduced-motion`.
- Verts/bleus Tailwind génériques (`#22c55e`, `#3b82f6`) — **proscrits**, ils ne correspondent pas au logo. Utiliser les tokens de marque.
- Polices génériques (Inter, Roboto, Arial) — `DM Sans` + `JetBrains Mono` uniquement.

---

## 17. Fichiers de référence

| Fichier | Rôle |
|---------|------|
| `frontend/tailwind.config.cjs` | Tokens couleurs/typo, theme HeroUI, `backgroundImage` (dégradés) |
| `frontend/src/index.css` | Variables `:root`, ombres, `.num`, `.field-overridden`, reduced-motion |
| `frontend/src/main.tsx` | Provider HeroUI, classe `dark` |
| `frontend/src/components/ui/Button.tsx` | Variants boutons (§7.1) |
| `frontend/src/components/ui/Input.tsx` | Input + état surchargé (§7.2) |
| `frontend/src/components/ui/Card.tsx` · `StatCard.tsx` | Cartes & KPI (§7.4–7.5) |
| `frontend/src/components/ui/Modal.tsx` | Modale (§7.11) |
| `frontend/src/components/shared/StatusChip.tsx` | Badge statut (§7.6) |
| `frontend/src/components/shared/SaveIndicator.tsx` | Auto-save (§13) |
| `frontend/src/components/shared/PeepCurve.tsx` | Courbe signature SVG (§8) |
| `frontend/src/components/layout/AppLayout.tsx` | Sidebar + main (§9) |
| `backend/src/services/planGenerator.ts` · `svgSymbols.ts` | Couleurs plan 2D (§10) |
| `public/peep-logo.png` · `public/maria-logo.png` | Logos (app / PDF) |

---

*Design System Peep v3.0 — ETS Maria · Dérivé du logo · Usage interne uniquement.*
