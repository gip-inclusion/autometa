"""Watch local interactive directory and sync new/modified files to S3."""

import logging
import mimetypes
import os
import re
import threading
import time
from pathlib import Path
from uuid import uuid4

from botocore.exceptions import ClientError

from . import config, s3

logger = logging.getLogger(__name__)

watcher_thread = None
stop_event = threading.Event()

# Why: les écritures atomiques passent par un `<fichier>.tmp.<pid>.<id>` renommé aussitôt ; vu
# pendant sa courte vie, il partait sur S3 où rien ne le supprime, puis dans les publications.
UNSYNCED = re.compile(r"\.tmp\.\d+\.[0-9a-f]+$|(^|/)__pycache__/")

# Why: renvoyer un fichier restauré écrasait ce qu'on avait déposé sur S3 entre son téléchargement et ce renvoi.
# Ne protège que si la restauration et le watcher tournent dans le même processus (un seul worker uvicorn).
restored_mtimes: dict[Path, float] = {}


def write_restored(path: Path, content: bytes):
    """Write a file downloaded from S3 so that the watcher does not send it back."""
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}.{uuid4().hex}")
    temporary.write_bytes(content)
    restored_mtimes[path] = temporary.stat().st_mtime
    temporary.replace(path)


def start_sync_watcher():
    """Start the background file watcher if S3 is configured."""
    global watcher_thread

    if watcher_thread is not None and watcher_thread.is_alive():
        logger.debug("Sync watcher already running")
        return

    config.INTERACTIVE_DIR.mkdir(parents=True, exist_ok=True)

    stop_event.clear()
    watcher_thread = threading.Thread(target=watch_loop, daemon=True)
    watcher_thread.start()
    logger.info("Started S3 sync watcher for %s", config.INTERACTIVE_DIR)


def stop_sync_watcher():
    global watcher_thread
    stop_event.set()
    if watcher_thread is not None:
        watcher_thread.join(timeout=5)
        watcher_thread = None
    logger.info("Stopped S3 sync watcher")


def scan_files() -> dict[Path, float]:
    """Map each local interactive file to its mtime, skipping files that vanish mid-scan."""
    files = {}
    for path in config.INTERACTIVE_DIR.rglob("*"):
        try:
            if path.is_file():
                files[path] = path.stat().st_mtime
        except FileNotFoundError:
            logger.debug("File vanished during scan: %s", path)
    return files


def watch_loop():
    s3_paths = {f["path"] for f in s3.interactive.list_files()}
    known_files = scan_files()
    for path in known_files:
        if str(path.relative_to(config.INTERACTIVE_DIR)) not in s3_paths:
            _sync_file(path)

    logger.debug("Initial scan: %d local files, %d in S3", len(known_files), len(s3_paths))

    while not stop_event.is_set():
        try:
            current_files = scan_files()
            for path, mtime in current_files.items():
                changed = path not in known_files or known_files[path] < mtime
                if changed and restored_mtimes.get(path) != mtime:
                    _sync_file(path)

            known_files = current_files

        except Exception as e:  # Why: daemon thread polling filesystem, must not crash on transient I/O errors
            logger.error("Error in sync watch loop: %s", e)

        stop_event.wait(2)


def _sync_file(local_path: Path):
    relative_path = str(local_path.relative_to(config.INTERACTIVE_DIR))
    if UNSYNCED.search(relative_path):
        return
    start = time.perf_counter()
    try:
        content = local_path.read_bytes()
        content_type, _ = mimetypes.guess_type(local_path.name)

        if not s3.interactive.upload(relative_path, content, content_type):
            logger.error("Failed to sync to S3: %s", relative_path)
            return

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "s3.upload",
            extra={"s3.path": relative_path, "s3.size": len(content), "s3.duration": duration_ms},
        )

    except (OSError, ClientError) as e:
        logger.error("Error uploading %s to S3: %s", local_path, e)
