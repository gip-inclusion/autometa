"""Masquage des secrets dans un texte destiné à être affiché, journalisé ou stocké."""

import re

from lib.sources import list_instances, load_config

from . import config

# Why: formes reconnaissables même quand la valeur n'est pas dans la configuration de cet environnement
# (jeton de prod lu depuis un poste local, clé d'un autre service collée dans une conversation).
PATTERNS = {
    "mot de passe de DSN": (re.compile(r"://[^/\s:@]+:[^/\s@]+@"), "://***@"),
    # Why: un extrait tronqué (« … so_3314:<mot de passe>@hôte ») perd le schéma ; un mot de passe long suffit.
    "identifiants user:mot de passe": (
        re.compile(r"\b(?!mailto:)([\w.-]+):[^\s/@:'\"]{16,}@(?=[\w-]+\.[\w.-]+)"),
        r"\1:***@",
    ),
    "paramètre d'URL sensible": (
        re.compile(r"([?&][\w-]*(?:token|key|signature|secret|pass|auth)[\w-]*=)[^&\s'\"]+", re.I),
        r"\1***",
    ),
    "jeton JWT": (re.compile(r"eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}"), "***"),
    "jeton Matomo": (re.compile(r"(token_auth\W{1,4})[0-9a-f]{32}"), r"\1***"),
    "clé autometa-jobs": (re.compile(r"pmk_[A-Za-z0-9]{16,}"), "pmk_***"),
    "jeton Bearer": (re.compile(r"(Bearer )[A-Za-z0-9._\-]{24,}"), r"\1***"),
    "jeton Notion": (re.compile(r"\b(?:ntn_[A-Za-z0-9]{20,}|secret_[A-Za-z0-9]{30,})"), "***"),
    "clé Anthropic": (re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"), "sk-ant-***"),
}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def known_secrets() -> list[str]:
    """Valeurs secrètes résolues, y compris celles de config/sources.yaml (jetons Matomo, Metabase, Zendesk)."""
    values = [
        config.NOTION_TOKEN,
        config.GRIST_API_KEY,
        config.LIVESTORM_API_KEY,
        config.SLACK_BOT_TOKEN,
        config.TALLY_API_KEY,
        config.DATADOG_API_KEY,
        config.DATADOG_APP_KEY,
        config.AUTOMETA_TABLES_DATABASE_URL,
        config.DATA_INCLUSION_DATABASE_URL,
        config.DATABASE_URL,
        config.DASHBOARD_STORAGE_DB_URL,
        config.DORA_STAGING_DB_URL,
        config.MONRECAP_APPLI_DB_URL,
    ]
    for source_type in ("matomo", "metabase", "zendesk"):
        for instance in list_instances(source_type):
            cfg = load_config().get(source_type, {}).get(instance, {})
            values += [cfg.get(key) for key in ("token", "api_key", "password", "basic_auth")]
    return [v for v in values if v and len(v) > 6 and not v.startswith("${env.")]


def secret_kinds(text: str) -> list[str]:
    """Les sortes de secrets présents en clair dans le texte."""
    kinds = [kind for kind, (rx, _) in PATTERNS.items() if any("***" not in m.group(0) for m in rx.finditer(text))]
    if any(secret in text for secret in known_secrets()):
        kinds.append("secret de configuration")
    return kinds


def redact(text: str) -> str:
    """Retire d'un texte tout ce qui pourrait être un secret."""
    for rx, replacement in PATTERNS.values():
        text = rx.sub(replacement, text)
    for secret in known_secrets():
        text = text.replace(secret, "***")
    return text
