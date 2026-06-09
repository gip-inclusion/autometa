"""Tests for web/concurrency.py — context-preserving thread offload."""

import asyncio
import contextvars
import threading

from web.concurrency import run_in_thread

_marker = contextvars.ContextVar("marker", default="unset")


def test_run_in_thread_runs_off_the_event_loop_thread():
    main_thread = threading.get_ident()
    assert asyncio.run(run_in_thread(threading.get_ident)) != main_thread


def test_run_in_thread_preserves_contextvars():
    async def scenario():
        _marker.set("set-on-loop")
        return await run_in_thread(_marker.get)

    assert asyncio.run(scenario()) == "set-on-loop"


def test_run_in_thread_passes_args_and_kwargs():
    def add(a, b, c=0):
        return a + b + c

    assert asyncio.run(run_in_thread(add, 1, 2, c=3)) == 6
