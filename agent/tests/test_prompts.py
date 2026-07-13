"""Tests de l'assemblage du contexte structuré (blocs <client> / <devis>)."""

import catalog
import prompts

CLIENT = {
    "id": 2, "code": "CMARTI01", "nom": "Camping Les Martinets",
    "contact": "Sophie Berthier", "email": "s.berthier@lesmartinets.fr",
    "telephone": "04 93 55 12 40", "ville": "Antibes", "type": "professionnel",
}
DOCUMENT = {
    "id": 16, "numero": "DE00118", "client_id": 2, "type": "devis",
    "objet": "Extension filtration pataugeoire + skimmers",
    "date_emission": "2026-06-20", "date_validite": "2026-08-19",
    "statut": "SENT", "montant_ht": 1220.0,
    "notes": "Relance téléphonique du 05/07 restée sans réponse",
    "lignes": [
        {"sage_ref": "PMP-HAY-SP033", "designation": "Pompe de filtration Powerline 0,33 kW mono - 8 m3/h",
         "quantite": 1.0, "prix_unitaire_ht": 449.0},
        {"sage_ref": "SKM-AST-BE", "designation": "Skimmer beton grande meurtriere blanc",
         "quantite": 2.0, "prix_unitaire_ht": 95.0},
    ],
}


def test_contexte_devis_dans_premier_message():
    msgs = prompts.build_messages("relance_devis", "", [], [], client=CLIENT, document=DOCUMENT)
    assert msgs[0]["role"] == "user"
    body = msgs[0]["content"]
    assert "DE00118" in body
    assert "20/06/2026" in body
    assert "1 220,00 € HT" in body
    assert "envoyé, sans réponse" in body
    assert "Camping Les Martinets" in body
    assert "PMP-HAY-SP033" in body
    assert "Rédige la relance" in body  # message par défaut quand l'employé n'écrit rien


def test_mail_libre_sans_blocs_structures():
    msgs = prompts.build_messages("mail_libre", "Mail au fournisseur Zodiac", [], [])
    body = msgs[0]["content"]
    assert "<client>" not in body
    assert "<devis>" not in body
    assert "Mail au fournisseur Zodiac" in body


def test_affinage_reprefixe_le_contexte():
    history = [
        {"role": "user", "content": "Rédige la relance pour le devis ci-dessus."},
        {"role": "assistant", "content": "Objet : Relance devis DE00118\n\n…"},
    ]
    msgs = prompts.build_messages("relance_devis", "plus court", history, [],
                                  client=CLIENT, document=DOCUMENT)
    assert "DE00118" in msgs[0]["content"]      # contexte re-préfixé au 1er message user
    assert msgs[-1]["content"] == "plus court"  # l'affinage reste brut


def test_catalog_by_refs_conserve_ordre():
    rows = catalog.by_refs(["FLT-AST-D400", "PMP-HAY-SP033", "REF-INCONNUE"])
    assert [r["sageRef"] for r in rows] == ["FLT-AST-D400", "PMP-HAY-SP033"]
