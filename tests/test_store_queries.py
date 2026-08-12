"""Tests for ConversationStore list/aggregation queries."""

import pytest
from sqlalchemy import select

from web.database import store
from web.db import get_db
from web.models import Report as ReportModel
from web.models import Tag as TagModel

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("_db")]

ALICE = "alice@example.com"
BOB = "bob@example.com"


def ensure_tag(name, tag_type="product"):
    with get_db() as session:
        if not session.scalars(select(TagModel).where(TagModel.name == name)).first():
            session.add(TagModel(name=name, type=tag_type, label=name))


def make_conv(user_id=ALICE, tags=None, conv_type="exploration"):
    conv = store.create_conversation(user_id=user_id, conv_type=conv_type)
    for name in tags or []:
        ensure_tag(name)
    if tags:
        store.set_conversation_tags(conv.id, tags)
    return conv


def make_report(title="rapport", tags=None, archived=False, conversation_id=None):
    report = store.create_report(title=title, content="contenu")
    with get_db() as session:
        model = session.get(ReportModel, report.id)
        model.archived = int(archived)
        model.conversation_id = conversation_id
    for name in tags or []:
        ensure_tag(name)
    if tags:
        store.set_report_tags(report.id, tags)
    return report


def test_list_conversations_filters_by_user(client):
    own = make_conv(ALICE)
    other = make_conv(BOB)

    ids = [c.id for c in store.list_conversations(user_id=ALICE)]

    assert own.id in ids
    assert other.id not in ids


def test_list_conversations_excludes_report_containers_by_default(client):
    plain = make_conv()
    container = make_conv()
    make_report(title="lié", conversation_id=container.id)

    default_ids = [c.id for c in store.list_conversations()]
    all_convs = store.list_conversations(exclude_report_containers=False)

    assert plain.id in default_ids
    assert container.id not in default_ids
    with_report = {c.id: c for c in all_convs}[container.id]
    assert with_report.report.title == "lié"


def test_list_conversations_filters_conv_type(client):
    exploration = make_conv()
    knowledge = make_conv(conv_type="knowledge")

    default_ids = [c.id for c in store.list_conversations()]
    knowledge_ids = [c.id for c in store.list_conversations(conv_type="knowledge")]

    assert exploration.id in default_ids
    assert knowledge.id not in default_ids
    assert knowledge_ids == [knowledge.id]


def test_list_conversations_with_tags_requires_all_tags(client):
    both = make_conv(tags=["emplois", "trafic"])
    make_conv(tags=["emplois"])

    results = store.list_conversations_with_tags(tag_names=["emplois", "trafic"])

    assert [conv.id for conv, _ in results] == [both.id]
    assert sorted(t.name for t in results[0][1]) == ["emplois", "trafic"]
    assert results[0][0].report is None


def _implication(source, target, facet="audience"):
    """Crée deux termes et fait impliquer le second par le premier."""
    from sqlalchemy import select

    from web.db import get_db
    from web.models import Tag, TagImplication

    with get_db() as session:
        ids = {}
        for name in (source, target):
            tag = session.scalar(select(Tag).where(Tag.name == name))
            if tag is None:
                tag = Tag(name=name, type=facet, label=name, active=True)
                session.add(tag)
                session.flush()
            ids[name] = tag.id
        session.add(TagImplication(tag_id=ids[source], implies_tag_id=ids[target]))
        session.flush()


def test_conversation_filter_expands_implications(client):
    _implication("siae", "solutions-structurees")
    precise = make_conv(tags=["siae"])

    results = store.list_conversations_with_tags(tag_names=["solutions-structurees"])

    assert [conv.id for conv, _ in results] == [precise.id]


def test_conversation_filter_does_not_expand_in_reverse(client):
    _implication("siae", "solutions-structurees")
    make_conv(tags=["solutions-structurees"])

    assert store.list_conversations_with_tags(tag_names=["siae"]) == []


def test_report_filter_expands_implications(client):
    _implication("siae", "solutions-structurees")
    make_report(title="précis", tags=["siae"])

    results = store.list_reports_with_tags(tag_names=["solutions-structurees"])

    assert [r.title for r, _ in results] == ["précis"]


def test_list_reports_with_tags_filters_archived_and_tags(client):
    tagged = make_report(title="actif", tags=["emplois"])
    make_report(title="archivé", tags=["emplois"], archived=True)
    make_report(title="sans-tag")

    default = store.list_reports_with_tags(tag_names=["emplois"])
    with_archived = store.list_reports_with_tags(tag_names=["emplois"], include_archived=True)

    assert [r.title for r, _ in default] == ["actif"]
    assert sorted(r.title for r, _ in with_archived) == ["actif", "archivé"]
    assert [t.name for t in default[0][1]] == ["emplois"]
    assert tagged.id in [r.id for r, _ in default]


def test_get_used_conversation_tags_counts_by_user(client):
    ensure_tag("trafic", tag_type="metric")
    make_conv(ALICE, tags=["emplois", "trafic"])
    make_conv(BOB, tags=["emplois"])

    counts = {t.name: t.count for tags in store.get_used_conversation_tags_by_type().values() for t in tags}
    alice_counts = {
        t.name: t.count for tags in store.get_used_conversation_tags_by_type(user_id=ALICE).values() for t in tags
    }

    assert counts == {"emplois": 2, "trafic": 1}
    assert alice_counts == {"emplois": 1, "trafic": 1}


def test_get_used_conversation_tags_with_active_filter(client):
    ensure_tag("trafic", tag_type="metric")
    make_conv(ALICE, tags=["emplois", "trafic"])
    make_conv(BOB, tags=["emplois"])

    by_type = store.get_used_conversation_tags_by_type(active_tag_names=["trafic"])
    counts = {t.name: t.count for tags in by_type.values() for t in tags}

    assert counts == {"emplois": 1, "trafic": 1}
