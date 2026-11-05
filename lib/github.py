"""Lecture seule des dépôts publics des organisations de l'inclusion sur GitHub : API et copies superficielles anonymes."""

import fcntl
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

import httpx

from lib.attestation import git_env
from web import config

logger = logging.getLogger(__name__)

ORGS = ("gip-inclusion", "betagouv", "numerique-gouv", "suitenumerique")
JSON = "application/vnd.github+json"
RAW = "application/vnd.github.raw+json"


class GitHubError(Exception):
    """Échec d'une lecture GitHub, avec un message qui dit quoi en conclure."""


def repository(name: str) -> str:
    """Le dépôt `org/nom` normalisé, s'il appartient à une organisation permise."""
    org, _, repo = str(name).strip("/").lower().partition("/")
    if org not in ORGS or not re.fullmatch(r"[\w.-]+", repo) or repo in (".", ".."):
        raise ValueError(f"{name} : seuls les dépôts des organisations {', '.join(ORGS)} sont permis")
    return f"{org}/{repo}"


def reference(ref: str | None) -> str | None:
    """Une branche, une étiquette ou un SHA, refusé si git pouvait y lire une option ou un motif de références."""
    if ref is not None and (not re.fullmatch(r"[\w./-]+", ref) or ref.startswith("-")):
        raise ValueError(f"{ref} : référence invalide, attendu une branche, une étiquette ou un SHA complet")
    return ref


def repository_of(path: str) -> str:
    """Le dépôt visé par un chemin `repos/org/nom/…` de l'API REST."""
    parts = str(path).strip("/").split("/")
    if parts[0] != "repos" or len(parts) < 3 or ".." in parts:
        raise ValueError(f"{path} : seuls les chemins repos/<org>/<dépôt>/… sont permis")
    return repository("/".join(parts[1:3]))


def request(method: str, path: str, accept: str = JSON, timeout: int = 30, **kwargs) -> httpx.Response:
    """Un appel à l'API GitHub, avec le jeton s'il existe ; un échec devient une GitHubError qui dit quoi en conclure."""
    try:
        # Why: un jeton expiré ou révoqué ne doit pas couper la lecture des dépôts publics.
        for token in dict.fromkeys([config.GITHUB_TOKEN, ""]):
            headers = {"Accept": accept} | ({"Authorization": f"Bearer {token}"} if token else {})
            response = httpx.request(
                method,
                f"https://api.github.com/{path}",
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
                **kwargs,
            )
            if response.status_code != 401:
                break
            logger.warning("GitHub refuse GITHUB_TOKEN (expiré ou révoqué) : nouvel essai sans jeton")
    except httpx.RequestError as e:
        raise GitHubError(f"GitHub injoignable ({type(e).__name__}) : panne réseau, pas un refus d'accès") from e
    if response.status_code == 404:
        raise GitHubError(f"{path} : introuvable (absent, privé, ou absent de cette référence)")
    if response.status_code in (403, 429) and response.headers.get("x-ratelimit-remaining") == "0":
        reset = datetime.fromtimestamp(int(response.headers["x-ratelimit-reset"]), UTC)
        raise GitHubError(f"quota de l'API GitHub épuisé jusqu'à {reset:%H:%M} UTC : chercher dans un clone (grep)")
    if response.is_error:
        raise GitHubError(f"GitHub {response.status_code} sur {path} : {response.text[:200]}")
    return response


def public(repo: str) -> dict:
    """Les métadonnées du dépôt, s'il est public."""
    meta = request("GET", f"repos/{repo}").json()
    if meta["private"]:
        raise GitHubError(f"{repo} est privé : seuls les dépôts publics sont lisibles")
    return meta


def api(path: str, params: dict | None = None, raw: bool = False, timeout: int = 30):
    """GET sur un chemin `repos/org/nom/…` d'un dépôt public permis : le JSON, ou le texte brut d'un fichier si `raw`."""
    repo = repository_of(path)
    # Why: le jeton peut voir des dépôts privés, et ce qui est lu peut être publié ; sans jeton, GitHub les cache déjà.
    if config.GITHUB_TOKEN:
        public(repo)
    response = request("GET", path.strip("/"), RAW if raw else JSON, timeout, params=params)
    return response.text if raw else response.json()


def read(repo: str, path: str, ref: str | None = None) -> str:
    """Le contenu d'un fichier, à `ref` ou sur la branche par défaut."""
    return api(f"repos/{repository(repo)}/contents/{quote(path.strip('/'))}", {"ref": ref} if ref else None, raw=True)


