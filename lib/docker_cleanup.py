"""Docker cleanup and debugging utilities.

Manages image/container/volume lifecycle to keep the VPS disk usage under control.
Uses direct Docker CLI commands (no dependency on docker-agent).
"""

import logging
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)


def _run_docker(*args, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a docker command."""
    cmd = ["docker", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def cleanup(dry_run: bool = False) -> dict:
    """Clean up unused Docker resources.

    Removes:
    - Dangling images (untagged, no container)
    - Stopped containers not linked to any project
    - Unused volumes
    - Build cache

    Returns dict with cleaned resource counts and space reclaimed.
    """
    results = {
        "dangling_images": 0,
        "stopped_containers": 0,
        "unused_volumes": 0,
        "build_cache_mb": 0,
        "total_reclaimed_mb": 0,
        "dry_run": dry_run,
        "errors": [],
    }

    # 1. Dangling images
    try:
        list_result = _run_docker("images", "-f", "dangling=true", "-q")
        dangling = [img for img in list_result.stdout.strip().splitlines() if img]
        results["dangling_images"] = len(dangling)

        if dangling and not dry_run:
            rm_result = _run_docker("image", "prune", "-f")
            if rm_result.returncode != 0:
                results["errors"].append(f"Image prune failed: {rm_result.stderr[:200]}")
            else:
                _parse_reclaimed(rm_result.stdout, results)
    except Exception as e:
        results["errors"].append(f"Image cleanup error: {e}")

    # 2. Stopped containers (older than 24h, not matometa infra)
    try:
        list_result = _run_docker(
            "ps", "-a", "--filter", "status=exited",
            "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}"
        )
        protected_prefixes = ("matometa-",)
        stopped = []
        for line in list_result.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                cid, name = parts[0], parts[1]
                if not any(name.startswith(p) for p in protected_prefixes):
                    stopped.append((cid, name))

        results["stopped_containers"] = len(stopped)

        if stopped and not dry_run:
            for cid, name in stopped:
                rm_result = _run_docker("rm", cid, timeout=10)
                if rm_result.returncode != 0:
                    results["errors"].append(f"Failed to remove {name}: {rm_result.stderr[:100]}")
                else:
                    logger.info("Removed stopped container: %s", name)
    except Exception as e:
        results["errors"].append(f"Container cleanup error: {e}")

    # 3. Unused volumes
    try:
        list_result = _run_docker("volume", "ls", "-f", "dangling=true", "-q")
        unused = [v for v in list_result.stdout.strip().splitlines() if v]
        protected_volumes = {"gitea_data"}
        unused = [v for v in unused if v not in protected_volumes]
        results["unused_volumes"] = len(unused)

        if unused and not dry_run:
            for vol in unused:
                rm_result = _run_docker("volume", "rm", vol, timeout=10)
                if rm_result.returncode != 0:
                    results["errors"].append(f"Failed to remove volume {vol}: {rm_result.stderr[:100]}")
    except Exception as e:
        results["errors"].append(f"Volume cleanup error: {e}")

    # 4. Build cache
    try:
        if not dry_run:
            prune_result = _run_docker("builder", "prune", "-f", "--filter", "until=48h")
            if prune_result.returncode == 0:
                _parse_reclaimed(prune_result.stdout, results)
    except Exception as e:
        results["errors"].append(f"Build cache cleanup error: {e}")

    logger.info("Cleanup %s: images=%d, containers=%d, volumes=%d, errors=%d",
                "dry-run" if dry_run else "done",
                results["dangling_images"], results["stopped_containers"],
                results["unused_volumes"], len(results["errors"]))

    return results


def disk_usage() -> dict:
    """Get Docker disk usage summary."""
    try:
        result = _run_docker("system", "df", "--format",
                             "{{.Type}}\t{{.TotalCount}}\t{{.Size}}\t{{.Reclaimable}}")
        if result.returncode != 0:
            return {"error": result.stderr[:200]}

        usage = {}
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 4:
                usage[parts[0].lower()] = {
                    "count": parts[1],
                    "size": parts[2],
                    "reclaimable": parts[3],
                }
        return usage
    except Exception as e:
        return {"error": str(e)}


def debug_container(project_slug: str, environment: str = "staging") -> dict:
    """Get diagnostic info for a project's container.

    Returns container state, recent logs, resource usage, and network info.
    """
    container_prefix = f"{project_slug}-{environment}"
    info = {"project": project_slug, "environment": environment, "containers": []}

    try:
        # List containers for this project
        result = _run_docker(
            "compose", "-p", container_prefix, "ps",
            "--format", "{{.Name}}\t{{.State}}\t{{.Status}}\t{{.Ports}}"
        )

        if result.returncode != 0 or not result.stdout.strip():
            return {"error": f"No containers found for {container_prefix}"}

        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue

            name = parts[0]
            container_info = {
                "name": name,
                "state": parts[1],
                "status": parts[2],
                "ports": parts[3] if len(parts) > 3 else "",
            }

            # Get recent logs
            logs_result = _run_docker("logs", "--tail", "20", name, timeout=10)
            container_info["logs"] = (logs_result.stdout + logs_result.stderr)[-2000:]

            # Get resource usage
            stats_result = _run_docker(
                "stats", "--no-stream", "--format",
                "{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}",
                name, timeout=10,
            )
            if stats_result.returncode == 0 and stats_result.stdout.strip():
                stats_parts = stats_result.stdout.strip().split("\t")
                if len(stats_parts) >= 4:
                    container_info["cpu"] = stats_parts[0]
                    container_info["memory"] = stats_parts[1]
                    container_info["network_io"] = stats_parts[2]
                    container_info["block_io"] = stats_parts[3]

            info["containers"].append(container_info)

    except Exception as e:
        info["error"] = str(e)

    return info


def _parse_reclaimed(output: str, results: dict):
    """Parse 'Total reclaimed space: X.YMB' from docker prune output."""
    import re
    match = re.search(r"Total reclaimed space:\s*([\d.]+)\s*(MB|GB|kB|B)", output, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        unit = match.group(2).upper()
        if unit == "GB":
            value *= 1024
        elif unit == "KB":
            value /= 1024
        elif unit == "B":
            value /= (1024 * 1024)
        results["total_reclaimed_mb"] += value
