"""Lecture des dépôts publics GitHub : lib/github.py et le script du skill github."""

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from lib import github, query
from lib.attestation import git

SCRIPT = Path(__file__).parent.parent / "skills" / "github" / "scripts" / "query.py"


def pull_request(number: int) -> dict:
    return {
        "number": number,
        "title": f"PR {number}",
        "state": "closed",
        "draft": False,
        "merged_at": "2026-10-02T12:00:00Z",
        "user": {"login": "dev"},
        "updated_at": "2026-10-02T12:00:00Z",
        "base": {"ref": "main"},
        "head": {"ref": "fix"},
        "html_url": f"https://github.com/gip-inclusion/demo/pull/{number}",
        "body": "Pourquoi",
        "merge_commit_sha": "abc",
    }


def commit(repo: Path, files: dict[str, str], message: str) -> str:
    for name, content in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(content)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


@pytest.fixture
def remote(tmp_path, monkeypatch):
    """`gip-inclusion/demo`, servi à la place de github.com : deux commits sur main, le second resserre la règle."""
    repo = tmp_path / "remote" / "gip-inclusion" / "demo.git"
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    for key, value in (
        ("user.email", "dev@example.invalid"),
        ("user.name", "Dev"),
        ("commit.gpgsign", "false"),
        # Why: GitHub sert n'importe quel commit atteignable par son SHA ; un dépôt local, seulement si on le lui dit.
        ("uploadpack.allowReachableSHA1InWant", "true"),
    ):
        git(repo, "config", key, value)
    first = commit(repo, {"app/models.py": "def eligible():\n    return True\n"}, "Add eligibility")
    second = commit(
        repo, {"app/models.py": "def eligible():\n    return False\n", "README.md": "Eligible\n"}, "Tighten eligibility"
    )
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", f"url.file://{tmp_path / 'remote'}/.insteadOf")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "https://github.com/")
    (tmp_path / "tmp").mkdir()
    monkeypatch.setattr(github.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    return SimpleNamespace(repo=repo, first=first, second=second)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("gip-inclusion/les-emplois", "gip-inclusion/les-emplois"),
        ("BetaGouv/beta.gouv.fr", "betagouv/beta.gouv.fr"),
        ("gip-inclusion/Les-Emplois", "gip-inclusion/les-emplois"),
        ("numerique-gouv/.github", "numerique-gouv/.github"),
        ("SuiteNumerique/docs", "suitenumerique/docs"),
    ],
)
def test_repository_accepts_the_allowed_organisations(name, expected):
    assert github.repository(name) == expected


@pytest.mark.parametrize(
    "name", ["autre/x", "gip-inclusion", "gip-inclusion/..", "gip-inclusion/a/b", "gip-inclusion/a b"]
)
def test_repository_refuses_anything_else(name):
    with pytest.raises(ValueError, match="seuls les dépôts"):
        github.repository(name)


@pytest.mark.parametrize("ref", [None, "main", "feature/x", "v2.64.0", "7ff89badcf" * 4])
def test_reference_accepts_branches_tags_and_shas(ref):
    assert github.reference(ref) == ref


@pytest.mark.parametrize("ref", ["--depth=1000", "-x", "refs/pull/*/head", "main:refs/heads/x", "a b", ""])
def test_reference_refuses_what_git_would_read_as_an_option_or_a_pattern(ref):
    with pytest.raises(ValueError, match="référence invalide"):
        github.reference(ref)


def test_a_refused_token_falls_back_to_anonymous_reading(mocker):
    mocker.patch.object(github.config, "GITHUB_TOKEN", "expiré")
    sent = mocker.patch(
        "lib.github.httpx.request", side_effect=[httpx.Response(401), httpx.Response(200, json={"a": 1})]
    )

    assert github.request("GET", "repos/gip-inclusion/x").json() == {"a": 1}
    assert [call.kwargs["headers"].get("Authorization") for call in sent.call_args_list] == ["Bearer expiré", None]


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(404), "absent, privé"),
        (httpx.Response(403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "0"}), "quota"),
        (httpx.ConnectError("boom"), "panne réseau, pas un refus d'accès"),
        (httpx.Response(500, text="oops"), "GitHub 500"),
    ],
)
def test_each_failure_says_what_to_conclude(mocker, response, message):
    mocker.patch("lib.github.httpx.request", side_effect=[response])

    with pytest.raises(github.GitHubError, match=message):
        github.request("GET", "repos/gip-inclusion/x")


