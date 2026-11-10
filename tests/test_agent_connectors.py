import contextlib
import io
import json
import socket
import tarfile

import httpx
import pytest

from lib import agent_config, agent_connectors
from lib.agent_connectors import github
from lib.agent_connectors import notion as notion_connector
from lib.agent_connectors import url as url_connector

BASE = "0123456789abcdef0123456789abcdef"
PAGE = "fedcba9876543210fedcba9876543210"


def errors(step):
    return agent_connectors.errors(0, step)


def test_dod_15_types_are_the_closed_list_of_the_config_each_with_one_interface():
    assert agent_connectors.types() == ["notion", "github", "url", "s3", "cron"]
    for kind, entry in agent_connectors.catalogue().items():
        module = agent_connectors.connector(kind)
        assert entry["description"] and "cap" in entry["fields"]
        assert all(callable(getattr(module, f)) for f in ("errors", "source", "prepare"))


@pytest.mark.parametrize("kind", ["sql", "__init__", "agent_connectors"])
def test_dod_15_a_type_outside_the_config_is_never_imported(kind):
    with pytest.raises(ValueError, match="hors de config/agent_preparations.yaml"):
        agent_connectors.connector(kind)
    assert "attendu un type parmi notion, github, url, s3, cron" in errors({"type": kind})[0]


@pytest.mark.parametrize(
    ("step", "expected"),
    [
        ({"type": "notion"}, "base ou page : attendu exactement l'un des deux"),
        ({"type": "notion", "base": BASE, "page": PAGE}, "exactement l'un des deux"),
        ({"type": "notion", "page": "notion.so/x"}, "page : attendu l'identifiant Notion"),
        ({"type": "notion", "base": BASE, "depth": 2}, "depth : sans objet pour une base"),
        ({"type": "notion", "page": PAGE, "columns": ["Nom"]}, "columns : sans objet pour une page"),
        ({"type": "notion", "page": PAGE, "depth": 4}, "depth : attendu un entier de 1 à 3"),
        ({"type": "notion", "base": BASE, "filter": [{"column": "Statut"}]}, "exactement un opérateur"),
        ({"type": "notion", "base": BASE, "filter": [{"column": "S", "equals": 1, "in": [1]}]}, "exactement un"),
        ({"type": "notion", "base": BASE, "filter": [{"column": "S", "proche": "x"}]}, "opérateur inconnu"),
        ({"type": "notion", "base": BASE, "filter": [{"column": "Créé", "after": "hier"}]}, "AAAA-MM-JJ"),
        ({"type": "notion", "base": BASE, "filter": []}, "de 1 à 10 conditions"),
        ({"type": "notion", "base": BASE, "columns": []}, "columns : attendu une liste de 1 à 30"),
        (
            {"type": "notion", "base": BASE, "group_by": list("abcdef")},
            "group_by : attendu une liste de 1 à 5",
        ),
        ({"type": "notion", "base": BASE, "cap": 10**6}, "preparations[0].cap : attendu un entier de 1000"),
        ({"type": "notion", "base": BASE, "requete": "x"}, "champs inconnus pour notion : requete"),
        ({"type": "github"}, "repos ou organization : attendu au moins l'un des deux"),
        ({"type": "github", "repos": ["les-emplois"]}, "n'est pas un dépôt proprietaire/depot"),
        ({"type": "github", "repos": ["a/../b"]}, "n'est pas un dépôt"),
        ({"type": "github", "repos": "a/b"}, "repos : attendu une liste"),
        ({"type": "github", "organization": "a/b"}, "organization : attendu un nom de propriétaire"),
        ({"type": "github", "repos": ["a/b"], "repo_cap": 100}, "repo_cap : attendu un entier de 2000"),
        ({"type": "url", "url": "http://example.org"}, "url : attendu une adresse https://"),
        ({"type": "url", "url": "https://user:pass@example.org"}, "sans identifiants"),
        ({"type": "url"}, "url : attendu une adresse https://"),
    ],
)
def test_dod_15_a_malformed_preparation_is_refused_naming_its_field(step, expected):
    found = errors(step)
    assert any(expected in e for e in found), found
    assert all(e.startswith("preparations[0]") for e in found)


