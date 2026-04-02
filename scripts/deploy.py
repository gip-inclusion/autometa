#!/usr/bin/env python3
"""Standalone deploy CLI for expert-mode projects.

Independent of the agent — can be run manually, by cron, or via webhook.
The agent can also call this via Bash tool for troubleshooting.

Usage:
    python -m scripts.deploy list                              # List all projects
    python -m scripts.deploy status                            # All projects status
    python -m scripts.deploy status <slug-or-uuid>             # One project
    python -m scripts.deploy staging <slug-or-uuid>            # Deploy staging
    python -m scripts.deploy production <slug-or-uuid>         # Deploy production
    python -m scripts.deploy logs <slug-or-uuid> [--env ENV]   # View logs
    python -m scripts.deploy restart <slug-or-uuid> [--env ENV] # Restart
    python -m scripts.deploy stop <slug-or-uuid> [--env ENV]   # Stop
    python -m scripts.deploy validate <slug-or-uuid>           # Check compose file
    python -m scripts.deploy health                            # Health check all
    python -m scripts.deploy cleanup [--dry-run]                   # Clean unused Docker resources
    python -m scripts.deploy debug <slug-or-uuid> [--env ENV]      # Debug containers
    python -m scripts.deploy smoke <slug-or-uuid> [--env ENV]      # Browser smoke test

Note: <slug-or-uuid> accepts either project slug (e.g. gold-falcon) or UUID.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import docker_deploy
from web.database import ConversationStore


def _resolve_project(store, identifier: str):
    """Resolve a project by slug or UUID."""
    project = store.get_project_by_slug(identifier)
    if project:
        return project
    # Try as UUID (full or partial)
    project = store.get_project(identifier)
    if project:
        return project
    return None


def cmd_list(args):
    """List all projects with their slugs and IDs."""
    store = ConversationStore()
    projects = store.list_projects(limit=500)
    if not projects:
        print("No projects found")
        return 0
    print(f"{'SLUG':20s} {'ID':38s} {'STATUS':12s} {'STAGING URL'}")
    print("-" * 100)
    for p in projects:
        print(f"{p.slug:20s} {p.id:38s} {p.status or '-':12s} {p.staging_deploy_url or '-'}")
    return 0


def cmd_status(args):
    store = ConversationStore()
    if args.slug:
        project = _resolve_project(store, args.slug)
        if not project:
            print(f"Project not found: {args.slug}")
            print("Hint: use 'python -m scripts.deploy list' to see available projects")
            return 1
        for env in ("staging", "production"):
            st = docker_deploy.status(project.id, env)
            if st["status"] != "not_deployed":
                print(f"{project.slug}/{env}: {st['status']}")
                for c in st.get("containers", []):
                    print(f"  {c['name']}: {c['state']} ({c['status_text']})")
    else:
        projects = store.list_projects(limit=500)
        for project in projects:
            for env in ("staging", "production"):
                deploy_url = (project.staging_deploy_url if env == "staging"
                              else project.production_deploy_url)
                if not deploy_url:
                    continue
                st = docker_deploy.status(project.id, env)
                status = st.get("status", "unknown")
                print(f"{project.slug:20s} {env:12s} {status:15s} {deploy_url}")
    return 0


def cmd_deploy(args, environment):
    store = ConversationStore()
    project = _resolve_project(store, args.slug)
    if not project:
        print(f"Project not found: {args.slug}")
        print("Hint: use 'python -m scripts.deploy list' to see available projects")
        return 1

    print(f"Deploying {project.slug}/{environment}...")
    result = docker_deploy.deploy(project.id, environment)
    print(json.dumps(result, indent=2))
    if result["status"] not in ("running",):
        # Show container logs on failure for diagnostics
        log_text = docker_deploy.logs(project.id, environment, lines=30)
        if log_text and log_text != "No logs available":
            print(f"\n--- Container logs ({environment}) ---")
            print(log_text)
    return 0 if result["status"] == "running" else 1


def cmd_logs(args):
    store = ConversationStore()
    project = _resolve_project(store, args.slug)
    if not project:
        print(f"Project not found: {args.slug}")
        print("Hint: use 'python -m scripts.deploy list' to see available projects")
        return 1

    log_text = docker_deploy.logs(project.id, args.env, lines=args.lines)
    print(log_text)
    return 0


def cmd_restart(args):
    store = ConversationStore()
    project = _resolve_project(store, args.slug)
    if not project:
        print(f"Project not found: {args.slug}")
        print("Hint: use 'python -m scripts.deploy list' to see available projects")
        return 1

    result = docker_deploy.restart(project.id, args.env)
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "running" else 1


def cmd_stop(args):
    store = ConversationStore()
    project = _resolve_project(store, args.slug)
    if not project:
        print(f"Project not found: {args.slug}")
        print("Hint: use 'python -m scripts.deploy list' to see available projects")
        return 1

    result = docker_deploy.stop(project.id, args.env)
    print(json.dumps(result, indent=2))
    return 0


def cmd_validate(args):
    store = ConversationStore()
    project = _resolve_project(store, args.slug)
    if not project:
        print(f"Project not found: {args.slug}")
        print("Hint: use 'python -m scripts.deploy list' to see available projects")
        return 1

    warnings = docker_deploy.validate_compose(project.id)
    if warnings:
        for w in warnings:
            print(f"WARNING: {w}")
        return 1
    print("OK: compose file looks good")
    return 0


def cmd_health(args):
    results = docker_deploy.health_check_all()
    for key, status in sorted(results.items()):
        print(f"{key:30s} {status}")
    return 0


def cmd_cleanup(args):
    """Clean up unused Docker resources."""
    from lib.docker_cleanup import cleanup, disk_usage

    # Show current usage
    print("=== Docker Disk Usage ===")
    usage = disk_usage()
    if "error" in usage:
        print(f"  Error: {usage['error']}")
    else:
        for rtype, info in usage.items():
            print(f"  {rtype:15s} count={info['count']:>5s}  size={info['size']:>10s}  reclaimable={info['reclaimable']}")

    print()
    dry_run = getattr(args, "dry_run", False)
    result = cleanup(dry_run=dry_run)

    action = "Would remove" if dry_run else "Removed"
    print(f"=== Cleanup {'(dry run)' if dry_run else ''} ===")
    print(f"  {action} {result['dangling_images']} dangling images")
    print(f"  {action} {result['stopped_containers']} stopped containers")
    print(f"  {action} {result['unused_volumes']} unused volumes")
    if result["total_reclaimed_mb"] > 0:
        print(f"  Reclaimed: {result['total_reclaimed_mb']:.1f} MB")
    if result["errors"]:
        for err in result["errors"]:
            print(f"  ERROR: {err}")
    return 0


def cmd_debug(args):
    """Debug a project's containers."""
    store = ConversationStore()
    project = _resolve_project(store, args.slug)
    if not project:
        print(f"Project not found: {args.slug}")
        print("Hint: use 'python -m scripts.deploy list' to see available projects")
        return 1

    from lib.docker_cleanup import debug_container
    info = debug_container(project.slug, args.env)

    if "error" in info:
        print(f"Error: {info['error']}")
        return 1

    for c in info.get("containers", []):
        print(f"\n=== {c['name']} ({c['state']}) ===")
        if c.get("cpu"):
            print(f"  CPU: {c['cpu']}  Memory: {c['memory']}")
            print(f"  Network: {c['network_io']}  Disk: {c['block_io']}")
        if c.get("logs"):
            print(f"  --- Last 20 log lines ---")
            print(c["logs"][-1000:])
    return 0


