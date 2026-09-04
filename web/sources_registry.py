"""Registre des sources de données : ce que l'application sait interroger, et comment le vérifier."""

from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Callable

from sqlalchemy import func, select

from lib.sources import list_instances, load_config

from . import config, source_checks
from .db import get_db
from .models import CronRun, MatomoBaseline, MetabaseCard

METIER = "Données métier"
WEB = "Analytiques web"
CONNECTEURS = "Connecteurs"
INTERNE = "Interne"

GROUPS = [METIER, WEB, CONNECTEURS, INTERNE]

METABASE_DOCS = {
    "stats": "skills/metabase_query/SKILL.md",
    "datalake": "knowledge/datalake/README.md",
    "dora": "knowledge/dora/README.md",
    "rdvi": "knowledge/rdvi/README.md",
}

METABASE_LABELS = {
    "stats": "Metabase Stats",
    "datalake": "Metabase Datalake",
    "dora": "Metabase Dora",
    "rdvi": "Metabase RDV-Insertion",
    "data_inclusion": "Metabase data·inclusion",
}


@dataclass(frozen=True)
class Source:
    slug: str
    name: str
    group: str
    blurb: str
    check: Callable[[], tuple[bool, str]]
    configured: Callable[[], bool]
    icon: str = "ri-database-2-line"
    skill: str | None = None
    doc: str | None = None
    inventory: Callable[[], datetime | None] | None = None


def last_column_sync(column) -> datetime | None:
    with get_db() as session:
        return session.scalar(select(func.max(column)))


def last_metabase_sync(instance: str) -> datetime | None:
    with get_db() as session:
        return session.scalar(select(func.max(MetabaseCard.synced_at)).where(MetabaseCard.instance == instance))


def last_cron_success(app_slug: str) -> datetime | None:
    with get_db() as session:
        return session.scalar(
            select(func.max(CronRun.started_at)).where(CronRun.app_slug == app_slug, CronRun.status == "success")
        )


def yaml_configured(source_type: str, instance: str, *keys: str) -> bool:
    """Vrai quand toutes les clés sont renseignées — la config non résolue garde son motif ${env.…}."""
    cfg = load_config().get(source_type, {}).get(instance, {})
    values = [str(cfg.get(key) or "") for key in keys]
    return all(value and not value.startswith("${env.") for value in values)


def metabase_sources() -> list[Source]:
    return [
        Source(
            slug=f"metabase-{instance.replace('_', '-')}",
            name=METABASE_LABELS.get(instance, f"Metabase {instance}"),
            group=METIER,
            blurb=f"Cartes et tableaux de bord de l'instance {instance}.",
            icon="ri-pie-chart-2-line",
            skill="metabase_query",
            doc=METABASE_DOCS.get(instance),
            check=partial(source_checks.check_metabase_instance, instance),
            configured=partial(yaml_configured, "metabase", instance, "api_key"),
            inventory=partial(last_metabase_sync, instance),
        )
        for instance in list_instances("metabase")
    ]


