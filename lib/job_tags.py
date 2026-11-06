"""Tags des pipelines de jobs, sur le vocabulaire commun — le service de jobs ne stocke aucune métadonnée."""

from sqlalchemy import delete, select

from lib.taxonomy import apply_toggle, load_vocabulary, normalize_tag_name, ordered_facets
from web.db import get_db
from web.models import JobTag, Tag
from web.stores.records import Tag as TagRecord
from web.stores.records import model_to_tag
from web.stores.tags import matching_keys

__all__ = ["editor_context", "pipelines_with_tags", "propose_term", "tags_by_pipeline", "toggle_tag"]


def tags_by_pipeline(pipeline_ids: list[str]) -> dict[str, list[TagRecord]]:
    result: dict[str, list[TagRecord]] = {pid: [] for pid in pipeline_ids}
    with get_db() as session:
        rows = session.execute(
            select(JobTag.pipeline_id, Tag)
            .join(Tag, Tag.id == JobTag.tag_id)
            .where(JobTag.pipeline_id.in_(pipeline_ids))
            .order_by(Tag.label)
        ).all()
        for pipeline_id, tag in rows:
            result[pipeline_id].append(model_to_tag(tag))
    return result


def pipelines_with_tags(tag_names: list[str]) -> set[str]:
    """Pipelines portant tous les tags demandés, implications comprises."""
    with get_db() as session:
        return matching_keys(session, JobTag, JobTag.pipeline_id, tag_names)


def toggle_tag(pipeline_id: str, name: str) -> bool:
    """Coche un terme actif ou décoche un terme posé ; False pour un terme ni actif ni posé."""
    with get_db() as session:
        facet_of = dict(session.execute(select(Tag.name, Tag.type).where(Tag.active)).all())
        current = list(
            session.scalars(
                select(Tag.name).join(JobTag, JobTag.tag_id == Tag.id).where(JobTag.pipeline_id == pipeline_id)
            )
        )
        # Why: un terme désactivé par la synchro Notion reste posé ; il doit pouvoir être retiré.
        if name not in facet_of and name not in current:
            return False
        target = apply_toggle(current, name, facet_of)
        session.execute(delete(JobTag).where(JobTag.pipeline_id == pipeline_id))
        session.add_all(
            JobTag(pipeline_id=pipeline_id, tag_id=tag_id)
            for tag_id in session.scalars(select(Tag.id).where(Tag.name.in_(target)))
        )
    return True


def propose_term(pipeline_id: str, label: str) -> str | None:
    """Crée au besoin un terme proposé de la facette Nature et le pose ; renvoie le motif d'un refus."""
    name = normalize_tag_name(label)
    if not name:
        return "Libellé vide"
    with get_db() as session:
        tag = session.scalar(select(Tag).where(Tag.name == name))
        if tag is None:
            tag = Tag(name=name, type="nature", label=label, active=True, pending=True)
            session.add(tag)
            session.flush()
        elif not tag.active:
            return f"Terme désactivé : {name}"
        session.merge(JobTag(pipeline_id=pipeline_id, tag_id=tag.id))
    return None


def editor_context(pipeline_id: str) -> dict:
    """Tags du pipeline et vocabulaire actif des facettes offertes aux jobs, terme posé exclu."""
    current = tags_by_pipeline([pipeline_id])[pipeline_id]
    names = {t.name for t in current}
    with get_db() as session:
        vocabulary = load_vocabulary(session)
    groups = [
        {"label": facet.label, "terms": [t for t in vocabulary.get(facet.name, []) if t.name not in names]}
        for facet in ordered_facets("job")
    ]
    return {"pipeline_id": pipeline_id, "job_tags": current, "tag_groups": [g for g in groups if g["terms"]]}
