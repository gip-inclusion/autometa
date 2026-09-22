"""Registre des sources, sondes partagées et fiches — couloir hermétique."""

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path

import fakeredis.aioredis
import pytest
from redis.exceptions import RedisError

from web import config
from web.routes import sources as sources_routes
from web.source_checks import redact
from web.sources_registry import GROUPS, Source, all_sources, check_source, find_source, grouped_sources

REPO = Path(__file__).parent.parent
SITES_DIR = REPO / "knowledge" / "sites"


def make_source(**overrides) -> Source:
    defaults = dict(
        slug="essai",
        name="Essai",
        group=GROUPS[0],
        blurb="Une source d'essai.",
        check=lambda: (True, "ok"),
        configured=lambda: True,
    )
    return Source(**{**defaults, **overrides})


@pytest.fixture(autouse=True)
def isolated_probe_cache(mocker):
    """Un Redis neuf par test : sans cela le couloir hermétique dépendrait d'un Redis réellement lancé."""
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    mocker.patch("web.routes.sources.get_redis", return_value=fake)
    return fake


def test_registry_covers_the_four_groups():
    assert list(grouped_sources()) == GROUPS
    assert all(grouped_sources()[group] for group in GROUPS)


@pytest.mark.parametrize(
    "slug",
    ["autometa-tables-db", "zendesk", "grist", "rpe", "s3", "tally"],
)
def test_sources_absent_from_the_old_home_grid_are_declared(slug):
    """DOD-2 : le registre déclare les sources qu'un listing de knowledge/ taisait."""
    assert find_source(slug) is not None


@pytest.mark.parametrize("source", [s for s in all_sources() if s.doc], ids=lambda s: s.slug)
def test_declared_doc_resolves_to_an_existing_document(source):
    """DOD-10 : une fiche déclarée existe, et elle vit là où la documentation vivait déjà."""
    assert (REPO / source.doc).is_file()
    assert source.doc.split("/")[0] in ("knowledge", "skills", "docs")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("---\nname: rpe\n---\n# RPE\ncorps", "# RPE\ncorps"),
        ("# Sans en-tête\ncorps", "# Sans en-tête\ncorps"),
        ("---\nen-tête jamais fermé\n# Titre", "---\nen-tête jamais fermé\n# Titre"),
        ("---\nname: x\n---\ncorps avec --- au milieu\n", "corps avec --- au milieu\n"),
    ],
)
def test_front_matter_is_stripped_before_rendering(raw, expected):
    assert sources_routes.strip_front_matter(raw) == expected


@pytest.mark.parametrize("doc", ["../../etc/passwd", "/etc/passwd", "web/config.py"])
def test_doc_outside_the_allowed_roots_is_refused(doc):
    """Le champ doc désigne un fichier du dépôt : il ne doit pas pouvoir sortir des dossiers de documentation."""
    assert sources_routes.doc_path(make_source(doc=doc)) is None


def test_no_parallel_source_documentation_tree():
    """La page lit la documentation existante ; elle n'en fabrique pas une copie concurrente."""
    assert not (REPO / "knowledge" / "sources").exists()


def test_documentation_is_never_declared_twice_for_one_source():
    docs = [s.doc for s in all_sources() if s.doc]
    shared = {doc for doc in docs if docs.count(doc) > 1}
    # Grist et Livestorm partagent légitimement la fiche webinaires : elles décrivent le même jeu de données.
    assert shared <= {"knowledge/webinaires/_index.md"}


def test_building_the_registry_never_raises_without_credentials(monkeypatch):
    monkeypatch.setattr(config, "AUTOMETA_TABLES_DATABASE_URL", "")
    monkeypatch.setattr(config, "NOTION_TOKEN", None)
    assert len(all_sources()) > 10


def probe(source):
    return asyncio.run(sources_routes.probe(source))