def all_sources() -> list[Source]:
    return [
        Source(
            slug="autometa-tables-db",
            doc="skills/autometa_tables_db/SKILL.md",
            name="autometa_tables_db",
            group=METIER,
            blurb=(
                "Toutes les tables des instances Metabase, centralisées en PostgreSQL. "
                "Source prioritaire : à interroger avant Metabase."
            ),
            skill="autometa_tables_db",
            check=source_checks.check_autometa_tables,
            configured=lambda: bool(config.AUTOMETA_TABLES_DATABASE_URL),
        ),
        Source(
            slug="data-inclusion",
            doc="knowledge/data_inclusion/README.md",
            name="data·inclusion (entrepôt)",
            group=METIER,
            blurb="Entrepôt dbt des structures et services d'insertion, par tunnel SSH.",
            skill="data_inclusion",
            check=source_checks.check_data_inclusion,
            configured=lambda: bool(config.DATA_INCLUSION_DATABASE_URL),
        ),
        *metabase_sources(),
        Source(
            slug="rpe",
            doc="skills/rpe/SKILL.md",
            name="RPE (France Travail)",
            group=METIER,
            blurb=(
                "Indicateurs agrégés du Réseau pour l'emploi : emploi, formation, recrutement, RSA, "
                "par territoire et par mois. Tout le réseau, pas seulement nos services."
            ),
            icon="ri-government-line",
            skill="rpe",
            check=source_checks.check_rpe,
            configured=lambda: bool(config.RPE_PUBLIC_PASS),
            inventory=partial(last_cron_success, "refresh-rpe"),
        ),
        Source(
            slug="matomo",
            doc="knowledge/matomo/README.md",
            name="Matomo",
            group=WEB,
            blurb="Comportement des visiteurs sur les huit sites : visites, événements, parcours.",
            icon="ri-line-chart-line",
            skill="matomo_query",
            check=source_checks.check_matomo,
            configured=partial(yaml_configured, "matomo", "inclusion", "token"),
            inventory=partial(last_column_sync, MatomoBaseline.synced_at),
        ),
        Source(
            slug="tag-manager",
            doc="knowledge/matomo/tag-manager.md",
            name="Matomo Tag Manager",
            group=WEB,
            blurb="Conteneurs, déclencheurs et balises de suivi des sites.",
            icon="ri-price-tag-3-line",
            skill="tag_manager",
            check=source_checks.check_matomo,
            configured=partial(yaml_configured, "matomo", "inclusion", "token"),
        ),
        Source(
            slug="notion",
            doc="knowledge/notion/_index.md",
            name="Notion",
            group=CONNECTEURS,
            blurb="Espaces de travail partagés avec l'intégration : bases, pages, vocabulaire de tags.",
            icon="ri-booklet-line",
            skill="notion",
            check=source_checks.check_notion,
            configured=lambda: bool(config.NOTION_TOKEN),
        ),
        Source(
            slug="datadog",
            doc="skills/datadog_logs/SKILL.md",
            name="Datadog Logs",
            group=CONNECTEURS,
            blurb=(
                "Logs applicatifs des services en production : URL réellement appelées, "
                "paramètres de filtre, vues Django, utilisateur connecté. Rétention 30 jours."
            ),
            icon="ri-file-list-3-line",
            skill="datadog_logs",
            check=source_checks.check_datadog,
            configured=lambda: bool(config.DATADOG_API_KEY and config.DATADOG_APP_KEY),
        ),
        Source(
            slug="tally",
            name="Tally",
            group=CONNECTEURS,
            blurb="Formulaires et réponses collectées auprès des utilisateurs.",
            icon="ri-survey-line",
            skill="tally",
            check=source_checks.check_tally,
            configured=lambda: bool(config.TALLY_API_KEY),
        ),
        Source(
            slug="grist",
            doc="knowledge/webinaires/_index.md",
            name="Grist",
            group=CONNECTEURS,
            blurb="Tableur collaboratif — inscriptions et participation aux webinaires.",
            icon="ri-table-line",
            check=source_checks.check_grist,
            configured=lambda: bool(config.GRIST_API_KEY and config.GRIST_WEBINAIRES_DOC_ID),
            inventory=partial(last_cron_success, "sync-webinaires"),
        ),
        Source(
            slug="livestorm",
            doc="knowledge/webinaires/_index.md",
            name="Livestorm",
            group=CONNECTEURS,
            blurb="Historique de participation aux webinaires, avant la bascule vers Grist.",
            icon="ri-live-line",
            check=source_checks.check_livestorm,
            configured=lambda: bool(config.LIVESTORM_API_KEY),
        ),
        Source(
            slug="zendesk",
            doc="skills/zendesk_query/SKILL.md",
            name="Zendesk",
            group=CONNECTEURS,
            blurb="Tickets et échanges du support des Emplois de l'inclusion.",
            icon="ri-customer-service-2-line",
            skill="zendesk_query",
            check=source_checks.check_zendesk,
            configured=partial(yaml_configured, "zendesk", "emplois", "subdomain", "email", "token"),
        ),
        Source(
            slug="slack",
            name="Slack",
            group=CONNECTEURS,
            blurb="Canaux d'alerte et de retour d'usage de l'application.",
            icon="ri-slack-line",
            check=source_checks.check_slack,
            configured=lambda: bool(config.SLACK_BOT_TOKEN),
        ),
        Source(
            slug="db-applicative",
            name="Base applicative",
            group=INTERNE,
            blurb=(
                "Conversations, rapports, tableaux de bord, et les miroirs synchronisés "
                "des sites Matomo et des cartes Metabase."
            ),
            icon="ri-server-line",
            check=source_checks.check_app_db,
            configured=lambda: bool(config.DATABASE_URL),
        ),
        Source(
            slug="dashboard-storage",
            doc="docs/interactive-dashboards.md",
            name="dashboard_storage",
            group=INTERNE,
            blurb="Schéma où les tableaux de bord et les skills déposent leurs propres données.",
            icon="ri-archive-line",
            check=source_checks.check_dashboard_storage,
            configured=lambda: bool(config.DASHBOARD_STORAGE_DB_URL),
        ),
        Source(
            slug="s3",
            name="S3",
            group=INTERNE,
            blurb="Fichiers des tableaux de bord, pièces jointes, sauvegardes.",
            icon="ri-hard-drive-2-line",
            check=source_checks.check_s3,
            configured=lambda: bool(config.S3_BUCKET),
        ),
    ]


def check_source(source: Source) -> tuple[bool, str]:
    if not source.configured():
        return (False, "non configuré dans cet environnement")
    return source.check()


def find_source(slug: str) -> Source | None:
    return next((s for s in all_sources() if s.slug == slug), None)


def grouped_sources() -> dict[str, list[Source]]:
    sources = all_sources()
    return {group: [s for s in sources if s.group == group] for group in GROUPS}