def test_api_refuses_a_private_repository_the_token_can_see(mocker):
    mocker.patch.object(github.config, "GITHUB_TOKEN", "jeton")
    sent = mocker.patch("lib.github.request", return_value=httpx.Response(200, json={"private": True}))

    with pytest.raises(github.GitHubError, match="privé"):
        github.api("repos/gip-inclusion/secret/contents/x")
    sent.assert_called_once_with("GET", "repos/gip-inclusion/secret")


def test_api_without_token_reads_directly(mocker):
    mocker.patch.object(github.config, "GITHUB_TOKEN", "")
    sent = mocker.patch("lib.github.request", return_value=httpx.Response(200, text="contenu"))

    assert github.api("repos/gip-inclusion/x/contents/a.py", raw=True) == "contenu"
    sent.assert_called_once_with("GET", "repos/gip-inclusion/x/contents/a.py", github.RAW, 30, params=None)


def test_log_sends_only_the_given_filters_and_keeps_the_subject_line(mocker):
    mocker.patch.object(github.config, "GITHUB_TOKEN", "")
    found = {"sha": "abc", "commit": {"committer": {"date": "2026-10-28T10:00:00Z"}, "author": {"name": "Dev"}}}
    found["commit"]["message"] = "Tighten eligibility\n\nBecause."
    sent = mocker.patch("lib.github.request", return_value=httpx.Response(200, json=[found]))

    commits = github.log("gip-inclusion/demo", "app/models.py", max_results=5)

    assert commits == [{"commit": "abc", "date": "2026-10-28", "author": "Dev", "subject": "Tighten eligibility"}]
    assert sent.call_args.kwargs["params"] == {"per_page": 5, "path": "app/models.py"}


def test_show_keeps_only_the_files_under_the_path(mocker):
    mocker.patch.object(github.config, "GITHUB_TOKEN", "")
    files = [
        {"filename": name, "status": "modified", "additions": 1, "deletions": 0}
        for name in ("app/a.py", "application/b.py", "doc.md")
    ]
    data = {"sha": "abc", "commit": {"committer": {"date": "2026-10-28T10"}, "author": {"name": "Dev"}, "message": "m"}}
    mocker.patch("lib.github.request", return_value=httpx.Response(200, json=data | {"files": files}))

    assert [f["filename"] for f in github.show("gip-inclusion/demo", "abc", "app")["files"]] == ["app/a.py"]


def test_blame_gives_each_line_its_last_commit_and_its_text_at_the_blamed_commit(mocker):
    mocker.patch.object(github.config, "GITHUB_TOKEN", "jeton")
    old, new = (
        {"oid": oid, "committedDate": f"2026-10-0{n}T12:00:00Z", "author": {"name": "Dev"}}
        for n, oid in ((1, "a1"), (2, "b2"))
    )
    ranges = [
        {"startingLine": 1, "endingLine": 1, "commit": old | {"messageHeadline": "Add eligibility"}},
        {"startingLine": 2, "endingLine": 2, "commit": new | {"messageHeadline": "Tighten eligibility"}},
    ]
    sent = mocker.patch(
        "lib.github.request",
        side_effect=[
            httpx.Response(200, json={"private": False}),
            httpx.Response(
                200, json={"data": {"repository": {"object": {"oid": "head", "blame": {"ranges": ranges}}}}}
            ),
            httpx.Response(200, text="def eligible(): # \x0c\r\n    return False\n"),
        ],
    )

    rows = github.blame("gip-inclusion/demo", "app/models.py")

    assert [(r["line"], r["commit"], r["date"], r["summary"], r["text"]) for r in rows] == [
        (1, "a1", "2026-10-01", "Add eligibility", "def eligible(): # \x0c"),
        (2, "b2", "2026-10-02", "Tighten eligibility", "    return False"),
    ]
    assert sent.call_args.kwargs["params"] == {"ref": "head"}


@pytest.mark.parametrize(
    ("token", "body", "message"),
    [
        ("", None, "exige GITHUB_TOKEN"),
        ("jeton", {"errors": [{"message": "Could not resolve file"}]}, "Could not resolve file"),
        ("jeton", {"data": {"repository": {"object": None}}}, "référence introuvable"),
    ],
)
def test_blame_says_why_it_cannot_answer(mocker, token, body, message):
    mocker.patch.object(github.config, "GITHUB_TOKEN", token)
    mocker.patch(
        "lib.github.request",
        side_effect=[httpx.Response(200, json={"private": False}), httpx.Response(200, json=body)],
    )

    with pytest.raises(github.GitHubError, match=message):
        github.blame("gip-inclusion/demo", "a.py", "v1")