def pulls(repo: str, state: str = "open", commit: str | None = None, max_results: int = 30) -> list[dict]:
    """Les pull requests du dépôt, ou celles qui contiennent `commit`, des plus récemment modifiées aux plus anciennes."""
    repo = repository(repo)
    if commit:
        items = api(f"repos/{repo}/commits/{commit}/pulls")
    else:
        params = {"state": state, "sort": "updated", "direction": "desc", "per_page": min(max_results, 100)}
        items = api(f"repos/{repo}/pulls", params)
    return [summary(pr) for pr in items[:max_results]]


def summary(pr: dict) -> dict:
    return {
        "number": pr["number"],
        "title": pr["title"],
        "state": pr["state"],
        "draft": pr.get("draft"),
        "merged_at": pr.get("merged_at"),
        "author": (pr.get("user") or {}).get("login"),
        "updated_at": pr["updated_at"],
        "base": pr["base"]["ref"],
        "url": pr["html_url"],
    }


def pull(repo: str, number: int) -> dict:
    """Une pull request, sa description et la liste de ses fichiers modifiés."""
    repo = repository(repo)
    pr = api(f"repos/{repo}/pulls/{number}")
    files = api(f"repos/{repo}/pulls/{number}/files", {"per_page": 100})
    return {
        **summary(pr),
        "body": pr["body"],
        "merge_commit": pr.get("merge_commit_sha"),
        "head": pr["head"]["ref"],
        "files": [{k: f[k] for k in ("filename", "status", "additions", "deletions")} for f in files],
    }


def log(
    repo: str, path: str | None = None, ref: str | None = None, since: str | None = None, max_results: int = 30
) -> list[dict]:
    """Les commits de `ref`, du plus récent au plus ancien, éventuellement limités à un chemin ou à une date."""
    params = {"per_page": min(max_results, 100), "sha": ref, "path": path, "since": since}
    commits = api(f"repos/{repository(repo)}/commits", {key: value for key, value in params.items() if value})
    return [
        {
            "commit": c["sha"],
            "date": c["commit"]["committer"]["date"][:10],
            "author": c["commit"]["author"]["name"],
            "subject": c["commit"]["message"].partition("\n")[0],
        }
        for c in commits
    ]


def show(repo: str, commit: str, path: str | None = None) -> dict:
    """Message et diff d'un commit, éventuellement limités aux fichiers sous `path`."""
    data = api(f"repos/{repository(repo)}/commits/{commit}")
    return {
        "commit": data["sha"],
        "date": data["commit"]["committer"]["date"][:10],
        "author": data["commit"]["author"]["name"],
        "message": data["commit"]["message"],
        "files": [
            {key: f.get(key) for key in ("filename", "status", "additions", "deletions", "patch")}
            for f in data["files"]
            if not path or f"{f['filename']}/".startswith(f"{path.rstrip('/')}/")
        ],
    }


def blame(repo: str, path: str, ref: str | None = None) -> list[dict]:
    """Pour chaque ligne du fichier, le dernier commit qui l'a modifiée."""
    repo = repository(repo)
    if not config.GITHUB_TOKEN:
        raise GitHubError("blame passe par l'API GraphQL de GitHub, qui exige GITHUB_TOKEN")
    public(repo)
    owner, name = repo.split("/")
    query = """query($owner: String!, $name: String!, $ref: String!, $path: String!) {
      repository(owner: $owner, name: $name) { object(expression: $ref) { ... on Commit { oid blame(path: $path) {
        ranges { startingLine endingLine commit { oid committedDate messageHeadline author { name } } } } } } } }"""
    variables = {"owner": owner, "name": name, "ref": ref or "HEAD", "path": path}
    body = request("POST", "graphql", json={"query": query, "variables": variables}).json()
    if body.get("errors"):
        raise GitHubError(f"blame de {path} : {body['errors'][0]['message']}")
    found = body["data"]["repository"]["object"]
    if not found:
        raise GitHubError(f"{ref} : référence introuvable dans {repo}")
    contents = request("GET", f"repos/{repo}/contents/{quote(path)}", RAW, params={"ref": found["oid"]}).text
    # Why: GitHub numérote les lignes aux seuls \n ; splitlines() couperait aussi aux \f, \x1c ou \u2028.
    lines = contents.replace("\r\n", "\n").split("\n")
    return [
        {
            "line": number,
            "commit": r["commit"]["oid"],
            "date": r["commit"]["committedDate"][:10],
            "author": r["commit"]["author"]["name"],
            "summary": r["commit"]["messageHeadline"],
            "text": lines[number - 1],
        }
        for r in found["blame"]["ranges"]
        for number in range(r["startingLine"], r["endingLine"] + 1)
    ]


