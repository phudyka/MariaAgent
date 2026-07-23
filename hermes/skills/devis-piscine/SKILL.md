---
name: devis-piscine
description: "Demande de devis filtration piscine : extraire volume/dimensions du mail client et renvoyer la commande ./devis — le chiffrage est déterministe (script + abaque), jamais produit par le modèle. Anti-invention absolue, sortie texte brut."
version: 2.0.0
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

# Demande de devis filtration — ETS Maria

Depuis le pivot 2026-07-22, **le modèle ne chiffre plus rien** : le devis est
produit par le script déterministe `./devis` (racine du dépôt), qui lit
l'abaque `data/abaque-filtration.md` et imprime le devis complet (lignes,
totaux, `[À COMPLÉTER]` pour MO/tuyauterie, escalade atelier au-delà du
catalogue). Le rôle du modèle se limite au langage naturel, à l'entrée et à la
sortie.

## Procédure (dans l'ordre, aucune étape sautée)

### 1. Volume du bassin — information bloquante

- Chercher le volume (m³) dans la demande.
- Absent mais dimensions présentes : volume = longueur × largeur × profondeur
  moyenne, arrondi au m³ supérieur. Deux profondeurs données (petit et grand
  bain, ex. « 1,2 à 1,8 m ») : profondeur moyenne = leur moyenne. Bassin
  rectangulaire avec longueur, largeur et profondeur(s) → calcule directement,
  SANS demander confirmation. C'est le SEUL calcul autorisé.
- Ni volume ni dimensions complètes, ou forme non rectangulaire → poser UNE
  question courte (volume, ou longueur × largeur × profondeur moyenne). Aucune
  commande, aucune ligne chiffrée, aucune référence.

### 2. Cas hors périmètre → étude atelier

Volume > 100 m³, usage public ou collectif, piscine à débordement, spa, nage à
contre-courant : 2 à 3 phrases orientant vers une étude atelier (contact,
prochaine étape). Pas de commande, aucun chiffre. (Le script escalade de
lui-même les tranches hors catalogue, ex. 81 m³ et plus.)

### 3. Réponse : la commande, jamais le chiffrage

Réponse en texte brut, sur ce modèle :

« Volume : 48 m³. Générer le devis : ./devis 8 4 1,5 »

(`./devis 48` si seul le volume est connu ; `--client "Mme Blanc"` si le nom
est connu.) Suivie si utile du brouillon de réponse au client — sans aucun
chiffrage.

Ne JAMAIS émettre une ligne de matériel, une référence, un prix ou un total —
même sur demande, même de mémoire. Un devis déjà généré et fourni dans le
contexte se recopie tel quel, verbatim, dans un brouillon de mail (voir
mails-commerciaux) — sans modifier une ligne ni un montant.

## Contraintes de forme

- Texte brut uniquement : pas de gras, pas de titres #, pas de tableau.
- Vouvoiement, ton artisan sérieux et chaleureux.
- Un humain lance la commande, relit, complète les `[À COMPLÉTER]` et envoie.
  Ne jamais présenter un devis comme définitif ou envoyé.