@pytest.mark.parametrize(
    "step",
    [
        {"type": "notion", "base": BASE, "filter": [{"column": "Statut", "in": ["À faire"]}], "cap": 5000},
        {"type": "notion", "page": PAGE, "depth": 3},
        {"type": "github", "repos": ["owner/repo"], "organization": "owner", "repo_cap": 10000},
        {"type": "url", "url": "https://example.org/notes.md"},
    ],
)
def test_dod_15_any_source_given_in_the_configuration_is_accepted(step):
    assert errors(step) == []


ROWS = [
    {"Nom": "Export CSV", "Statut": "À faire", "Tags": ["export"], "Créé": "2026-10-01"},
    {"Nom": "Carte | régions", "Statut": "Fait", "Tags": ["carte", "export"], "Créé": "2026-09-01"},
    {"Nom": "Relance", "Statut": "À faire", "Tags": [], "Créé": None},
]


@pytest.fixture
def notion_base(mocker):
    mocker.patch("lib.notion.NOTION_TOKEN", "notion-token")
    pages = [{"properties": row, "last_edited_time": f"2026-11-0{i + 1}T10:00:00Z"} for i, row in enumerate(ROWS)]
    mocker.patch("lib.notion.query_database", return_value=pages)
    mocker.patch("lib.notion.extract_page_properties", side_effect=lambda page: dict(page["properties"]))


def prepared(step):
    return agent_connectors.prepare({"type": "notion", "base": BASE, **step})


@pytest.mark.parametrize(
    ("filter", "names"),
    [
        ([{"column": "Statut", "equals": "À faire"}], ["Export CSV", "Relance"]),
        ([{"column": "Tags", "equals": "export"}], ["Export CSV", "Carte \\| régions"]),
        ([{"column": "Tags", "in": ["carte"]}], ["Carte \\| régions"]),
        ([{"column": "Nom", "contains": "csv"}], ["Export CSV"]),
        ([{"column": "Créé", "after": "2026-09-15"}], ["Export CSV"]),
        ([{"column": "Créé", "avant": "2026-09-15"}], ["Carte \\| régions"]),
        ([{"column": "Statut", "equals": "À faire"}, {"column": "Tags", "equals": "export"}], ["Export CSV"]),
    ],
)
def test_dod_15_a_notion_base_is_filtered_narrowed_and_rendered_as_a_markdown_table(notion_base, filter, names):
    found = prepared({"filter": filter, "columns": ["Nom", "Statut"]})
    lines = found["content"].splitlines()
    assert found["source"] == f"base {BASE}"
    assert lines[0] == f"{len(names)} lignes."
    assert lines[2] == "| Nom | Statut | derniere_modification |"
    assert [line.split(" | ")[0].removeprefix("| ") for line in lines[4:]] == names


def test_dod_15_a_notion_base_beyond_its_cap_becomes_a_deterministic_digest(notion_base, mocker):
    pages = [
        {"properties": {**row, "Notes": "n" * 300}, "last_edited_time": f"2026-11-0{i + 1}"}
        for i, row in enumerate(ROWS)
    ]
    mocker.patch("lib.notion.query_database", return_value=pages)
    found = prepared({"cap": 1000, "group_by": ["Statut", "Tags"]})
    text = found["content"]
    assert text == prepared({"cap": 1000, "group_by": ["Statut", "Tags"]})["content"]
    assert "## Statut\n- À faire : 2\n- Fait : 1" in text
    assert "## Tags\n- export : 2\n- carte : 1" in text
    recent = text.split("## Lignes les plus récentes\n")[1].splitlines()[2:]
    assert recent[0].startswith("| Relance |")
    assert len(text) <= 1000


