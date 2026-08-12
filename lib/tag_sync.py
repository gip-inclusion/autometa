"""Synchronisation du vocabulaire de tags depuis Notion — sens unique, Notion fait foi."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import delete, func, select

from lib import notion
from lib.taxonomy import FACETS_BY_NAME, normalize_tag_name
from web import config
from web.db import get_db
from web.models import ConversationTag, DashboardTag, ReportTag, Tag, TagImplication, TagSyncState

logger = logging.getLogger(__name__)

# Why: garde-fou — un fetch vide ou tronqué (auth expirée, pagination cassée) ne doit
# jamais vider le vocabulaire. En dessous de ce ratio on refuse d'appliquer.
MIN_RETAINED_RATIO = 0.8


@dataclass
class SyncResult:
    created: int = 0
    updated: int = 0
    deactivated: int = 0
    deleted: int = 0
    implications: int = 0
    rejected: list[str] = field(default_factory=list)
    applied: bool = False
    error: str | None = None

    @property
    def status(self) -> str:
        return "ok" if self.applied and not self.rejected else ("partial" if self.applied else "refused")


@dataclass(frozen=True)
class NotionTerm:
    page_id: str
    name: str
    label: str
    facet: str
    description: str | None
    active: bool
    implies_page_ids: tuple[str, ...]


def parse_row(page: dict) -> tuple[NotionTerm | None, str | None]:
    """Convertit une ligne Notion en terme, ou retourne un motif de rejet."""
    props = notion.extract_page_properties(page)
    raw_slug = (props.get("Slug") or "").strip()
    if not raw_slug:
        return None, f"{page['id']}: slug vide"

    name = normalize_tag_name(raw_slug)
    if not name:
        return None, f"{raw_slug}: slug vide après normalisation"

    facet = props.get("Facette")
    if facet not in FACETS_BY_NAME:
        return None, f"{name}: facette inconnue ({facet!r})"

    return (
        NotionTerm(
            page_id=page["id"],
            name=name,
            label=(props.get("Libellé") or "").strip() or name,
            facet=facet,
            description=(props.get("Description") or "").strip() or None,
            active=bool(props.get("Actif")),
            implies_page_ids=tuple(props.get("Implique") or ()),
        ),
        None,
    )


def fetch_terms() -> tuple[list[NotionTerm], list[str]]:
    pages = notion.query_database(notion.db_id_from_url(config.NOTION_TAGS_DB))
    terms, rejected = [], []
    seen: dict[str, str] = {}
    for page in pages:
        term, reason = parse_row(page)
        if reason:
            rejected.append(reason)
            continue
        if term.name in seen:
            rejected.append(f"{term.name}: doublon de slug")
            continue
        seen[term.name] = term.page_id
        terms.append(term)
    return terms, rejected


def assigned_tag_ids(session) -> set[int]:
    """Ids de tags portés par au moins un objet — jamais supprimés, seulement désactivés."""
    ids = set()
    for model in (DashboardTag, ConversationTag, ReportTag):
        ids.update(session.scalars(select(model.tag_id).distinct()))
    return ids


def sync_tags(*, dry_run: bool = False) -> SyncResult:
    """Applique le vocabulaire Notion en base. Ne supprime jamais un tag encore assigné."""
    if not config.NOTION_TAGS_DB or not config.NOTION_TOKEN:
        return SyncResult(error="NOTION_TAGS_DB ou NOTION_TOKEN absent")

    try:
        terms, rejected = fetch_terms()
    except Exception as exc:  # Why: le cron ne doit pas mourir sur une panne Notion; on trace l'état.
        logger.exception("tag-sync: fetch Notion échoué")
        _record_state(status="error", error=str(exc), term_count=None)
        return SyncResult(error=str(exc))

    result = SyncResult(rejected=rejected)

    with get_db() as session:
        known = {t.notion_page_id: t for t in session.scalars(select(Tag)) if t.notion_page_id}
        existing_count = session.scalar(select(func.count()).select_from(Tag).where(Tag.notion_page_id.is_not(None)))

        if not terms:
            result.error = "fetch vide — vocabulaire inchangé"
        elif existing_count and len(terms) < existing_count * MIN_RETAINED_RATIO:
            result.error = f"fetch suspect ({len(terms)} termes contre {existing_count} en base) — vocabulaire inchangé"

        if result.error:
            logger.error("tag-sync refusé: %s", result.error)
            if not dry_run:
                _record_state(status="refused", error=result.error, term_count=existing_count, session=session)
            return result

        # Why: SAVEPOINT plutôt que rollback() — annuler la transaction entière emporterait
        # aussi ce que l'appelant avait déjà écrit (et, en test, toute la transaction partagée).
        nested = session.begin_nested()
        by_page_id = _apply_terms(session, terms, known, result)
        _apply_deactivations(session, terms, known, result)
        result.implications = _apply_implications(session, terms, by_page_id)

        if dry_run:
            nested.rollback()
        else:
            nested.commit()
            result.applied = True
            _record_state(
                status=result.status, error="; ".join(rejected) or None, term_count=len(terms), session=session
            )

    logger.info(
        "tag-sync: created=%d updated=%d deactivated=%d deleted=%d rejected=%d dry_run=%s",
        result.created,
        result.updated,
        result.deactivated,
        result.deleted,
        len(result.rejected),
        dry_run,
    )
    return result


def _apply_terms(session, terms, known, result) -> dict[str, int]:
    by_page_id: dict[str, int] = {}
    for term in terms:
        # Why: n'adopter par nom qu'une ligne orpheline — sinon on volerait la ligne d'une autre
        # page Notion (collision de slug lors d'un renommage) et on écraserait son notion_page_id.
        tag = known.get(term.page_id) or session.scalar(
            select(Tag).where(Tag.name == term.name, Tag.notion_page_id.is_(None))
        )
        if tag is None:
            tag = Tag(name=term.name, type=term.facet, label=term.label)
            session.add(tag)
            result.created += 1
        elif (tag.name, tag.type, tag.label, tag.description, tag.active) != (
            term.name,
            term.facet,
            term.label,
            term.description,
            term.active,
        ):
            result.updated += 1
        tag.name, tag.type, tag.label = term.name, term.facet, term.label
        tag.description, tag.active, tag.notion_page_id = term.description, term.active, term.page_id
        # Why: promotion — un terme proposé dans l'app cesse d'être « pending » dès que Notion l'adopte.
        tag.pending = False
        session.flush()
        by_page_id[term.page_id] = tag.id
    return by_page_id


def _apply_deactivations(session, terms, known, result) -> None:
    """Une ligne disparue de Notion est désactivée si elle est assignée, supprimée sinon."""
    live_page_ids = {t.page_id for t in terms}
    assigned = assigned_tag_ids(session)
    for page_id, tag in known.items():
        if page_id in live_page_ids:
            continue
        if tag.id in assigned:
            if tag.active:
                tag.active = False
                result.deactivated += 1
        else:
            session.delete(tag)
            result.deleted += 1


def _apply_implications(session, terms, by_page_id) -> int:
    session.execute(delete(TagImplication).where(TagImplication.tag_id.in_(by_page_id.values())))
    count = 0
    for term in terms:
        tag_id = by_page_id[term.page_id]
        for target_page_id in term.implies_page_ids:
            target_id = by_page_id.get(target_page_id)
            if target_id and target_id != tag_id:
                session.add(TagImplication(tag_id=tag_id, implies_tag_id=target_id))
                count += 1
    session.flush()
    return count


def _record_state(*, status, error, term_count, session=None) -> None:
    def write(s):
        state = s.scalar(select(TagSyncState)) or TagSyncState()
        state.last_synced_at = datetime.now(timezone.utc)
        state.last_status = status
        state.last_error = (error or "")[:2000] or None
        if term_count is not None:
            state.term_count = term_count
        s.add(state)

    if session is not None:
        write(session)
    else:
        with get_db() as own:
            write(own)


def pending_terms() -> list[dict]:
    """Termes proposés depuis l'app, en attente de promotion dans Notion."""
    with get_db() as session:
        rows = session.execute(
            select(Tag.name, Tag.type, Tag.label, func.count(DashboardTag.dashboard_slug))
            .outerjoin(DashboardTag, DashboardTag.tag_id == Tag.id)
            .where(Tag.pending, Tag.active)
            .group_by(Tag.id)
            .order_by(Tag.type, Tag.label)
        ).all()
    return [{"name": name, "facet": facet, "label": label, "usages": usages} for name, facet, label, usages in rows]


