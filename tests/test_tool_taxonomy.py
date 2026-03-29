"""Tests for lib/tool_taxonomy.py."""

import pytest

from lib.tool_taxonomy import PUBLIC_CATEGORIES, classify_tool, is_public_category


@pytest.mark.parametrize(
    "tool,input_data,expected",
    [
        ("Bash", {"command": "python -c 'from lib.matomo import MatomoAPI'"}, "API: Matomo"),
        ("Bash", {"command": "matomo_api.request('VisitsSummary.get')"}, "API: Matomo"),
        ("Bash", {"command": "python -c 'from lib.metabase import MetabaseAPI'"}, "API: Metabase"),
        ("Bash", {"command": "api.execute_sql('SELECT 1')"}, "API: Metabase"),
        (
            "Bash",
            {"command": "from lib.matomo import MatomoAPI; from lib.metabase import MetabaseAPI"},
            "API: Matomo + Metabase",
        ),
        ("Bash", {"command": "curl https://matomo.inclusion.gouv.fr/..."}, "API: Matomo (curl)"),
        ("Bash", {"command": "curl https://api.github.com/repos/..."}, "API: GitHub"),
        ("Bash", {"command": "curl https://example.com/api"}, "API: curl"),
        ("Bash", {"command": "git clone https://github.com/gip-inclusion/les-emplois"}, "API: GitHub (clone)"),
        ("Bash", {"command": "git status"}, "Shell: git"),
        ("Bash", {"command": "python -c 'print(1)'"}, "Execute: script"),
        ("Bash", {"command": ".venv/bin/python script.py"}, "Execute: script"),
        ("Bash", {"command": "sqlite3 ./knowledge/metabase/cards.db 'SELECT 1'"}, "Query: SQLite"),
        ("Bash", {"command": "ls -la /app"}, "Shell: explore"),
        ("Bash", {"command": "cat /tmp/output.txt"}, "Shell: explore"),
        ("Bash", {"command": "pip install pandas"}, "Shell: setup"),
        ("Bash", {"command": "mkdir -p /tmp/test"}, "Shell: setup"),
        ("Bash", {"command": "echo hello"}, "Shell: other"),
        ("Read", {"file_path": "/app/knowledge/sites/emplois.md"}, "Read: knowledge"),
        ("Read", {"file_path": "/app/skills/matomo_query/skill.md"}, "Read: skill definition"),
        ("Read", {"file_path": "/app/skills/matomo_query/scripts/matomo.py"}, "Read: skill code"),
        ("Read", {"file_path": "/app/web/routes/conversations.py"}, "Read: code"),
        ("Read", {"file_path": "/app/CLAUDE.md"}, "Read: docs"),
        ("Read", {"file_path": "/tmp/output.txt"}, "Read: temp"),
        ("Read", {"file_path": "/app/config/sources.yaml"}, "Read: other"),
        ("Write", {"file_path": "/tmp/analysis.py"}, "Write: temp"),
        ("Write", {"file_path": "/app/data/interactive/dashboard.html"}, "Write: interactive"),
        ("Write", {"file_path": "/app/data/scripts/query.py"}, "Write: script"),
        ("Write", {"file_path": "/app/knowledge/sites/new-site.md"}, "Write: knowledge"),
        ("Write", {"file_path": "/app/config.txt"}, "Write: other"),
        ("Edit", {"file_path": "/app/knowledge/sites/emplois.md"}, "Edit: knowledge"),
        ("Edit", {"file_path": "/app/skills/matomo_query/skill.md"}, "Edit: skill"),
        ("Edit", {"file_path": "/app/web/app.py"}, "Edit: code"),
        ("Edit", {"file_path": "/app/config.yaml"}, "Edit: other"),
        ("Skill", {"skill": "matomo_query"}, "Skill: matomo_query"),
        ("Glob", {"pattern": "**/*.py"}, "Search: codebase"),
        ("Grep", {"pattern": "MatomoAPI"}, "Search: codebase"),
        ("TodoWrite", {"todos": []}, "Thinking: todo"),
        ("WebFetch", {"url": "https://example.com"}, "Web: fetch"),
        ("Task", {"prompt": "do something"}, "System: task"),
        ("AskUserQuestion", {"question": "Which option?"}, "Interaction: ask user"),
        ("UnknownTool", {}, "Other: UnknownTool"),
    ],
)
def test_classify_tool(tool, input_data, expected):
    assert classify_tool(tool, input_data) == expected


@pytest.mark.parametrize(
    "category,expected",
    [
        ("API: Matomo", True),
        ("API: Metabase", True),
        ("Read: knowledge", True),
        ("Write: interactive", True),
        ("Skill: matomo_query", True),
        ("Skill: save_report", True),
        ("Skill: custom_skill", True),
        ("Shell: explore", False),
        ("Write: temp", False),
        ("Thinking: todo", False),
        ("Execute: script", False),
    ],
)
def test_is_public_category(category, expected):
    assert is_public_category(category) is expected


def test_public_categories_contains_expected():
    for cat in [
        "API: Matomo",
        "API: Metabase",
        "API: Matomo + Metabase",
        "Read: knowledge",
        "Read: skill definition",
        "Read: docs",
    ]:
        assert cat in PUBLIC_CATEGORIES
    for cat in ["Shell: explore", "Shell: setup"]:
        assert cat not in PUBLIC_CATEGORIES
