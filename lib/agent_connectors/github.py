"""Preparation github: a condensed view of public repositories named in the agent's configuration, by repository or organisation."""

import re
import tarfile
import tempfile
from typing import Any

import httpx

from lib.agent_connectors import bounded_int
from web import config

DESCRIPTION = (
    "un condensé de dépôts GitHub publics (README, configuration, TODO et FIXME, issues et PR ouvertes, derniers "
    "commits, arborescence) ; au-delà du plafond, les dépôts suivants passent au run suivant"
)
FIELDS = {
    "repos": "liste de dépôts proprietaire/depot, lus d'abord et dans cet ordre (50 au plus)",
    "organization": "un propriétaire GitHub : ses dépôts publics non archivés suivent, par ordre alphabétique",
    "repo_cap": "facultatif, taille d'un dépôt en caractères, 2000 à 60000, 30000 par défaut",
}
OWNER = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})"
REPO = OWNER + r"/[A-Za-z0-9._-]{1,100}"

API = "https://api.github.com"
CONFIG_FILES = (
    "pyproject.toml",
    "package.json",
    "requirements.txt",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "Procfile",
    "setup.cfg",
)
TODO = re.compile(r"\b(TODO|FIXME)\b")
# Why: bounds on what one repository may cost Autometa: the archive on disk, a file read for TODO, the lists.
ARCHIVE_MAX = 500 * 1024 * 1024
FILE_MAX = 512 * 1024
TODO_MAX = 200
TREE_MAX = 150
ORG_MAX = 300


def headers() -> dict:
    """Why: Autometa's optional token only lifts the rate limit; public repositories are read either way."""
    token = {"Authorization": f"Bearer {config.GITHUB_TOKEN}"} if config.GITHUB_TOKEN else {}
    return {"Accept": "application/vnd.github+json", **token}