def git(cwd: Path, *args: str, ok: tuple[int, ...] = (0,), timeout: int = 120) -> str:
    """Git sans identifiants : un dépôt privé ou absent échoue au lieu de demander un mot de passe."""
    # Why: un lien symbolique extrait tel quel ferait lire à l'agent un fichier du conteneur (/app/.env, /proc/…).
    command = ("git", "-c", "credential.helper=", "-c", "core.symlinks=false", "-C", str(cwd), *args)
    env = git_env() | {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": ""}
    try:
        done = subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=timeout, env=env)
    except subprocess.TimeoutExpired as e:
        raise GitHubError(f"git {args[0]} : pas de réponse en {timeout} s") from e
    if done.returncode not in ok:
        error = done.stderr.strip()
        if "could not read Username" in error:
            error = "dépôt absent ou privé (le clone est anonyme : seuls les dépôts publics sont lisibles)"
        raise GitHubError(f"git {args[0]} : {error}")
    return done.stdout


def workspace() -> Path:
    """Dossier des clones de la conversation, partagé par ses sous-agents."""
    return Path(tempfile.gettempdir()) / (config.agent_conversation_id() or "autometa") / "github"


def clone(repo: str, root: Path, ref: str | None = None) -> tuple[Path, str]:
    """Copie anonyme et superficielle du dépôt, extraite à `ref` : le chemin et le commit."""
    repo, ref = repository(repo), reference(ref)
    # Why: une copie par référence, pour qu'un sous-agent n'extraie pas une autre référence sous les pieds d'un autre.
    path = root / (f"{repo}@{quote(ref, safe='')}" if ref else repo)
    path.mkdir(parents=True, exist_ok=True)
    # Why: avant le fetch, pour que le ménage d'une autre conversation ne prenne pas une copie rafraîchie pour oubliée.
    os.utime(path)
    with open(path.parent / f".{path.name}.lock", "w") as lock:
        # Why: les sous-agents d'une conversation partagent les clones et peuvent les demander en même temps.
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not (path / ".git").exists():
            git(path, "init", "-q")
            git(path, "remote", "add", "origin", f"https://github.com/{repo}.git")
        # Why: une copie complète coûte trois fois plus de mémoire au conteneur ; l'historique passe par l'API.
        git(path, "fetch", "-q", "--depth", "1", "origin", ref or "HEAD", timeout=600)
        git(path, "checkout", "-q", "--detach", "--force", "FETCH_HEAD")
        commit = git(path, "rev-parse", "HEAD").strip()
    return path, commit


def sweep(max_age: int = 86400) -> None:
    """Supprime les clones inutilisés depuis `max_age` secondes, toutes conversations confondues."""
    for org in ORGS:
        for path in Path(tempfile.gettempdir()).glob(f"*/github/{org}/*"):
            if path.is_dir() and time.time() - path.stat().st_mtime > max_age:
                # Why: les ménages de deux conversations peuvent viser le même clone en même temps.
                shutil.rmtree(path, ignore_errors=True)


def grep(path: Path, pattern: str, glob: str | None = None, ignore_case: bool = False, max_results: int = 200) -> dict:
    """Les lignes d'un clone extrait qui correspondent à l'expression régulière étendue `pattern`."""
    flags = ["-i"] if ignore_case else []
    command = ("git", "-C", str(path), "grep", "-n", "-I", "-E", "--null", *flags, "-e", pattern, "--")
    total, matches = 0, []
    # Why: un motif trop large sort des centaines de Mo ; lues au fil de l'eau, seules les premières lignes restent en mémoire.
    with subprocess.Popen(
        (*command, *([glob] if glob else [])), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=git_env()
    ) as process:
        for line in process.stdout:
            total += 1
            if total <= max_results:
                file, number, text = line.decode(errors="replace").rstrip("\r\n").split("\0", 2)
                matches.append({"path": file, "line": int(number), "text": text[:300]})
        error = process.stderr.read().decode(errors="replace").strip()
    if process.returncode not in (0, 1):
        raise GitHubError(f"git grep : {error}")
    return {"total": total, "matches": matches}
