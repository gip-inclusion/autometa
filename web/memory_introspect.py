"""Diagnostic memory introspection: periodic RSS/heap stats to locate prod growth."""

import asyncio
import ctypes
import gc
import logging
import os
import tempfile
import tracemalloc
from collections import Counter

logger = logging.getLogger(__name__)

_last_rss = 0


def process_memory() -> dict:
    """RSS and swap of this process in bytes, from /proc (0 when unavailable)."""
    rss = swap = 0
    try:
        with open("/proc/self/status") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    rss = int(line.split()[1]) * 1024
                elif line.startswith("VmSwap:"):
                    swap = int(line.split()[1]) * 1024
    except OSError:
        logger.debug("memory: /proc/self/status unavailable")
    return {"rss_bytes": rss, "swap_bytes": swap}


def malloc_arenas() -> int | None:
    """Count of glibc malloc arenas (heaps); None when libc/malloc_info is unavailable."""
    try:
        libc = ctypes.CDLL("libc.so.6")
    except OSError:
        return None
    libc.fopen.restype = ctypes.c_void_p
    libc.fopen.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    libc.malloc_info.argtypes = [ctypes.c_int, ctypes.c_void_p]
    libc.fclose.argtypes = [ctypes.c_void_p]
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        stream = libc.fopen(path.encode(), b"w")
        if not stream:
            return None
        libc.malloc_info(0, stream)
        libc.fclose(stream)
        with open(path) as fh:
            return fh.read().count("<heap ")
    finally:
        os.unlink(path)


def live_object_count() -> int:
    """Total tracked live objects — rises with a Python-object leak; native RSS growth won't move it."""
    return len(gc.get_objects())


def running_task_count() -> int | None:
    """asyncio tasks on the running loop; None when called outside a loop (e.g. a worker thread)."""
    try:
        return len(asyncio.all_tasks())
    except RuntimeError:
        return None


def top_types(limit: int = 25) -> list[tuple[str, int]]:
    """Most common live object types by instance count (heavy: scans the whole heap)."""
    counts = Counter(type(o).__name__ for o in gc.get_objects())
    return counts.most_common(limit)


def tracemalloc_top(limit: int = 15) -> list[str]:
    """Top allocation sites grouped by file (surfaces SDK modules); empty unless tracing."""
    if not tracemalloc.is_tracing():
        return []
    stats = tracemalloc.take_snapshot().statistics("filename")[:limit]
    return [f"{s.size} {s.count} {s.traceback.format()[-1].strip()}" for s in stats]


def gather(deep: bool = False, tasks: int | None = None) -> dict:
    data = process_memory()
    data["malloc_arenas"] = malloc_arenas()
    data["gc_objects"] = live_object_count()
    data["tasks"] = tasks
    if deep:
        data["top_types"] = top_types()
        data["tracemalloc_top"] = tracemalloc_top()
    return data


def log_snapshot(deep: bool = False, tasks: int | None = None) -> dict:
    global _last_rss
    data = gather(deep=deep, tasks=tasks)
    rss = data["rss_bytes"]
    delta = rss - _last_rss if _last_rss else 0
    _last_rss = rss
    logger.info(
        "memory.snapshot rss=%dMiB delta=%+dMiB swap=%dMiB tasks=%s objects=%s arenas=%s",
        rss // (1024 * 1024),
        delta // (1024 * 1024),
        data["swap_bytes"] // (1024 * 1024),
        data["tasks"],
        data["gc_objects"],
        data["malloc_arenas"],
    )
    if deep:
        logger.info("memory.top_types %s", data["top_types"])
        for line in data["tracemalloc_top"]:
            logger.info("memory.tracemalloc %s", line)
    return data