@pytest.mark.parametrize(
    ("commit_sha", "path"),
    [(None, "repos/gip-inclusion/demo/pulls"), ("abc", "repos/gip-inclusion/demo/commits/abc/pulls")],
)
def test_pulls_lists_the_pull_requests_of_the_repository_or_of_a_commit(mocker, commit_sha, path):
    api = mocker.patch("lib.github.api", return_value=[pull_request(1), pull_request(2)])

    found = github.pulls("gip-inclusion/demo", commit=commit_sha, max_results=1)

    assert [(pr["number"], pr["author"], pr["base"]) for pr in found] == [(1, "dev", "main")]
    assert api.call_args.args[0] == path


def test_pull_adds_the_description_and_the_changed_files(mocker):
    files = [{"filename": "a.py", "status": "modified", "additions": 1, "deletions": 2, "patch": "@@"}]
    mocker.patch("lib.github.api", side_effect=[pull_request(9), files])

    found = github.pull("gip-inclusion/demo", 9)

    assert (found["number"], found["body"], found["head"], found["files"]) == (
        9,
        "Pourquoi",
        "fix",
        [{"filename": "a.py", "status": "modified", "additions": 1, "deletions": 2}],
    )


def test_a_private_repository_fails_instead_of_asking_for_credentials(mocker, tmp_path):
    prompt = "fatal: could not read Username for 'https://github.com': terminal prompts disabled"
    mocker.patch("lib.github.subprocess.run", return_value=subprocess.CompletedProcess((), 128, "", prompt))

    with pytest.raises(github.GitHubError, match="absent ou privé"):
        github.git(tmp_path, "fetch")


def test_each_ref_gets_its_own_clone(remote, tmp_path):
    latest, head = github.clone("gip-inclusion/demo", tmp_path / "clones")
    older, first = github.clone("gip-inclusion/demo", tmp_path / "clones", ref=remote.first)

    assert (head, first) == (remote.second, remote.first)
    assert github.grep(latest, "return") == {
        "total": 1,
        "matches": [{"path": "app/models.py", "line": 2, "text": "    return False"}],
    }
    assert github.grep(older, "return")["matches"][0]["text"] == "    return True"


def test_grep_keeps_a_line_whole_whatever_control_characters_it_holds(remote, tmp_path):
    commit(remote.repo, {"app/min.js": "a\x0cb\u2028c = eligible\r\n"}, "Minify")
    path, _ = github.clone("gip-inclusion/demo", tmp_path)

    assert github.grep(path, "c = eligible")["matches"] == [
        {"path": "app/min.js", "line": 1, "text": "a\x0cb\u2028c = eligible"}
    ]


def test_a_symlink_is_checked_out_as_a_plain_file_holding_its_target(remote, tmp_path):
    (remote.repo / "settings.py").symlink_to("/etc/hosts")
    commit(remote.repo, {}, "Link settings")
    path, _ = github.clone("gip-inclusion/demo", tmp_path)

    assert not (path / "settings.py").is_symlink()
    assert (path / "settings.py").read_text() == "/etc/hosts"


def test_grep_counts_every_match_but_returns_at_most_max_results(remote, tmp_path):
    path, _ = github.clone("gip-inclusion/demo", tmp_path)

    found = github.grep(path, "eligible", ignore_case=True, max_results=1)

    assert (found["total"], len(found["matches"])) == (2, 1)


def test_grep_reports_an_invalid_pattern(remote, tmp_path):
    path, _ = github.clone("gip-inclusion/demo", tmp_path)

    with pytest.raises(github.GitHubError, match="git grep"):
        github.grep(path, "(")


def test_search_github_code_works_in_a_throwaway_clone(remote):
    result = query.execute_github_search("gip-inclusion/demo", "def ", query.CallerType.APP)

    assert result.data == {
        "commit": remote.second,
        "total": 1,
        "matches": [{"path": "app/models.py", "line": 1, "text": "def eligible():"}],
    }


def test_sweep_removes_only_clones_idle_for_a_day(mocker, tmp_path):
    mocker.patch.object(github.tempfile, "gettempdir", return_value=str(tmp_path))
    idle, recent, foreign = (
        tmp_path / p for p in ("c1/github/betagouv/x", "c2/github/betagouv/y", "c1/github/autre/z")
    )
    for path in (idle, recent, foreign):
        path.mkdir(parents=True)
    for path in (idle, foreign):
        os.utime(path, (0, 0))

    github.sweep()

    assert [path.exists() for path in (idle, recent, foreign)] == [False, True, True]


def run_cli(monkeypatch, *argv):
    spec = importlib.util.spec_from_file_location("github_cli", SCRIPT)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    monkeypatch.setattr("sys.argv", ["query.py", *argv])
    cli.main()


