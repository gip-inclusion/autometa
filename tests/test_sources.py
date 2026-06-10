"""Tests for lib/sources.py — config loading and credential resolution."""

import textwrap

import pytest

from lib import sources
from lib.sources import (
    get_default_instance,
    get_matomo,
    get_source_config,
    list_instances,
    load_config,
    substitute_env_vars,
)

CONFIG = """
matomo:
  _default: inclusion
  inclusion:
    url: https://stats.example.org
    token: ${env.TEST_MATOMO_TOKEN}
metabase:
  _default: stats
  stats:
    url: https://mb.example.org
    api_key: ${env.TEST_MB_KEY}
"""


@pytest.fixture
def write_config(tmp_path, monkeypatch):
    def _write(content=CONFIG):
        path = tmp_path / "sources.yaml"
        path.write_text(textwrap.dedent(content))
        monkeypatch.setattr(sources, "CONFIG_PATH", path)
        monkeypatch.setattr(sources, "config_cache", None)
        return path

    return _write


@pytest.mark.parametrize(
    "value,expected",
    [
        ("plain", "plain"),
        ("${env.TEST_SUB_VAR}", "resolved"),
        ("x-${env.TEST_SUB_VAR}-y", "x-resolved-y"),
        ("${env.TEST_SUB_MISSING}", "${env.TEST_SUB_MISSING}"),
        ({"k": "${env.TEST_SUB_VAR}"}, {"k": "resolved"}),
        (["${env.TEST_SUB_VAR}", 42], ["resolved", 42]),
        (42, 42),
        (None, None),
    ],
)
def test_substitute_env_vars(monkeypatch, value, expected):
    monkeypatch.setenv("TEST_SUB_VAR", "resolved")
    assert substitute_env_vars(value) == expected


def test_substitute_env_vars_strict_raises_on_missing():
    with pytest.raises(ValueError, match="TEST_SUB_MISSING"):
        substitute_env_vars("${env.TEST_SUB_MISSING}", strict=True)


def test_load_config_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "CONFIG_PATH", tmp_path / "absent.yaml")
    monkeypatch.setattr(sources, "config_cache", None)
    with pytest.raises(FileNotFoundError):
        load_config()


def test_load_config_caches_until_force_reload(write_config):
    path = write_config()
    assert "matomo" in load_config()

    path.write_text("matomo:\n  _default: autre\n")
    assert load_config()["matomo"]["_default"] == "inclusion"
    assert load_config(force_reload=True)["matomo"]["_default"] == "autre"


def test_get_source_config_resolves_default_instance(write_config, monkeypatch):
    write_config()
    monkeypatch.setenv("TEST_MATOMO_TOKEN", "tok")

    config = get_source_config("matomo")

    assert config == {"url": "https://stats.example.org", "token": "tok"}


def test_get_source_config_unknown_type(write_config):
    write_config()
    with pytest.raises(ValueError, match="Unknown source type"):
        get_source_config("nope")


def test_get_source_config_unknown_instance_lists_available(write_config):
    write_config()
    with pytest.raises(ValueError, match="Available: inclusion"):
        get_source_config("matomo", instance="absente")


def test_get_source_config_strict_on_selected_instance(write_config, monkeypatch):
    write_config()
    monkeypatch.delenv("TEST_MATOMO_TOKEN", raising=False)

    with pytest.raises(ValueError, match="TEST_MATOMO_TOKEN"):
        get_source_config("matomo")


def test_get_matomo_strips_scheme_from_url(write_config, monkeypatch, mocker):
    write_config()
    monkeypatch.setenv("TEST_MATOMO_TOKEN", "tok")
    api_cls = mocker.patch("lib.sources.MatomoAPI")

    get_matomo()

    api_cls.assert_called_once_with(url="stats.example.org", token="tok", instance="inclusion")


def test_list_instances_excludes_private_keys(write_config):
    write_config()
    assert list_instances("matomo") == ["inclusion"]
    assert list_instances("inconnu") == []


def test_get_default_instance(write_config):
    write_config()
    assert get_default_instance("matomo") == "inclusion"
    assert get_default_instance("inconnu") is None
