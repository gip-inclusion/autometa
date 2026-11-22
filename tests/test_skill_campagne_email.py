import re
from pathlib import Path

import pytest

SKILL = Path(__file__).parent.parent / "skills" / "campagne_email" / "SKILL.md"


@pytest.fixture(scope="module")
def skill() -> str:
    return SKILL.read_text(encoding="utf-8")


def section(text: str, title: str) -> str:
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert match, f"section « {title} » absente"
    return match.group(1)


def test_dod_1_framing_comes_before_writing_and_stops_on_missing_target_or_act(skill):
    cadrage = section(skill, "1. Cadrage, avant d'écrire")
    for point in ("**Cible**", "**Produit et acte**", "**Expéditeur et outil**", "**Qui valide**"):
        assert point in cadrage
    assert "Seules la cible et l'acte bloquent l'écriture" in cadrage
    assert "s'arrêter et demander" in cadrage


def test_dod_2_target_is_counted_in_attio_and_existing_emails_listed_in_brevo(skill):
    assert "La cible se compte dans le CRM Attio avec la skill `attio`" in skill
    assert "La skill `brevo` les lit" in skill
    assert "**Ce qu'elle reçoit déjà**" in section(skill, "1. Cadrage, avant d'écrire")


def test_dod_3_draft_follows_the_tool_format_and_tracks_its_links(skill):
    format_outil = section(skill, "3. Format selon l'outil")
    assert "Brevo" in format_outil and "LGM" in format_outil
    for parametre in ("mtm_campaign", "mtm_source", "mtm_medium", "mtm_content"):
        assert parametre in format_outil


def test_dod_4_ready_campaign_goes_to_validation_and_nothing_is_sent(skill):
    assert "« Campagnes à valider »" in skill
    assert "Statut « À valider »" in skill
    assert "aucun envoi, aucune programmation" in skill


def test_dod_4_no_person_is_named_in_the_public_skill(skill):
    salutations = re.findall(r"Bonjour ([A-ZÉ][a-zé]+)", skill)
    assert set(salutations) <= {"Madame", "Prénom"}