def test_dod_15_a_notion_digest_groups_the_few_valued_columns_when_none_is_declared(notion_base, mocker):
    pages = [{"properties": {"Nom": f"T{i}", "Statut": "Fait" if i % 2 else "À faire"}} for i in range(200)]
    mocker.patch("lib.notion.query_database", return_value=pages)
    text = prepared({"cap": 2000})["content"]
    assert text.startswith("200 lignes, au-delà du plafond de 2000 caractères")
    assert "## Statut\n- À faire : 100\n- Fait : 100" in text
    assert "## Nom" not in text
    with pytest.raises(ValueError, match="trop petit pour le seul décompte"):
        prepared({"cap": 1000, "group_by": ["Nom"]})


def test_dod_15_a_column_absent_from_the_base_is_named_with_the_columns_it_has(notion_base):
    with pytest.raises(ValueError, match="colonnes absentes : Priorité ; colonnes de la base : Nom, Statut"):
        prepared({"columns": ["Priorité"]})


@pytest.mark.parametrize("status", [403, 404])
def test_dod_15_an_unshared_notion_base_or_page_gives_a_clear_error(notion_base, mocker, status):
    response = httpx.Response(status, request=httpx.Request("POST", "https://api.notion.com/v1/x"))
    for target in ("lib.notion.query_database", "lib.notion.page_markdown"):
        mocker.patch(target, side_effect=httpx.HTTPStatusError("x", request=response.request, response=response))
    with pytest.raises(ValueError, match="non partagée avec l'intégration Notion d'Autometa"):
        prepared({})
    with pytest.raises(ValueError, match=f"notion page {PAGE} : introuvable ou non partagée"):
        agent_connectors.prepare({"type": "notion", "page": PAGE})


def test_dod_15_notion_without_a_token_says_so(mocker):
    mocker.patch("lib.notion.NOTION_TOKEN", "")
    with pytest.raises(ValueError, match="NOTION_TOKEN absent"):
        prepared({})


def test_dod_15_a_notion_page_is_read_to_its_depth_and_cut_to_its_cap(mocker):
    mocker.patch("lib.notion.NOTION_TOKEN", "notion-token")
    markdown = mocker.patch("lib.notion.page_markdown", return_value="# OKR\n" + "x" * 3000)
    found = agent_connectors.prepare({"type": "notion", "page": PAGE, "depth": 3, "cap": 1000})
    markdown.assert_called_once_with(PAGE, 3)
    assert found["content"].endswith("[contenu tronqué à 1000 caractères sur 3006]")
    assert notion_connector.source({"page": PAGE}) == f"page {PAGE}"