def test_unconfigured_source_is_reported_as_such_not_probed():
    """DOD-6 : hors configuration, on ne sonde pas et on le dit."""
    probed = []
    source = make_source(configured=lambda: False, check=lambda: probed.append(1) or (True, "ok"))

    assert probe(source) == {"state": "unconfigured", "detail": "non configuré dans cet environnement"}
    assert probed == []


def test_probe_is_cached_across_web_processes():
    """DOD-7 : le cache vit dans Redis, donc une seule sonde par minute quel que soit le nombre de workers."""
    calls = []
    source = make_source(check=lambda: (calls.append(1), (True, "ok"))[1])

    async def scenario():
        for _ in range(6):
            assert (await sources_routes.probe(source))["state"] == "ok"

    asyncio.run(scenario())

    assert len(calls) == 1


def test_probe_still_answers_when_redis_is_down(mocker):
    """Redis indisponible ne doit pas empêcher la page de s'afficher — seule la mise en cache est perdue."""
    mocker.patch("web.routes.sources.get_redis", side_effect=RedisError("down"))
    calls = []
    source = make_source(check=lambda: (calls.append(1), (True, "ok"))[1])

    for _ in range(3):
        assert probe(source)["state"] == "ok"

    assert len(calls) == 3


def test_probe_survives_a_client_exception():
    source = make_source(check=lambda: (_ for _ in ()).throw(TimeoutError("trop long")))
    assert probe(source)["state"] == "ko"


def test_probe_detail_never_carries_a_connection_string():
    """DOD-8 : un message de sonde qui porte un DSN ne doit pas atteindre la page."""
    dsn = "postgresql://user:sup3rs3cret@db.example.net:5432/base"
    source = make_source(check=lambda: (False, f"échec sur {dsn}"))

    detail = probe(source)["detail"]
    assert "sup3rs3cret" not in detail
    assert "***" in detail


@pytest.mark.parametrize(
    "raw,forbidden",
    [
        ("postgres://u:pwd@host/db", "pwd"),
        ("connexion refusée vers postgresql://admin:hunter2@10.0.0.1/x", "hunter2"),
    ],
)
def test_redact_strips_dsn_credentials(raw, forbidden):
    assert forbidden not in redact(raw)


def test_realtime_source_has_no_inventory_date():
    assert sources_routes.inventory_state(make_source())["realtime"] is True


def test_reachable_source_can_still_have_a_stale_inventory():
    """DOD-4 : les deux signaux sont indépendants."""
    stale = datetime(2026, 1, 1, tzinfo=timezone.utc)
    source = make_source(inventory=lambda: stale)

    assert probe(source)["state"] == "ok"
    state = sources_routes.inventory_state(source)
    assert state["realtime"] is False
    assert state["label"]


def test_never_synced_inventory_is_named_as_such():
    assert sources_routes.inventory_state(make_source(inventory=lambda: None))["label"] == "jamais synchronisé"


def test_selftest_probes_the_registry_sources():
    """DOD-11 : une seule définition de sonde, consommée par les deux pages."""
    from web.selftest import _check_specs

    names = [name for name, _ in _check_specs()]
    for source in all_sources():
        assert source.name in names


def test_check_source_short_circuits_when_unconfigured():
    ok, detail = check_source(make_source(configured=lambda: False))
    assert ok is False
    assert "non configuré" in detail


def test_check_source_runs_the_probe_when_configured():
    assert check_source(make_source(check=lambda: (True, "en ligne"))) == (True, "en ligne")


@pytest.mark.parametrize("path", sorted(SITES_DIR.glob("*.md")), ids=lambda p: p.name)
def test_site_fiches_carry_no_frozen_traffic_table(path):
    """DOD-12 : les chiffres vivent en base, pas recopiés dans une fiche."""
    header = re.compile(r"^\|.*(Visiteurs uniques|Unique Visitors|Daily Avg|Moy\. visiteurs).*\|$", re.M)
    assert not header.search(path.read_text())
