# Roadmap — évolutions de l'agent ETS Maria

Étapes possibles après la démo, ordonnées par rapport effort/valeur.
Rien ici n'est implémenté : c'est la carte, pas le voyage.

## 1. Consolidation immédiate (après retour de Maria)

- Compléter `agent/data/entreprise.md` avec Kévin (téléphone, conditions, délais réels).
- Remplacer le catalogue mock par un **export CSV réel de Sage** (même format `;` que
  l'import Peep : la colonne `sageRef` est déjà alignée). Zéro code à changer.
- Idem pour les **clients et devis mock** : `agent/seed_db.py` est déjà l'importeur
  CSV→SQLite (colonnes optionnelles `designation`/`prix_unitaire_ht` prévues pour
  les prix figés des exports réels). Remplacer les `*_mock.csv`, relancer
  `seed_db.py --force`, zéro code à changer.
- Collecter 5–10 vrais mails types de l'équipe → les intégrer comme exemples dans le
  prompt (few-shot) pour caler le ton maison.
- Recueillir le feedback des commerciaux : quelles tâches reviennent vraiment ?

## 2. Intégration Sage 100 (lecture seule d'abord)

Le serveur Windows héberge Sage 100. Deux paliers :

1. **Palier export (simple, robuste)** : tâche planifiée Windows qui exporte
   régulièrement articles/clients/devis en CSV vers un partage accessible à la VM.
   Côté agent, la mécanique existe déjà : `seed_db.py --force` réimporte les CSV
   dans `maria.db` (même schéma clients/documents/lignes que l'UI de sélection).
   Aucune écriture dans Sage, risque nul.
2. **Palier passerelle (temps réel)** : petit service Windows en lecture via les
   **Objets Métiers Sage 100** ou la base SQL (ODBC), exposant une API REST interne
   (LAN uniquement). L'agent interroge à la demande — même interface que `catalog.py`
   aujourd'hui, c'est prévu pour être remplacé.

L'écriture dans Sage (créer un devis, un client) est un chantier séparé, à ne pas
ouvrir avant que la lecture soit fiable et validée par l'expert-comptable/éditeur.

## 3. Intégration Peep

Peep expose déjà une API REST (JWT). Croisements naturels :

- L'agent rédige le **mail d'envoi d'un devis Peep** : `GET /quotes/:id` → brouillon
  personnalisé avec référence, montant, points clés.
- Peep affiche un bouton « Rédiger le mail » qui appelle l'agent.
- Plus tard : l'agent pré-remplit un devis Peep depuis un mail client
  (« piscine 8×4, skimmers » → `POST /calculate` → brouillon de devis).

## 4. Boîte mail réelle

Connecteur **IMAP/SMTP local** : lire les mails entrants, proposer un brouillon dans
le dossier Brouillons (jamais d'envoi automatique au départ). C'est l'étape qui
transforme la démo en outil quotidien — et celle qui exige les garde-fous les plus
stricts (voir §7).

## 5. Base documentaire (RAG)

Procédures internes, CGV, historique SAV, fiches techniques fabricants :

- embeddings locaux via Ollama (`nomic-embed-text` ou `bge-m3`),
- index local (sqlite-vec ou ChromaDB embarqué),
- l'agent cite ses sources internes dans les brouillons.

Même philosophie : tout reste sur la VM.

## 6. Nouvelles tâches

- Relances automatiques planifiées (liste des devis `SENT` > N jours via Peep).
- Courriers types (attestations, confirmations d'intervention) depuis templates DOCX.
- Synthèses : « résume les demandes SAV de la semaine » (nécessite §4 ou §5).

## 7. Gouvernance et sécurité (avant tout usage quotidien)

- Comptes utilisateurs + journal des générations (qui a généré quoi, quand).
- Charte d'usage : relecture humaine obligatoire, pas d'envoi direct.
- Revue périodique des brouillons envoyés vs générés (dérive du ton, erreurs).

## 8. Matériel

| Machine | Modèle conseillé | Attendu |
|---|---|---|
| VM Debian actuelle (CPU) | qwen3:4b-instruct-2507 | 5–15 tok/s — démo et petit volume |
| **Mac mini M4 32 Go** (prévu) | `qwen3:30b-a3b` (MoE, ~19 Go) ou `mistral-small3.2:24b` | 20–40 tok/s, qualité rédactionnelle nettement supérieure, RAG confortable |
| Alternative : GPU (RTX 4060 Ti 16 Go+) dans un poste Linux | mêmes modèles quantisés | équivalent Mac mini, plus bricolé |

Sur Mac mini : Ollama s'installe nativement (pas de VM), l'agent FastAPI est portable
tel quel. Le guide DEPLOY_MARIA.md reste valable en remplaçant §2–3 par l'install macOS.
