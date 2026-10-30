"""Masquage des secrets — web/redaction.py."""

import json

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
        (
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012",
            "abcdefghijklmnopqrstuvwxyz012",
            "en-tête d'autorisation",
        ),
        ("Authorization: Basic dXNlcjpwYXNzd29yZDEyMzQ=", "dXNlcjpwYXNzd29yZDEyMzQ=", "en-tête d'autorisation"),
        ("NOTION_TOKEN=ntn_abcdefghijklmnopqrstuv", "ntn_abcdefghijklmnopqrstuv", "jeton Notion"),
        ("cle sk-ant-api03-abcdefghijklmnopqrst", "abcdefghijklmnopqrst", "clé Anthropic"),
        # Tally signe ses liens de prévisualisation : le jeton est dans un paramètre dont le nom ne commence pas par token.
        (f"https://tally.so/forms/x/preview?accessToken={FAUX}&lang=fr", FAUX, "paramètre d'URL sensible"),
        (f"https://api.tally.so/x/pdf?a=1&signature={FAUX}", FAUX, "paramètre d'URL sensible"),
        ("jeton eyJhbGciOiJIUzI1.eyJzdWJtaXNzaW9u.c2lnbmF0dXJlMTIz collé", "eyJzdWJtaXNzaW9u", "jeton JWT"),
        (
            "extrait … so_3314:Sup3rLongPassw0rdXYZ@base-so-3314.postgresql.example.com:36000",
            "Sup3rLongPassw0rdXYZ",
            "identifiants user:mot de passe",
        ),
        ("redis://:p4ssw0rdXYZ@cache:6379", "p4ssw0rdXYZ", "mot de passe de DSN"),
        # Un `env` de prod : des valeurs absentes de la configuration du poste qui audite.
        ("SLACK_BOT_TOKEN=xoxb-1234567890-abcdefghij", "1234567890-abcdefghij", "variable secrète"),
        ("S3_SECRET_KEY=3f2a9c1e-7b6d-4e8f-9a0b-1c2d3e4f5a6b", "3f2a9c1e-7b6d", "variable secrète"),
        ("PGPASSWORD=supers3cret99", "supers3cret99", "variable secrète"),
        ('"password": "motdepasse-tres-secret"', "motdepasse-tres-secret", "champ secret"),
        ("x-api-key: abc123def456ghi", "abc123def456ghi", "champ secret"),
        ("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345", "ABCDEFGHIJKLMNOPQRST", "jeton de service"),
        ("cle mb_AbCdEf0123456789XyZaBcD=", "AbCdEf0123456789XyZaBcD", "jeton de service"),
    ],
)
def test_redact_removes_each_family_of_secret(text, secret, kind):
    assert secret not in redact(text)
    assert kind in secret_kinds(text)


def test_masking_escaped_json_keeps_it_valid():
    raw = json.dumps({"output": 'conf = {"password": "s3cretValue99", "url": "https://a/?api_key=abc123def"}'})

    assert json.loads(redact(raw))["output"] == 'conf = {"password": "***", "url": "https://a/?api_key=***"}'


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
        # Ressemblent à des secrets sans en être : chacune déclencherait un incident CRITIQUE et une alerte.
        "requester:jean-baptiste.dupont@orange.fr",
        "MAILTO:prenom.nom-de-famille@inclusion.gouv.fr",
        "postgresql://USER:PASSWORD@HOST/DB",
        "mysql://root:${DB_PASSWORD}@db/x",
        "https://host:8080?email=a@b.fr",
        "https://x/?author=dupont&keyword=emploi&passage=2",
        'SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")',
        '"password": "<mot de passe>"',
        "le password: est requis",
    ],
)
def test_plain_text_is_left_alone(text):
    assert redact(text) == text
    assert secret_kinds(text) == []