def archive(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(f"owner-repo-abc123/{path}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


REPO_FILES = {
    "README.md": "# Repo\nUne application.",
    "pyproject.toml": "[project]\nname = 'repo'",
    "app/views.py": "def view():\n    pass  # TODO: paginer\n",
    "app/deep/models.py": "# FIXME fuseau horaire\n",
    "logo.png": "\0PNG",
}


class FakeGitHub:
    """GitHub's API for public repositories: metadata, issues, commits, an archive, an owner's listing."""

    def __init__(self, mocker, private=(), repos="zba"):
        self.private, self.paths, self.repos = set(private), [], list(repos)
        mocker.patch("lib.agent_connectors.github.httpx.get", side_effect=self.get)
        mocker.patch("lib.agent_connectors.github.httpx.stream", side_effect=self.stream)

    def answer(self, path, body, status=200):
        self.paths.append(path)
        return httpx.Response(status, json=body, request=httpx.Request("GET", f"https://api.github.com/{path}"))

    def get(self, url, params=None, headers=None, timeout=None):
        path = url.removeprefix("https://api.github.com/")
        if path.startswith("orgs/") and path.endswith("/repos"):
            owner = path.split("/")[1]
            listed = [{"full_name": f"{owner}/{n}", "archived": False, "fork": False} for n in self.repos]
            return self.answer(path, listed + [{"full_name": f"{owner}/old", "archived": True}])
        if path.endswith("/issues"):
            issues = [
                {"number": 7, "title": "Bug", "labels": [{"name": "bug"}]},
                {"number": 8, "title": "PR", "pull_request": {}},
            ]
            return self.answer(path, issues)
        if path.endswith("/commits"):
            return self.answer(
                path,
                [
                    {
                        "sha": "abcdef123",
                        "commit": {"committer": {"date": "2026-11-01T00:00:00Z"}, "message": "Fix\n\nbody"},
                    }
                ],
            )
        repo = path.removeprefix("repos/")
        if repo == "owner/missing":
            return self.answer(path, {}, 404)
        return self.answer(
            path,
            {
                "private": repo in self.private,
                "description": "Desc",
                "language": "Python",
                "pushed_at": "2026-11-02T00:00:00Z",
            },
        )

    def stream(self, method, url, headers=None, timeout=None, follow_redirects=None):
        self.paths.append(url.removeprefix("https://api.github.com/"))
        return contextlib.nullcontext(
            httpx.Response(200, content=archive(REPO_FILES), request=httpx.Request("GET", url))
        )


def test_dod_15_a_github_repository_is_condensed_from_its_archive_and_its_api(mocker):
    fake = FakeGitHub(mocker)
    mocker.patch("lib.agent_connectors.github.config.GITHUB_TOKEN", "")
    text = agent_connectors.prepare({"type": "github", "repos": ["owner/repo"]})["content"]
    assert text.startswith("Dépôts lus ce run : owner/repo.")
    assert "Desc · Python · dernière activité 2026-11-02" in text
    assert "## README\n# Repo\nUne application." in text
    assert "- issue #7 Bug [bug]\n- PR #8 PR" in text
    assert "- abcdef1 2026-11-01 Fix" in text
    assert "### pyproject.toml\n```\n[project]" in text
    assert "app/views.py:2: pass  # TODO: paginer" in text
    assert "app/deep/models.py:1: # FIXME fuseau horaire" in text
    tree = text.split("## Arborescence (deux niveaux)\n")[1].splitlines()
    assert "app/views.py" in tree and "app/deep/models.py" not in tree
    assert "logo.png" in tree
    assert fake.paths == [
        "repos/owner/repo",
        "repos/owner/repo/issues",
        "repos/owner/repo/commits",
        "repos/owner/repo/tarball",
    ]


def test_dod_15_github_sends_autometa_token_only_when_there_is_one(mocker):
    mocker.patch("lib.agent_connectors.github.config.GITHUB_TOKEN", "gh-token")
    assert github.headers()["Authorization"] == "Bearer gh-token"
    mocker.patch("lib.agent_connectors.github.config.GITHUB_TOKEN", "")
    assert "Authorization" not in github.headers()


@pytest.mark.parametrize(
    ("repo", "message"),
    [("owner/secret", "dépôt privé, seuls les dépôts publics sont lus"), ("owner/missing", "dépôt introuvable")],
)
def test_dod_15_a_private_or_unknown_repository_is_refused(mocker, repo, message):
    FakeGitHub(mocker, private={"owner/secret"})
    with pytest.raises(ValueError, match=message):
        agent_connectors.prepare({"type": "github", "repos": [repo]})


def test_dod_15_an_organisation_follows_the_named_repositories_without_archives_or_forks(mocker):
    FakeGitHub(mocker)
    condensed = mocker.patch("lib.agent_connectors.github.condense", side_effect=lambda d, cap: f"# {d}")
    found = agent_connectors.prepare({"type": "github", "repos": ["owner/z"], "organization": "owner"})
    assert [c.args[0] for c in condensed.call_args_list] == ["owner/z", "owner/a", "owner/b"]
    assert found["source"] == "owner/z, owner"


def test_dod_15_repositories_beyond_the_total_cap_move_to_the_next_runs(mocker):
    mocker.patch("lib.agent_connectors.github.condense", side_effect=lambda d, cap: f"# {d}\n" + "x" * 2000)
    repos = ["o/a", "o/b", "o/c"]
    text, next_cursor = github.condense_all(repos, 0, 6000, 10000)
    assert text.startswith("Dépôts lus ce run : o/a, o/b ; le prochain run reprend à o/c.")
    assert next_cursor == 2
    text, next_cursor = github.condense_all(repos, 2, 2000, 10000)
    assert text.startswith("Dépôts lus ce run : o/c, o/a, o/b.")
    assert next_cursor == 2
    text, _ = github.condense_all(repos, 0, 9000, 1000)
    assert text.startswith("Dépôts lus ce run : o/a ;")


def test_dod_15_github_unreachable_or_rate_limited_launches_no_run(mocker):
    mocker.patch("lib.agent_connectors.github.httpx.get", side_effect=httpx.ConnectError("refusé"))
    with pytest.raises(ValueError, match="GitHub injoignable ou limite de débit atteinte"):
        agent_connectors.prepare({"type": "github", "repos": ["owner/repo"]})


def addresses(*ips):
    return lambda host, port, proto: [(socket.AF_INET, socket.SOCK_STREAM, proto, "", (ip, port)) for ip in ips]


PUBLIC = "93.184.215.14"


class Site:
    """An https site behind httpx's MockTransport: records each request as sent on the wire."""

    def __init__(self, mocker, response):
        self.requests, self.response = [], response
        transport = httpx.MockTransport(self.handle)
        mocker.patch("lib.agent_connectors.url.client", lambda: httpx.Client(transport=transport, timeout=30))

    def handle(self, request):
        self.requests.append(request)
        return self.response


def read_url(url="https://example.org/x", cap=1000):
    return agent_connectors.prepare({"type": "url", "url": url, "cap": cap})


@pytest.mark.parametrize("ip", ["10.0.0.4", "127.0.0.1", "169.254.169.254"])
def test_dod_15_a_url_resolving_to_a_private_address_is_never_fetched(mocker, ip):
    mocker.patch("lib.agent_connectors.url.socket.getaddrinfo", side_effect=addresses(PUBLIC, ip))
    site = Site(mocker, httpx.Response(200, text="x"))
    with pytest.raises(ValueError, match="ne résout pas vers une adresse publique"):
        read_url()
    assert site.requests == []


def test_dod_15_a_name_rebound_to_a_private_address_after_the_check_is_never_connected_to(mocker):
    """DNS rebinding: public when checked, private afterwards; the request goes to the checked address."""
    resolve = mocker.patch(
        "lib.agent_connectors.url.socket.getaddrinfo",
        side_effect=[addresses(PUBLIC)(0, 443, 6), addresses("10.0.0.4")(0, 443, 6)],
    )
    site = Site(mocker, httpx.Response(200, text="content", headers={"content-type": "text/plain"}))
    assert read_url("https://example.org:8443/notes?v=1")["content"] == "content"
    assert resolve.call_count == 1
    (request,) = site.requests
    assert str(request.url) == f"https://{PUBLIC}:8443/notes?v=1"
    assert request.headers["host"] == "example.org:8443"
    assert request.extensions["sni_hostname"] == "example.org"


def test_dod_15_an_ipv6_address_is_pinned_in_brackets():
    assert url_connector.pinned("https://example.org/a", "2606:4700::1") == "https://[2606:4700::1]/a"


@pytest.mark.parametrize(
    ("content_type", "body", "expected"),
    [
        (
            "text/html; charset=utf-8",
            "<html><style>p{}</style><h1>Notes</h1><p>Un  point</p></html>",
            "Notes\nUn point",
        ),
        ("text/markdown", "# Notes\n- un point", "# Notes\n- un point"),
    ],
)
def test_dod_15_a_public_url_is_read_as_text(mocker, content_type, body, expected):
    mocker.patch("lib.agent_connectors.url.socket.getaddrinfo", side_effect=addresses(PUBLIC))
    Site(mocker, httpx.Response(200, text=body, headers={"content-type": content_type}))
    assert read_url() == {"source": "https://example.org/x", "content": expected}


def chunks(size, count):
    yield from (b"x" * size for _ in range(count))


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, headers={"content-type": "text/plain", "content-length": "10001"}, content=b"x"),
        httpx.Response(200, headers={"content-type": "text/plain"}, content=chunks(4000, 1000)),
    ],
)
def test_dod_15_a_url_answer_beyond_ten_times_the_cap_is_refused_without_reading_it_all(mocker, response):
    mocker.patch("lib.agent_connectors.url.socket.getaddrinfo", side_effect=addresses(PUBLIC))
    Site(mocker, response)
    with pytest.raises(ValueError, match="réponse de plus de 10000 octets, rien n'est lu"):
        read_url(cap=1000)


