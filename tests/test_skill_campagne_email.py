import re
from pathlib import Path

import pytest

SKILL = Path(__file__).parent.parent / "skills" / "campagne_email" / "SKILL.md"


@pytest.fixture(scope="module")
def skill() -> str:
    return SKILL.read_text(encoding="utf-8")


def section(text: str, title: str) -> str:
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## \d+\. |\Z)", text, re.M | re.S)
    assert match, f"section « {title} » absente"
    return match.group(1)


def test_dod_1_framing_is_set_before_writing(skill):
    cadrage = section(skill, "1. Cadrage, avant d'écrire")
    assert "Établir ce bloc avant d'écrire" in cadrage
    for point in ("**Cible**", "**Produit et acte**", "**Expéditeur et outil**", "**Qui valide**"):
        assert point in cadrage


def test_dod_1_any_contradiction_with_the_card_stops_the_writing(skill):
    cadrage = section(skill, "1. Cadrage, avant d'écrire")
    assert (
        "Si la demande est vide ou contredit la carte, sur quelque point que ce soit, s'arrêter et demander" in cadrage
    )
    assert "Une contradiction entre la demande et la carte arrête toujours l'écriture" in cadrage


def test_dod_2_target_is_counted_in_attio_before_writing(skill):
    cadrage = section(skill, "1. Cadrage, avant d'écrire")
    assert "L'effectif se compte dans Attio avec la skill `attio` avant d'écrire" in cadrage
    assert "« à compter » ne s'écrit que si Attio ne répond pas" in cadrage
    assert "La cible se compte dans le CRM Attio avec la skill `attio`" in skill


def test_dod_2_existing_emails_are_listed_in_brevo_before_writing(skill):
    assert "**Ce qu'elle reçoit déjà**" in section(skill, "1. Cadrage, avant d'écrire")
    assert "La skill `brevo` les lit, avant d'écrire" in skill
    assert "« à vérifier » seulement si la skill `brevo` ne répond pas" in skill


def test_dod_3_draft_follows_the_tool_format_and_tracks_its_links(skill):
    format_outil = section(skill, "3. Format selon l'outil")
    assert "Brevo" in format_outil and "LGM" in format_outil
    for parametre in ("mtm_campaign", "mtm_source", "mtm_medium", "mtm_content"):
        assert parametre in format_outil
        assert parametre in section(skill, "12. Livraison")


def test_dod_4_ready_campaign_is_filed_for_validation(skill):
    livraison = section(skill, "12. Livraison")
    assert "« Campagnes à valider »" in livraison
    assert "Statut « À valider »" in livraison
    assert "skill `notion`" in livraison


def test_dod_4_nothing_is_scheduled_or_sent(skill):
    assert "aucun envoi, aucune programmation, aucun chargement dans Brevo ou LGM" in skill


def test_public_skill_names_nobody(skill):
    salutations = set(re.findall(r"Bonjour ([A-ZÉ][a-zé]+)", skill))
    signatures = set(re.findall(r"^\[?([A-ZÉ][a-zé]+)\]? de La plateforme", skill, re.M))
    assert salutations <= {"Madame", "Prénom"}
    assert signatures <= {"Prénom"}