def get(path: str, **params) -> Any:
    resp = httpx.get(f"{API}/{path}", params=params, headers=headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()


def scan_archive(repo: str) -> dict:
    """Tree, README, key configuration files and TODO/FIXME of the default branch, read from its archive."""
    found = {"tree": set(), "readme": "", "configuration": {}, "todo": []}
    with tempfile.TemporaryFile() as archive:
        with httpx.stream(
            "GET", f"{API}/repos/{repo}/tarball", headers=headers(), timeout=120, follow_redirects=True
        ) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_bytes():
                if archive.tell() + len(chunk) > ARCHIVE_MAX:
                    raise ValueError(f"préparation github {repo} : archive de plus de 500 Mo, dépôt non lu")
                archive.write(chunk)
        archive.seek(0)
        with tarfile.open(fileobj=archive, mode="r|gz") as tar:
            for member in tar:
                path = member.name.partition("/")[2]
                if not path or not (member.isfile() or member.isdir()):
                    continue
                parts = path.split("/")
                if len(parts) <= 2 and len(found["tree"]) < TREE_MAX:
                    found["tree"].add(path + ("/" if member.isdir() else ""))
                handle = tar.extractfile(member) if member.size <= FILE_MAX and "node_modules" not in parts else None
                if handle is None:
                    continue
                data = handle.read()
                if b"\0" in data[:1024]:
                    continue
                text = data.decode("utf-8", errors="replace")
                if len(parts) == 1 and path.lower().startswith("readme") and not found["readme"]:
                    found["readme"] = text[:4000]
                if len(parts) == 1 and path in CONFIG_FILES:
                    found["configuration"][path] = text[:2000]
                for number, line in enumerate(text.splitlines(), 1):
                    if len(found["todo"]) < TODO_MAX and TODO.search(line):
                        found["todo"].append(f"{path}:{number}: {line.strip()[:160]}")
    return found


def condense(repo: str, cap: int) -> str:
    """One repository as Markdown, cut to cap characters; private or unknown repositories are refused."""
    try:
        meta = get(f"repos/{repo}")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise ValueError(f"préparation github {repo} : dépôt introuvable") from exc
        raise
    if meta.get("private"):
        raise ValueError(f"préparation github {repo} : dépôt privé, seuls les dépôts publics sont lus")
    issues = get(f"repos/{repo}/issues", state="open", per_page=50, sort="updated")
    commits = get(f"repos/{repo}/commits", per_page=15)
    archive = scan_archive(repo)
    lines = [
        f"# {repo}",
        f"{meta.get('description') or ''} · {meta.get('language') or 'langage inconnu'} · "
        f"dernière activité {(meta.get('pushed_at') or '')[:10]}",
        "",
        "## README",
        archive["readme"] or "(aucun)",
        "",
        f"## Issues et PR ouvertes ({len(issues)} les plus récentes)",
        *(
            f"- {'PR' if 'pull_request' in i else 'issue'} #{i['number']} {i['title']}"
            + (f" [{', '.join(label['name'] for label in i.get('labels', []))}]" if i.get("labels") else "")
            for i in issues
        ),
        "",
        "## Derniers commits",
        *(
            f"- {c['sha'][:7]} {c['commit']['committer']['date'][:10]} {c['commit']['message'].splitlines()[0]}"
            for c in commits
        ),
        "",
        "## Fichiers de configuration",
        *(f"### {name}\n```\n{text}\n```" for name, text in sorted(archive["configuration"].items())),
        "",
        f"## TODO et FIXME ({len(archive['todo'])}{' au plus' if len(archive['todo']) == TODO_MAX else ''})",
        *archive["todo"],
        "",
        "## Arborescence (deux niveaux)",
        *sorted(archive["tree"]),
    ]
    text = "\n".join(lines)
    if len(text) <= cap:
        return text
    return text[:cap] + f"\n\n[condensé tronqué à {cap} caractères sur {len(text)}]"


def condense_all(repos: list[str], cursor: int, repo_cap: int, cap: int) -> tuple[str, int]:
    """Repositories from debut, in order, while the total cap holds; returns the text and where the next run starts."""
    parts, read, i = [], [], cursor % len(repos)
    while len(read) < len(repos) and (not parts or sum(map(len, parts)) + repo_cap <= cap):
        parts.append(condense(repos[i], repo_cap))
        read.append(repos[i])
        i = (i + 1) % len(repos)
    rest = f" ; le prochain run reprend à {repos[i]}" if len(read) < len(repos) else ""
    head = f"Dépôts lus ce run : {', '.join(read)}{rest}."
    return "\n\n".join([head, *parts]), i


def errors(step: dict) -> list[str]:
    if "repos" not in step and "organization" not in step:
        return ["repos ou organization : attendu au moins l'un des deux."]
    found = []
    repos = step.get("repos", [])
    if not isinstance(repos, list) or len(repos) > 50:
        found.append("repos : attendu une liste de 50 dépôts proprietaire/depot au plus.")
    else:
        found += [
            f"repos : {d!r} n'est pas un dépôt proprietaire/depot."
            for d in repos
            if not (isinstance(d, str) and re.fullmatch(REPO, d) and ".." not in d)
        ]
    if "organization" in step and not (
        isinstance(step["organization"], str) and re.fullmatch(OWNER, step["organization"])
    ):
        found.append("organization : attendu un nom de propriétaire GitHub.")
    if "repo_cap" in step:
        found += bounded_int("repo_cap", step["repo_cap"], 2_000, 60_000)
    return found


def source(step: dict) -> str:
    return ", ".join([*step.get("repos", []), *([step["organization"]] if "organization" in step else [])])


def organization_repos(owner: str) -> list[str]:
    """Public, non-archived, non-fork repositories of an owner, by name; an organisation first, then a user."""
    names, page = [], 1
    kind = "orgs"
    while len(names) < ORG_MAX:
        try:
            batch = get(f"{kind}/{owner}/repos", type="public", per_page=100, page=page)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404 or kind == "users":
                raise ValueError(f"préparation github : propriétaire {owner} introuvable") from exc
            kind = "users"
            continue
        names += [r["full_name"] for r in batch if not (r.get("archived") or r.get("fork") or r.get("private"))]
        if len(batch) < 100:
            break
        page += 1
    return sorted(names)[:ORG_MAX]


def prepare(step: dict, cap: int, cursor: int) -> dict:
    try:
        repos = list(step.get("repos", []))
        if "organization" in step:
            repos += [d for d in organization_repos(step["organization"]) if d not in repos]
        if not repos:
            raise ValueError(f"préparation github {source(step)} : aucun dépôt public à lire")
        text, next_cursor = condense_all(repos, cursor, step.get("repo_cap", 30_000), cap)
    except httpx.HTTPError as exc:
        raise ValueError(f"préparation github : GitHub injoignable ou limite de débit atteinte ({exc})") from exc
    return {"content": text, "next_cursor": next_cursor}