def test_dod_15_a_url_answer_within_its_byte_budget_is_read_then_cut_to_the_cap(mocker):
    mocker.patch("lib.agent_connectors.url.socket.getaddrinfo", side_effect=addresses(PUBLIC))
    Site(mocker, httpx.Response(200, headers={"content-type": "text/plain"}, content=chunks(2500, 4)))
    assert read_url(cap=1000)["content"].endswith("[contenu tronqué à 1000 caractères sur 10000]")


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"}), "contenu application/pdf"),
        (httpx.Response(302, headers={"location": "http://10.0.0.1"}), "lecture impossible"),
        (httpx.Response(500), "lecture impossible"),
    ],
)
def test_dod_15_a_url_that_is_not_text_or_answers_badly_launches_no_run(mocker, response, message):
    mocker.patch("lib.agent_connectors.url.socket.getaddrinfo", side_effect=addresses(PUBLIC))
    site = Site(mocker, response)
    with pytest.raises(ValueError, match=message):
        read_url()
    assert len(site.requests) == 1


def test_dod_15_an_unresolvable_host_is_not_public(mocker):
    mocker.patch("lib.agent_connectors.url.socket.getaddrinfo", side_effect=socket.gaierror)
    assert url_connector.public_address("nulle-part.invalid") is None


