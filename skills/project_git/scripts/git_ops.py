"""Git operations for expert-mode projects.

Usage:
    python -m skills.project_git.scripts.git_ops init --project-id <uuid>
    python -m skills.project_git.scripts.git_ops push --project-id <uuid> -m "message"
    python -m skills.project_git.scripts.git_ops status --project-id <uuid>
    python -m skills.project_git.scripts.git_ops branch --project-id <uuid> --name <name>
"""

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from web import config
from web.database import store
from lib.gitea import GiteaClient


def get_workdir(project_id: str) -> Path:
    """Get the working directory for a project."""
    return config.PROJECTS_DIR / project_id


def _authenticated_clone_url(repo_full_name: str) -> str:
    """Build an authenticated HTTP clone URL for Gitea."""
    base = config.GITEA_URL.rstrip("/")
    parts = urlsplit(base)
    token = quote(config.GITEA_API_TOKEN or "", safe="")
    netloc = f"{token}@{parts.netloc}" if token else parts.netloc
    base_path = parts.path.rstrip("/")
    clone_path = f"{base_path}/{repo_full_name}.git" if base_path else f"/{repo_full_name}.git"
    return urlunsplit((parts.scheme, netloc, clone_path, "", ""))


def cmd_init(args):
    """Initialize a Gitea repo for a project."""
    project = store.get_project(args.project_id)
    if not project:
        print(f"Error: Project {args.project_id} not found", file=sys.stderr)
        sys.exit(1)

    workdir = get_workdir(project.id)
    gt = GiteaClient()

    # Create Gitea repo if it doesn't exist yet
    if not project.gitea_repo_id:
        print(f"Creating Gitea repo: {project.name}")
        gt_repo = gt.create_repo(
            name=project.slug,
            description=project.description or f"Expert-mode app: {project.name}",
        )
        gitea_url = gt_repo.get("html_url", "")
        gitea_id = gt_repo["id"]
        full_name = gt_repo.get("full_name", "")

        store.update_project(
            project.id,
            gitea_repo_id=gitea_id,
            gitea_url=gitea_url,
            status="active",
        )
        print(f"Gitea repo created: {gitea_url}")
    else:
        print(f"Project already has a Gitea repo: {project.gitea_url}")
        # Derive full_name from gitea_url (e.g. http://host:3300/apps/slug -> apps/slug)
        path = (project.gitea_url or "").split("://", 1)[-1].split("/", 1)[-1]
        full_name = path.rstrip("/")

    # Clone locally if not already cloned
    if not (workdir / ".git").exists():
        clone_url = _authenticated_clone_url(full_name)
        workdir.mkdir(parents=True, exist_ok=True)
        print(f"Cloning to {workdir}")
        subprocess.run(
            ["git", "clone", clone_url, str(workdir)],
            check=True, capture_output=True,
        )
        # Configure git user for commits
        subprocess.run(
            ["git", "config", "user.email", "matometa@localhost"],
            cwd=workdir, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Matometa"],
            cwd=workdir, check=True, capture_output=True,
        )
    else:
        print(f"Already cloned at {workdir}")

    # Push spec as CLAUDE.md
    if project.spec:
        claude_md = workdir / "CLAUDE.md"
        claude_md.write_text(project.spec)
        subprocess.run(["git", "add", "CLAUDE.md"], cwd=workdir, check=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--stat"],
            cwd=workdir, capture_output=True, text=True,
        )
        if result.stdout.strip():
            subprocess.run(
                ["git", "commit", "-m", "Add project spec as CLAUDE.md"],
                cwd=workdir, check=True, capture_output=True,
            )
            subprocess.run(["git", "push"], cwd=workdir, check=True, capture_output=True)
            print("Pushed spec as CLAUDE.md")


def cmd_push(args):
    """Commit and push changes."""
    project = store.get_project(args.project_id)
    if not project:
        print(f"Error: Project {args.project_id} not found", file=sys.stderr)
        sys.exit(1)

    workdir = get_workdir(project.id)
    if not workdir.exists():
        print(f"Error: Working directory {workdir} does not exist", file=sys.stderr)
        sys.exit(1)

    message = args.message or "Update project files"

    subprocess.run(["git", "add", "-A"], cwd=workdir, check=True)
    result = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
        cwd=workdir, capture_output=True, text=True,
    )
    if not result.stdout.strip():
        print("Nothing to commit")
        return

    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=workdir, check=True,
    )
    subprocess.run(["git", "push"], cwd=workdir, check=True)
    print(f"Pushed: {message}")


def cmd_status(args):
    """Show git status and recent commits."""
    project = store.get_project(args.project_id)
    if not project:
        print(f"Error: Project {args.project_id} not found", file=sys.stderr)
        sys.exit(1)

    workdir = get_workdir(project.id)
    if not workdir.exists():
        print(f"Working directory {workdir} does not exist")
        return

    print("=== git status ===")
    subprocess.run(["git", "status", "--short"], cwd=workdir)
    print("\n=== Recent commits ===")
    subprocess.run(
        ["git", "log", "--oneline", "-10"],
        cwd=workdir,
    )


def cmd_branch(args):
    """Create a new branch."""
    project = store.get_project(args.project_id)
    if not project:
        print(f"Error: Project {args.project_id} not found", file=sys.stderr)
        sys.exit(1)

    workdir = get_workdir(project.id)
    subprocess.run(
        ["git", "checkout", "-b", args.name],
        cwd=workdir, check=True,
    )
    print(f"Created and switched to branch: {args.name}")


def main():
    parser = argparse.ArgumentParser(description="Git operations for expert-mode projects")
    subparsers = parser.add_subparsers(dest="command")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize Gitea repo")
    init_parser.add_argument("--project-id", required=True)

    # push
    push_parser = subparsers.add_parser("push", help="Commit and push")
    push_parser.add_argument("--project-id", required=True)
    push_parser.add_argument("-m", "--message", default=None)

    # status
    status_parser = subparsers.add_parser("status", help="Show git status")
    status_parser.add_argument("--project-id", required=True)

    # branch
    branch_parser = subparsers.add_parser("branch", help="Create branch")
    branch_parser.add_argument("--project-id", required=True)
    branch_parser.add_argument("--name", required=True)

    args = parser.parse_args()

    commands = {
        "init": cmd_init,
        "push": cmd_push,
        "status": cmd_status,
        "branch": cmd_branch,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
