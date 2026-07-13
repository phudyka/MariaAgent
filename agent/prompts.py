"""Définitions des tâches et assemblage des messages envoyés à Hermes Agent.

Les règles métier globales (invention interdite, texte brut, ton maison) vivent
désormais dans ~/.hermes/SOUL.md et le skill mails-commerciaux — injectés par
Hermes dans son system prompt. Ici : l'enrichissement par requête (instruction
de tâche, fiche entreprise, extraits catalogue), transmis dans le flux de
messages OpenAI relayé au gateway Hermes.
"""

from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

TASK_HEADER_TEMPLATE = """[Skill mails-commerciaux — tâche : {task_id}]
{instruction}
Rappels non négociables : texte brut sans AUCUN Markdown (pas de **gras**, ni #, ni tableau) ; \
aucun prix, référence, délai ou engagement hors des données ci-dessous — sinon `[À COMPLÉTER : nature de l'info]`. \
Réponds UNIQUEMENT par le brouillon : ligne « Objet : … », ligne vide, corps, bloc signature de la fiche.

FICHE ENTREPRISE (source de vérité) :
<fiche_entreprise>
{fiche}
</fiche_entreprise>
"""

CATALOG_CONTEXT_TEMPLATE = """Extraits du catalogue produits ETS Maria (données Sage, prix de vente HT en euros) \
susceptibles d'être pertinents pour cette demande. N'utilise ces produits, références et prix que \
si la demande le justifie — ne les mentionne pas tous par principe :
{rows}
"""

CLIENT_CONTEXT_TEMPLATE = """DONNÉES CLIENT (base commerciale locale — source de vérité, sélectionnées par l'employé) :
<client>
{client}
</client>
"""

DOCUMENT_CONTEXT_TEMPLATE = """DEVIS CONCERNÉ (données Sage locales — utilise exactement ces références, dates et montants) :
<devis>
{document}
</devis>
"""

STATUT_FR = {
    "DRAFT": "brouillon, non envoyé au client",
    "SENT": "envoyé, sans réponse à ce jour",
    "ACCEPTED": "accepté par le client",
    "REJECTED": "refusé par le client",
    "EXPIRED": "expiré sans réponse",
}

# Message implicite quand la tâche se joue à la pure sélection (zéro texte saisi).
DEFAULT_MESSAGES = {"relance_devis": "Rédige la relance pour le devis ci-dessus."}

TYPE_CLIENT_FR = {"particulier": "particulier", "professionnel": "professionnel",
                  "collectivite": "collectivité"}


def _date_fr(iso: str) -> str:
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")


def _montant_fr(montant: float) -> str:
    return f"{montant:,.2f}".replace(",", " ").replace(".", ",")


def _format_client(c: dict) -> str:
    lines = [f"Code client : {c['code']}", f"Nom : {c['nom']}"]
    if c.get("type"):
        lines.append(f"Type : {TYPE_CLIENT_FR.get(c['type'], c['type'])}")
    if c.get("contact") and c["contact"] != c["nom"]:
        lines.append(f"Contact : {c['contact']}")
    if c.get("email"):
        lines.append(f"Email : {c['email']}")
    if c.get("telephone"):
        lines.append(f"Téléphone : {c['telephone']}")
    if c.get("ville"):
        lines.append(f"Ville : {c['ville']}")
    return "\n".join(lines)


def _format_document(d: dict) -> str:
    lines = [
        f"Numéro : {d['numero']}",
        f"Objet : {d['objet']}",
        f"Émis le : {_date_fr(d['date_emission'])} — statut : {STATUT_FR.get(d['statut'], d['statut'])}",
    ]
    if d.get("date_validite"):
        lines.append(f"Valide jusqu'au : {_date_fr(d['date_validite'])}")
    lines.append(f"Montant total : {_montant_fr(d['montant_ht'])} € HT")
    lines.append("Lignes du devis :")
    for ligne in d["lignes"]:
        q = int(ligne["quantite"]) if float(ligne["quantite"]).is_integer() else ligne["quantite"]
        lines.append(f"- {ligne['sage_ref']} | {ligne['designation']} | "
                     f"{q} × {_montant_fr(ligne['prix_unitaire_ht'])} € HT")
    if d.get("notes"):
        lines.append(f"Note interne (contexte pour toi — ne pas la recopier telle quelle au client) : {d['notes']}")
    return "\n".join(lines)