def test_dod_15_every_preparation_is_cut_to_its_cap(mocker):
    mocker.patch(
        "lib.agent_connectors.cron.cron.get_app_runs", return_value=[{"status": "success", "output": "y" * 5000}]
    )
    found = agent_connectors.prepare({"type": "cron", "task": "sync-tags", "cap": 1000})
    assert len(found["content"]) < 1100
    assert found["content"].endswith("[contenu tronqué à 1000 caractères sur 5000]")


def test_dod_15_the_configuration_accepts_five_preparations_of_any_types(mocker):
    steps = [
        {"type": "notion", "base": BASE},
        {"type": "notion", "page": PAGE},
        {"type": "github", "organization": "owner"},
        {"type": "url", "url": "https://example.org"},
        {"type": "cron", "task": "sync-tags"},
    ]
    doc = {
        "format": "pdi.agent/1",
        "slug": "veille-x",
        "title": "Veille",
        "mission": "Suivre ce qui bouge dans les sources déclarées.",
        "destinations": [],
        "files": ["notes.md"],
        "preparations": steps,
    }
    assert agent_config.validate(doc) == []
    assert json.dumps(agent_config.describe(doc), ensure_ascii=False).count("préparation") == 5


def test_dod_15_an_owner_that_is_a_user_is_listed_and_an_unknown_one_is_named(mocker):
    def get(path, **params):
        if path.startswith("orgs/"):
            request = httpx.Request("GET", f"https://api.github.com/{path}")
            raise httpx.HTTPStatusError("404", request=request, response=httpx.Response(404, request=request))
        if path == "users/someone/repos":
            return [{"full_name": "someone/tool"}, {"full_name": "someone/fork", "fork": True}]
        request = httpx.Request("GET", f"https://api.github.com/{path}")
        raise httpx.HTTPStatusError("404", request=request, response=httpx.Response(404, request=request))

    mocker.patch("lib.agent_connectors.github.get", side_effect=get)
    assert github.organization_repos("someone") == ["someone/tool"]
    with pytest.raises(ValueError, match="propriétaire personne introuvable"):
        github.organization_repos("personne")