def test_the_cli_groups_blamed_lines_under_their_commit(mocker, monkeypatch, capsys):
    rows = [
        {"line": n, "commit": sha, "date": "2026-10-01", "author": "Dev", "summary": summary, "text": f"ligne {n}"}
        for n, sha, summary in ((1, "a1", "Add"), (2, "b2", "Tighten"), (3, "b2", "Tighten"), (4, "b2", "Tighten"))
    ]
    mocker.patch("lib.github.blame", return_value=rows)

    run_cli(monkeypatch, "blame", "gip-inclusion/demo", "app/models.py", "-L", "2,4", "--max-lines", "3")

    assert capsys.readouterr().out.splitlines() == [
        "b2 2026-10-01 Dev — Tighten",
        "      2 | ligne 2",
        "      3 | ligne 3",
        "… 1 lignes coupées",
    ]


def test_the_cli_clones_into_the_conversation_workspace_and_cleanup_removes_it(remote, monkeypatch, capsys):
    run_cli(monkeypatch, "clone", "gip-inclusion/demo")
    path, commit_line = capsys.readouterr().out.splitlines()
    run_cli(monkeypatch, "cleanup")

    assert (Path(path).parent.parent, commit_line) == (github.workspace(), f"commit {remote.second}")
    assert not Path(path).exists()


def test_the_cli_greps_and_counts_the_matches(remote, monkeypatch, capsys):
    run_cli(monkeypatch, "grep", "gip-inclusion/demo", "return")

    assert capsys.readouterr().out.splitlines() == [
        f"commit {remote.second} — 1 lignes trouvées",
        "app/models.py:2:     return False",
    ]


@pytest.mark.parametrize(
    ("argv", "function", "returned", "expected"),
    [
        (["read", "gip-inclusion/demo", "a.py"], "read", "contenu", ["contenu"]),
        (
            ["log", "gip-inclusion/demo", "app"],
            "log",
            [{"commit": "abc", "date": "2026-10-01", "author": "Dev", "subject": "Add"}],
            ["abc 2026-10-01 Dev — Add"],
        ),
        (
            ["show", "gip-inclusion/demo", "abc"],
            "show",
            {
                "commit": "abc",
                "date": "2026-10-01",
                "author": "Dev",
                "message": "Add\n\nWhy",
                "files": [
                    {"filename": "a.py", "status": "added", "additions": 1, "deletions": 0, "patch": "+x"},
                    {"filename": "logo.png", "status": "added", "additions": 0, "deletions": 0, "patch": None},
                ],
            },
            [
                "abc — Dev, 2026-10-01",
                "",
                "Add",
                "",
                "Why",
                "",
                "--- a.py (added, +1 −0)",
                "+x",
                "",
                "--- logo.png (added, +0 −0)",
                "(diff non fourni par GitHub : fichier binaire ou trop gros)",
            ],
        ),
    ],
)
def test_the_cli_prints_text_readings(mocker, monkeypatch, capsys, argv, function, returned, expected):
    mocker.patch(f"lib.github.{function}", return_value=returned)

    run_cli(monkeypatch, *argv)

    assert capsys.readouterr().out.splitlines() == expected


@pytest.mark.parametrize(
    ("argv", "function", "returned", "expected"),
    [
        (
            ["repo", "gip-inclusion/demo"],
            "public",
            {
                "id": 1,
                "full_name": "gip-inclusion/demo",
                "default_branch": "main",
                "description": None,
                "archived": False,
                "pushed_at": "2026-10-02T12:00:00Z",
                "html_url": "https://github.com/gip-inclusion/demo",
            },
            {
                "full_name": "gip-inclusion/demo",
                "default_branch": "main",
                "description": None,
                "archived": False,
                "pushed_at": "2026-10-02T12:00:00Z",
                "html_url": "https://github.com/gip-inclusion/demo",
            },
        ),
        (["prs", "gip-inclusion/demo", "--commit", "abc"], "pulls", [{"number": 1}], [{"number": 1}]),
        (["pr", "gip-inclusion/demo", "9"], "pull", {"number": 9}, {"number": 9}),
    ],
)
def test_the_cli_prints_json_readings(mocker, monkeypatch, capsys, argv, function, returned, expected):
    mocker.patch(f"lib.github.{function}", return_value=returned)

    run_cli(monkeypatch, *argv)

    assert json.loads(capsys.readouterr().out) == expected


def test_the_cli_reports_a_refusal_without_a_traceback(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exit_:
        run_cli(monkeypatch, "grep", "autre-org/x", "motif")

    assert exit_.value.code == 1
    assert capsys.readouterr().err.startswith("Erreur : autre-org/x : seuls les dépôts")