def cmd_smoke(args):
    """Run browser smoke test on a deployed project."""
    store = ConversationStore()
    project = _resolve_project(store, args.slug)
    if not project:
        print(f"Project not found: {args.slug}")
        return 1

    deploy_url = (project.staging_deploy_url if args.env == "staging"
                  else project.production_deploy_url)
    if not deploy_url:
        print(f"No {args.env} deploy URL for {project.slug}")
        return 1

    from lib.browser_smoke import smoke_test, browser_available
    if not browser_available():
        print("ERROR: agent-browser is not available")
        print("Install: npm install -g agent-browser && agent-browser install")
        return 1

    print(f"Running smoke test on {deploy_url}...")
    result = smoke_test(deploy_url, project.id)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "pass" else 1


def main():
    parser = argparse.ArgumentParser(description="Deploy CLI for expert-mode projects")
    sub = parser.add_subparsers(dest="command")

    p_status = sub.add_parser("status", help="Show deployment status")
    p_status.add_argument("slug", nargs="?", help="Project slug (omit for all)")

    p_staging = sub.add_parser("staging", help="Deploy staging")
    p_staging.add_argument("slug", help="Project slug")

    p_prod = sub.add_parser("production", help="Deploy production")
    p_prod.add_argument("slug", help="Project slug")

    p_logs = sub.add_parser("logs", help="View container logs")
    p_logs.add_argument("slug", help="Project slug")
    p_logs.add_argument("--env", default="staging", choices=["staging", "production"])
    p_logs.add_argument("--lines", type=int, default=100)

    p_restart = sub.add_parser("restart", help="Restart containers")
    p_restart.add_argument("slug", help="Project slug")
    p_restart.add_argument("--env", default="staging", choices=["staging", "production"])

    p_stop = sub.add_parser("stop", help="Stop containers")
    p_stop.add_argument("slug", help="Project slug")
    p_stop.add_argument("--env", default="staging", choices=["staging", "production"])

    p_validate = sub.add_parser("validate", help="Validate compose file")
    p_validate.add_argument("slug", help="Project slug")

    sub.add_parser("health", help="Health check all projects")
    sub.add_parser("list", help="List all projects (slugs and IDs)")

    p_cleanup = sub.add_parser("cleanup", help="Clean up unused Docker resources")
    p_cleanup.add_argument("--dry-run", action="store_true", dest="dry_run",
                           help="Show what would be cleaned without acting")

    p_debug = sub.add_parser("debug", help="Debug a project's containers")
    p_debug.add_argument("slug", help="Project slug or UUID")
    p_debug.add_argument("--env", default="staging", choices=["staging", "production"])

    p_smoke = sub.add_parser("smoke", help="Run browser smoke test")
    p_smoke.add_argument("slug", help="Project slug or UUID")
    p_smoke.add_argument("--env", default="staging", choices=["staging", "production"])

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # 'list' doesn't need Docker
    if args.command == "list":
        return cmd_list(args)

    if not docker_deploy.docker_available():
        print("ERROR: Docker is not available")
        return 1

    handlers = {
        "status": cmd_status,
        "staging": lambda a: cmd_deploy(a, "staging"),
        "production": lambda a: cmd_deploy(a, "production"),
        "logs": cmd_logs,
        "restart": cmd_restart,
        "stop": cmd_stop,
        "validate": cmd_validate,
        "health": cmd_health,
        "list": cmd_list,
        "cleanup": cmd_cleanup,
        "debug": cmd_debug,
        "smoke": cmd_smoke,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
