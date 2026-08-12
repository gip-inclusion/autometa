"""Passe de taguage automatique : propose, applique, et garde la trace de ce qui a été proposé."""

import csv
import io
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from web import config, llm
from web.db import get_db, get_engine
from web.llm_errors import LLMError
from web.models import Conversation, Dashboard, Message, Report

from . import job_inputs
from .taxonomy import build_prompt_taxonomy, load_vocabulary, normalize_tags

logger = logging.getLogger(__name__)

SCHEMA = "dashboard_storage"

_metadata = MetaData(schema=SCHEMA)
tag_suggestions = Table(
    "tag_suggestions",
    _metadata,
    Column("object_type", String, primary_key=True),
    Column("object_id", String, primary_key=True),
    Column("title", String),
    Column("current_tags", JSON),
    Column("suggested_tags", JSON),
    Column("model", String),
    Column("suggested_at", DateTime(timezone=True)),
)


def ensure_schema() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS " + SCHEMA))
    _metadata.create_all(engine)


@dataclass
class Subject:
    object_type: str
    object_id: str
    title: str
    body: str
    current_tags: list[str]


def dashboard_subjects(session, limit: int | None = None, exclude_ids: frozenset = frozenset()) -> list[Subject]:
    from web.stores.dashboards import serialize_dashboards

    stmt = select(Dashboard).where(~Dashboard.is_archived)
    if exclude_ids:
        stmt = stmt.where(Dashboard.slug.not_in(exclude_ids))
    stmt = stmt.order_by(Dashboard.updated_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    subjects = []
    for d in serialize_dashboards(session, list(session.scalars(stmt))):
        body = f"Titre : {d['title']}\nDescription : {d['description']}\nSite : {d['website'] or 'non précisé'}"
        subjects.append(Subject("dashboard", d["slug"], d["title"], body, d["tags"]))
    return subjects


def conversation_subjects(session, limit: int | None = None, exclude_ids: frozenset = frozenset()) -> list[Subject]:
    stmt = select(Conversation)
    if exclude_ids:
        stmt = stmt.where(Conversation.id.not_in(exclude_ids))
    stmt = stmt.order_by(Conversation.updated_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    conversations = list(session.scalars(stmt))

    # Why: un seul aller-retour pour les premiers messages du lot, au lieu d'une requête par conversation.
    first_messages: dict[str, str] = {}
    ids = [c.id for c in conversations]
    if ids:
        rows = session.execute(
            select(Message.conversation_id, Message.content)
            .where(Message.conversation_id.in_(ids), Message.role == "user")
            .order_by(Message.conversation_id, Message.id)
        ).all()
        for conv_id, content in rows:
            first_messages.setdefault(conv_id, content)

    subjects = []
    for conv in conversations:
        first = first_messages.get(conv.id)
        if not first:
            continue
        subjects.append(Subject("conversation", conv.id, conv.title or "", f"Demande : {first[:1500]}", []))
    return subjects


def report_subjects(session, limit: int | None = None, exclude_ids: frozenset = frozenset()) -> list[Subject]:
    stmt = select(Report).where((Report.archived == 0) | (Report.archived.is_(None)))
    # Why: object_id est du texte pour tous les types — une ligne non numérique ne doit pas
    # faire tomber la passe entière, on l'ignore simplement.
    numeric = [int(i) for i in exclude_ids if str(i).isdigit()]
    if numeric:
        stmt = stmt.where(Report.id.not_in(numeric))
    stmt = stmt.order_by(Report.updated_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    subjects = []
    for report in session.scalars(stmt):
        body = f"Titre : {report.title}\nExtrait : {(report.content or '')[:1500]}"
        subjects.append(Subject("report", str(report.id), report.title or "", body, []))
    return subjects


COLLECTORS = {
    "dashboard": dashboard_subjects,
    "conversation": conversation_subjects,
    "report": report_subjects,
}


def build_prompt(taxonomy: str, subject: Subject) -> str:
    return f"""Attribue des tags à cet objet, en piochant UNIQUEMENT dans le vocabulaire ci-dessous.

{taxonomy}

Règles :
- N'invente aucun tag : seuls les identifiants listés sont valides.
- Respecte les cardinalités indiquées pour chaque facette.
- Si l'objet porte sur Autometa lui-même, réponds `meta` et rien d'autre n'est obligatoire.
- Dans le doute sur une facette, ne mets rien pour cette facette.

Objet à taguer :
{subject.body}

Réponds UNIQUEMENT avec les identifiants séparés par des virgules, rien d'autre."""


def parse_response(response: str, valid: set[str]) -> list[str]:
    candidates = normalize_tags(response.replace("\n", ",").split(","))
    return [c for c in candidates if c in valid]


def suggest_for(subject: Subject, taxonomy: str, valid: set[str], model: str) -> list[str] | None:
    try:
        response = llm.generate_text(build_prompt(taxonomy, subject), model=model, max_tokens=120)
    except LLMError:
        logger.warning("tag-suggestions: échec LLM sur %s/%s", subject.object_type, subject.object_id)
        return None
    return parse_response(response, valid)


AUTO_TAGGER = "tagueur-automatique@autometa"


def apply_tags(object_type: str, object_id: str, names: list[str]) -> bool:
    """Pose les tags sur l'objet. Retourne False si l'objet a disparu ou refuse un terme."""
    from lib.dashboards import DashboardNotFound, UnknownTag, update_dashboard
    from web.database import store

    try:
        if object_type == "dashboard":
            update_dashboard(slug=object_id, updater_email=AUTO_TAGGER, set_tags=names, bump_updated_at=False)
        elif object_type == "conversation":
            store.set_conversation_tags(object_id, names, update_timestamp=False)
        elif object_type == "report":
            store.set_report_tags(int(object_id), names, update_timestamp=False)
        else:
            return False
    except DashboardNotFound, UnknownTag, ValueError:
        logger.warning("tag-suggestions: application impossible sur %s/%s", object_type, object_id)
        return False
    return True


def export_for_job(object_types: tuple[str, ...] = ("dashboard", "report", "conversation"), only_missing: bool = True):
    """Publie les objets à taguer comme jeu de données téléchargeable par un worker autometa-jobs."""
    rows = []
    for object_type in object_types:
        if object_type not in COLLECTORS:
            raise ValueError(f"Type inconnu : {object_type}")
        done = already_suggested(object_type) if only_missing else frozenset()
        with get_db() as session:
            for subject in COLLECTORS[object_type](session, None, done):
                rows.append([subject.object_type, subject.object_id, subject.title, subject.body])

    published = job_inputs.publish_dataset(
        "tag-suggestions-input", ["object_type", "object_id", "title", "body"], rows, fmt="sqlite"
    )
    with get_db() as session:
        vocabulary = load_vocabulary(session, include_pending=False)
    return {**published, "taxonomy": build_prompt_taxonomy(vocabulary)}


def ingest_job_output(csv_text: str, model: str = "autometa-jobs", apply: bool = True) -> dict:
    """Réinjecte l'artefact CSV d'un job (object_type,object_id,tags) après filtrage sur le vocabulaire."""
    ensure_schema()
    with get_db() as session:
        vocabulary = load_vocabulary(session, include_pending=False)
    valid = {term.name for terms in vocabulary.values() for term in terms}

    ingested = rejected = not_applied = 0
    engine = get_engine()
    for row in csv.DictReader(io.StringIO(csv_text.strip())):
        object_type = (row.get("object_type") or "").strip()
        object_id = (row.get("object_id") or "").strip()
        if object_type not in COLLECTORS or not object_id:
            rejected += 1
            continue
        # Why: un worker peut inventer des termes comme n'importe quel modèle — on refiltre à l'entrée.
        suggested = parse_response((row.get("tags") or "").replace(";", ","), valid)
        payload = {
            "object_type": object_type,
            "object_id": object_id,
            "title": (row.get("title") or "")[:500],
            "current_tags": [],
            "suggested_tags": suggested,
            "model": model,
            "suggested_at": datetime.now(timezone.utc),
        }
        statement = pg_insert(tag_suggestions).values(**payload)
        with engine.begin() as conn:
            conn.execute(
                statement.on_conflict_do_update(
                    index_elements=["object_type", "object_id"],
                    set_={k: statement.excluded[k] for k in payload if k not in ("object_type", "object_id")},
                )
            )
        ingested += 1
        if apply and not apply_tags(object_type, object_id, suggested):
            not_applied += 1

    logger.info(
        "tag-suggestions: ingestion job ingested=%d rejected=%d non_appliques=%d", ingested, rejected, not_applied
    )
    return {"ingested": ingested, "rejected": rejected, "not_applied": not_applied}


def already_suggested(object_type: str) -> set[str]:
    with get_engine().begin() as conn:
        return set(
            conn.scalars(select(tag_suggestions.c.object_id).where(tag_suggestions.c.object_type == object_type))
        )


def run(
    object_type: str = "dashboard",
    limit: int | None = None,
    model: str | None = None,
    only_missing: bool = True,
    time_budget_s: float | None = None,
    apply: bool = True,
) -> dict:
    """Tague les objets et garde la trace de ce qui a été proposé dans dashboard_storage."""
    if object_type not in COLLECTORS:
        raise ValueError(f"Type inconnu : {object_type}")

    ensure_schema()
    model = model or config.LLM_MODEL
    started = time.monotonic()
    # Why: l'exclusion se fait en SQL avant le LIMIT — sinon le lot serait toujours rempli par
    # les objets déjà traités et on ne progresserait jamais dans le corpus.
    done = already_suggested(object_type) if only_missing else frozenset()

    with get_db() as session:
        # Why: les termes proposés depuis l'app ne guident pas le tagueur tant qu'un humain
        # ne les a pas promus dans Notion — sinon une proposition isolée se propage au corpus.
        vocabulary = load_vocabulary(session, include_pending=False)
        subjects = COLLECTORS[object_type](session, limit, done)

    if not vocabulary:
        return {"error": "vocabulaire vide — lancer la synchro Notion d'abord", "processed": 0}

    taxonomy = build_prompt_taxonomy(vocabulary)
    valid = {term.name for terms in vocabulary.values() for term in terms}

    processed = failed = not_applied = 0
    remaining = 0
    engine = get_engine()
    for index, subject in enumerate(subjects):
        if time_budget_s is not None and time.monotonic() - started > time_budget_s:
            remaining = len(subjects) - index
            logger.warning("tag-suggestions: budget épuisé, %d sujet(s) reportés", remaining)
            break
        suggested = suggest_for(subject, taxonomy, valid, model)
        if suggested is None:
            failed += 1
            continue
        row = {
            "object_type": subject.object_type,
            "object_id": subject.object_id,
            "title": subject.title[:500],
            "current_tags": subject.current_tags,
            "suggested_tags": suggested,
            "model": model,
            "suggested_at": datetime.now(timezone.utc),
        }
        statement = pg_insert(tag_suggestions).values(**row)
        with engine.begin() as conn:
            conn.execute(
                statement.on_conflict_do_update(
                    index_elements=["object_type", "object_id"],
                    set_={k: statement.excluded[k] for k in row if k not in ("object_type", "object_id")},
                )
            )
        processed += 1
        if apply and not apply_tags(subject.object_type, subject.object_id, suggested):
            not_applied += 1

    logger.info(
        "tag-suggestions: type=%s processed=%d failed=%d deferred=%d non_appliques=%d model=%s",
        object_type,
        processed,
        failed,
        remaining,
        not_applied,
        model,
    )
    return {
        "object_type": object_type,
        "processed": processed,
        "failed": failed,
        "deferred": remaining,
        "not_applied": not_applied,
        "model": model,
    }