def purge_legacy_tags(*, dry_run: bool = True) -> dict:
    """Supprime les tags hérités (hors Notion) et leurs assignations. Étape finale, après relecture."""
    with get_db() as session:
        # Why: un terme proposé depuis l'app n'a pas non plus de notion_page_id — il attend sa
        # promotion, ce n'est pas de l'hérité, et le purger détruirait aussi ses assignations.
        legacy = list(session.scalars(select(Tag).where(Tag.notion_page_id.is_(None), ~Tag.pending)))
        assigned = assigned_tag_ids(session)
        report = {
            "count": len(legacy),
            "with_assignments": sum(1 for t in legacy if t.id in assigned),
            "names": sorted(t.name for t in legacy),
            "dry_run": dry_run,
        }
        if not dry_run:
            for tag in legacy:
                session.delete(tag)
        logger.warning("purge-legacy-tags: %d tags, dry_run=%s", len(legacy), dry_run)
        return report


def sync_state() -> dict:
    """État de la dernière synchro, pour le selftest."""
    with get_db() as session:
        state = session.scalar(select(TagSyncState))
        if state is None:
            return {"configured": bool(config.NOTION_TAGS_DB), "last_synced_at": None, "status": "never"}
        return {
            "configured": bool(config.NOTION_TAGS_DB),
            "last_synced_at": state.last_synced_at.isoformat() if state.last_synced_at else None,
            "status": state.last_status,
            "error": state.last_error,
            "term_count": state.term_count,
        }
