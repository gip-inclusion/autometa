"""Git + quality gate helpers for recettes (testing existing PDI apps).

Security model:
- Agent works on a Gitea mirror (origin) -- can push freely there
- GitHub is only an 'upstream' remote (public, read-only, no token)
- Only the guarded PR pipeline can push to GitHub (via route handler)
- Agent NEVER has GITHUB_TOKEN in its env
"""

import logging
import subprocess
from pathlib import Path
from urllib.parse import quote

from lib.expert_git import authenticated_clone_url, ensure_git_identity, run_git
from web import config

logger = logging.getLogger(__name__)


def clone_repo(github_repo: str, slug: str, dest: Path) -> None:
    """Clone a GitHub repo and mirror it to Gitea for safe agent access."""
    if (dest / ".git").exists():
        run_git(dest, "fetch", "origin")
        return

    dest.mkdir(parents=True, exist_ok=True)

    from lib.gitea import GiteaClient
    gitea = GiteaClient()
    repo_name = f"recette-{slug}"
    try:
        gitea.create_repo(name=repo_name, description=f"Mirror of {github_repo}")
    except Exception as e:
        if "409" not in str(e):
            raise

    github_url = f"https://{quote(config.GITHUB_TOKEN, safe='')}@github.com/{github_repo}.git"
    subprocess.run(
        ["git", "clone", "--depth", "1", github_url, str(dest)],
        check=True, capture_output=True, text=True, timeout=300,
    )
    ensure_git_identity(dest)

    gitea_url = authenticated_clone_url(f"{config.GITEA_ORG}/{repo_name}")
    run_git(dest, "remote", "set-url", "origin", gitea_url)
    run_git(dest, "remote", "add", "upstream", f"https://github.com/{github_repo}.git")

    try:
        run_git(dest, "push", "origin", "--all", timeout=120)
    except Exception:
        logger.warning("Initial push to Gitea failed (may be empty repo)")

    logger.info("Cloned %s -> Gitea %s, workdir %s", github_repo, repo_name, dest)


def checkout_branch(workdir: Path, branch: str) -> None:
    """Fetch and checkout a branch (from upstream if not on origin)."""
    try:
        run_git(workdir, "fetch", "origin", branch, timeout=60)
        run_git(workdir, "checkout", branch)
    except Exception:
        try:
            run_git(workdir, "fetch", "upstream", branch, timeout=60)
            run_git(workdir, "checkout", "-b", branch, f"upstream/{branch}")
        except Exception:
            run_git(workdir, "checkout", "-b", branch)


def create_worktree(workdir: Path, branch: str, worktree_path: Path) -> None:
    """Create a git worktree for the B side of A/B comparison."""
    remote_exists = False
    for remote in ("upstream", "origin"):
        try:
            run_git(workdir, "fetch", remote, branch, timeout=60)
            remote_exists = True
            break
        except Exception:
            continue

    if remote_exists:
        try:
            run_git(workdir, "branch", branch, f"{remote}/{branch}")
        except Exception:
            pass
        run_git(workdir, "worktree", "add", str(worktree_path), branch)
    else:
        run_git(workdir, "worktree", "add", "-b", branch, str(worktree_path))


def remove_worktree(workdir: Path, worktree_path: Path) -> None:
    """Remove a git worktree."""
    try:
        run_git(workdir, "worktree", "remove", str(worktree_path), "--force")
    except Exception:
        logger.warning("Failed to remove worktree %s", worktree_path)


def run_quality_checks(workdir: Path) -> dict:
    """Run quality checks using the repo's Makefile (make quality)."""
    for cmd in [["make", "quality"], ["ruff", "check", "."]]:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, cwd=str(workdir),
        )
        if result.returncode == 0:
            return {"status": "passed", "output": result.stdout[-2000:]}
        if cmd[0] == "make" and "No rule to make target" not in result.stderr:
            return {"status": "failed", "output": (result.stdout + result.stderr)[-2000:]}

    return {"status": "failed", "output": "No quality tool found (make quality / ruff)"}


def rebase_on_main(workdir: Path, branch: str) -> dict:
    """Fetch main from upstream (GitHub) and rebase branch onto it."""
    try:
        run_git(workdir, "fetch", "upstream", "main", timeout=60)
        run_git(workdir, "checkout", branch)
        run_git(workdir, "rebase", "upstream/main")
        return {"status": "ok", "output": "Rebase successful"}
    except Exception as e:
        try:
            run_git(workdir, "rebase", "--abort")
        except Exception:
            pass
        return {"status": "conflict", "output": str(e)}


def get_diff_summary(workdir: Path, branch: str) -> dict:
    """Get a diff summary of branch vs upstream/main for review."""
    try:
        run_git(workdir, "fetch", "upstream", "main", timeout=60)
        stat = run_git(workdir, "diff", "--stat", f"upstream/main...{branch}")
        diff = run_git(workdir, "diff", f"upstream/main...{branch}")
        return {"stat": stat, "diff": diff[-5000:]}
    except Exception as e:
        return {"stat": "", "diff": f"Error: {e}"}


def push_and_create_pr(recette, title: str, body: str) -> str:
    """Push branch to GitHub and create a PR."""
    if recette.pr_status != "rebased":
        raise ValueError(
            f"Cannot create PR: pr_status is '{recette.pr_status}', expected 'rebased'. "
            "Run quality checks and rebase first."
        )
    if not recette.branch_b:
        raise ValueError("No branch B set")

    workdir = config.RECETTES_DIR / f"{recette.id}-b"
    if not workdir.exists():
        workdir = config.RECETTES_DIR / recette.id

    auth_url = f"https://{quote(config.GITHUB_TOKEN, safe='')}@github.com/{recette.github_repo}.git"
    public_url = f"https://github.com/{recette.github_repo}.git"
    run_git(workdir, "remote", "set-url", "upstream", auth_url)
    try:
        run_git(workdir, "push", "upstream", recette.branch_b, "--force-with-lease", timeout=60)
    finally:
        run_git(workdir, "remote", "set-url", "upstream", public_url)

    from web.github import GitHubClient
    client = GitHubClient(token=config.GITHUB_TOKEN, repo=recette.github_repo)
    pr_url = client.create_pr(title=title, branch=recette.branch_b, body=body)

    logger.info("Created PR %s for recette %s", pr_url, recette.slug)
    return pr_url