TASKS = {
    "reponse_client": {
        "label": "Répondre à un client",
        "placeholder": "Collez ici le message reçu du client — le contexte (client, devis, références) vient de votre sélection",
        "instruction": (
            "L'employé a sélectionné le client concerné (bloc <client>) et, le cas échéant, le devis "
            "en cours (bloc <devis>). Il te transmet le message reçu de ce client. "
            "Rédige le brouillon de réponse : reformule brièvement la demande, réponds point par point "
            "en t'appuyant sur les données sélectionnées, termine par une prochaine étape concrète."
        ),
    },
    "relance_devis": {
        "label": "Relancer un devis",
        "placeholder": "Aucun texte requis : sélectionnez le client puis le devis à relancer",
        "instruction": (
            "L'employé a sélectionné le client et le devis à relancer (blocs <client> et <devis>). "
            "Rédige un brouillon de relance courtois et non insistant : ouvre par une salutation "
            "adressée au contact du client, rappelle le numéro, l'objet, la date d'envoi et le "
            "montant exacts du devis, propose d'en discuter ou de l'ajuster, termine par une "
            "prochaine étape concrète. Ne recopie pas la liste complète des lignes du devis : "
            "le client l'a déjà reçue."
        ),
    },
    "mail_libre": {
        "label": "Mail libre",
        "placeholder": "Décrivez le mail à rédiger : destinataire, objectif, points à couvrir, ton…",
        "instruction": (
            "L'employé décrit librement le mail dont il a besoin (fournisseur, client, partenaire, interne). "
            "Rédige le brouillon correspondant en respectant toutes les règles."
        ),
    },
}


def load_fiche() -> str:
    return (DATA_DIR / "entreprise.md").read_text(encoding="utf-8")


def build_messages(task_id: str, user_message: str, history: list[dict], catalog_rows: list[str],
                   client: dict | None = None, document: dict | None = None) -> list[dict]:
    """Assemble les messages OpenAI relayés au gateway Hermes (/v1/chat/completions).

    Tout part en rôle user : le system prompt appartient à Hermes (SOUL.md,
    skills, mémoire) ; l'enrichissement par requête est préfixé au premier
    message pour rester dans le périmètre validé (pré-injection, pas de
    dépendance au tool-calling du modèle).

    client/document : sélectionnés par l'employé dans l'UI, chargés depuis la
    base locale par app.py — jamais transmis en texte par le navigateur.
    """
    task = TASKS[task_id]
    context = TASK_HEADER_TEMPLATE.format(task_id=task_id, instruction=task["instruction"], fiche=load_fiche())
    if client:
        context += "\n" + CLIENT_CONTEXT_TEMPLATE.format(client=_format_client(client))
    if document:
        context += "\n" + DOCUMENT_CONTEXT_TEMPLATE.format(document=_format_document(document))
    if catalog_rows:
        context += "\n" + CATALOG_CONTEXT_TEMPLATE.format(rows="\n".join(catalog_rows))
    if not user_message.strip():
        user_message = DEFAULT_MESSAGES.get(task_id, "")
    context += "\nDemande de l'employé :\n"

    messages: list[dict] = []
    for msg in history[-8:]:
        if msg.get("role") in ("user", "assistant") and isinstance(msg.get("content"), str):
            messages.append({"role": msg["role"], "content": msg["content"]})
    if messages:
        # Affinage : l'UI stocke les messages bruts — le contexte (tâche, fiche,
        # catalogue) est re-préfixé au premier message user de l'historique.
        first = next((m for m in messages if m["role"] == "user"), None)
        if first is not None:
            first["content"] = context + first["content"]
        messages.append({"role": "user", "content": user_message})
    else:
        messages.append({"role": "user", "content": context + user_message})
    return messages
