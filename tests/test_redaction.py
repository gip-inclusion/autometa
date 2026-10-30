"""Masquage des secrets — web/redaction.py."""

import pytest

from web import redaction
from web.redaction import redact, secret_kinds

FAUX = "valeur-factice-de-test"  # gitleaks:allow
HEX = "0123456789abcdef0123456789abcdef"  # gitleaks:allow


@pytest.mark.parametrize(
    ("text", "secret", "kind"),
    [
        # httpx met l'URL complète dans ses exceptions, et check_matomo passe le jeton en paramètre.
        (
            f"Server error '500' for url 'https://matomo/index.php?module=API&token_auth={FAUX}'",
            FAUX,
            "paramètre d'URL sensible",
        ),
        (f"HTTP 401 sur https://x/api?api_key={FAUX}&format=json", FAUX, "paramètre d'URL sensible"),
        (f"échec https://y/?password={FAUX}", FAUX, "paramètre d'URL sensible"),
        (f"postgresql://u:{FAUX}@host/db", FAUX, "mot de passe de DSN"),
        (f'curl -d "token_auth={HEX}" https://matomo', HEX, "jeton Matomo"),
        ('{"token_auth": "' + HEX + '"}', HEX, "jeton Matomo"),
        ("export KEY=pmk_AbCdEf0123456789XyZ", "AbCdEf0123456789XyZ", "clé autometa-jobs"),
        ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz012", "abcdefghijklmnopqrstuvwxyz012", "jeton Bearer"),
        ("NOTION_TOKEN=ntn_abcdefghijklmnopqrstuv", "ntn_abcdefghijklmnopqrstuv", "jeton Notion"),
        ("cle sk-ant-api03-abcdefghijklmnopqrst", "abcdefghijklmnopqrst", "clé Anthropic"),
        # Tally signe ses liens de prévisualisation : le jeton est dans un paramètre dont le nom ne commence pas par token.
        (f"https://tally.so/forms/x/preview?accessToken={FAUX}&lang=fr", FAUX, "paramètre d'URL sensible"),
        (f"https://api.tally.so/x/pdf?a=1&signature={FAUX}", FAUX, "paramètre d'URL sensible"),
        ("jeton eyJhbGciOiJIUzI1.eyJzdWJtaXNzaW9u.c2lnbmF0dXJlMTIz collé", "eyJzdWJtaXNzaW9u", "jeton JWT"),
        (
            f"extrait … so_3314:{FAUX}-et-plus-long@base-so-3314.postgresql.example.com:36000",
            FAUX,
            "identifiants user:mot de passe",
        ),
    ],
)
def test_redact_removes_each_family_of_secret(text, secret, kind):
    assert secret not in redact(text)
    assert kind in secret_kinds(text)


def test_secret_kinds_ignores_what_is_already_masked():
    assert secret_kinds(redact(f"postgresql://u:{FAUX}@h/db Bearer abcdefghijklmnopqrstuvwxyz012")) == []


def test_a_configured_secret_is_masked_wherever_it_appears(mocker):
    mocker.patch.object(redaction.config, "NOTION_TOKEN", "valeur-du-jeton-configure")

    assert redact("le jeton est valeur-du-jeton-configure, voilà") == "le jeton est ***, voilà"
    assert secret_kinds("valeur-du-jeton-configure") == ["secret de configuration"]


@pytest.mark.parametrize("setting", ["DORA_STAGING_DB_URL", "MONRECAP_APPLI_DB_URL"])
def test_database_urls_are_known_secrets(mocker, setting):
    mocker.patch.object(redaction.config, setting, "db-secret-value-123")

    assert "db-secret-value-123" in redaction.known_secrets()


@pytest.mark.parametrize(
    "text",
    [
        "Le taux d'accès à l'emploi est de 42 % sur la période.",
        '<a href="mailto:prenom.nom-de-famille@inclusion.gouv.fr">écrire</a>',
    ],
)
def test_plain_text_is_left_alone(text):

    assert redact(text) == text
    assert secret_kinds(text) == []
