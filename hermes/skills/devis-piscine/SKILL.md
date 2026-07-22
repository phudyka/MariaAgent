---
name: devis-piscine
description: "Créer un devis d'installation de filtration piscine (pompe + filtre + pièces) depuis l'abaque de dimensionnement ETS Maria. Volume obligatoire, anti-invention absolue, sortie texte brut."
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [
      devis,
      piscine,
      filtration,
      dimensionnement,
      chiffrage,
      pompe,
      filtre,
    ]
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
  largeur × profondeur moyenne) et N'ÉMETTRE AUCUN DEVIS, aucune ligne chiffrée,
  aucune référence.

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

- Texte brut uniquement : pas de gras, pas de titres #, pas de tableau Markdown.
  Les `|` du bloc matériel sont de simples séparateurs texte.
- Vouvoiement, ton artisan sérieux et chaleureux.
- Un humain relit, complète les `[À COMPLÉTER]` et envoie. Ne jamais présenter
  le devis comme définitif ou envoyé.
- Voix humaine : « Voici notre proposition pour votre bassin de 45 m³ » — jamais
  « l'abaque indique », « d'après nos sources », ni note [1].
