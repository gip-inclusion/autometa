"""Async concurrency helpers."""

import asyncio
import contextvars
from collections.abc import Callable
from typing import Any


async def run_in_thread(fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
    """Run a blocking callable in a worker thread, preserving contextvars (log/trace correlation)."""
    ctx = contextvars.copy_context()
    return await asyncio.to_thread(ctx.run, fn, *args, **kwargs)
