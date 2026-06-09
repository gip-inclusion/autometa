"""Tests for web/memory_introspect — diagnostic RSS/heap stats."""

import asyncio

import pytest

from web import memory_introspect


def test_process_memory_parses_proc_status(mocker):
    mocker.patch("builtins.open", mocker.mock_open(read_data="VmRSS:\t 2048 kB\nVmSwap:\t 512 kB\n"))
    assert memory_introspect.process_memory() == {"rss_bytes": 2048 * 1024, "swap_bytes": 512 * 1024}


def test_process_memory_handles_missing_proc(mocker):
    mocker.patch("builtins.open", side_effect=OSError)
    assert memory_introspect.process_memory() == {"rss_bytes": 0, "swap_bytes": 0}


def test_malloc_arenas_returns_int_or_none():
    result = memory_introspect.malloc_arenas()
    assert result is None or isinstance(result, int)


def test_live_object_count_is_positive():
    assert memory_introspect.live_object_count() > 0


def test_running_task_count_none_outside_loop():
    assert memory_introspect.running_task_count() is None


def test_running_task_count_inside_loop():
    async def _count():
        return memory_introspect.running_task_count()

    assert asyncio.run(_count()) >= 1


def test_top_types_returns_name_count_tuples():
    result = memory_introspect.top_types(limit=5)
    assert len(result) <= 5
    assert all(isinstance(name, str) and isinstance(count, int) for name, count in result)


def test_tracemalloc_top_empty_when_not_tracing(mocker):
    mocker.patch.object(memory_introspect.tracemalloc, "is_tracing", return_value=False)
    assert memory_introspect.tracemalloc_top() == []


def test_gather_cheap_omits_heavy_keys(mocker):
    mocker.patch.object(memory_introspect, "malloc_arenas", return_value=2)
    data = memory_introspect.gather(tasks=3)
    assert data["malloc_arenas"] == 2
    assert data["tasks"] == 3
    assert {"rss_bytes", "swap_bytes", "gc_objects"} <= data.keys()
    assert "top_types" not in data and "tracemalloc_top" not in data


def test_gather_deep_adds_heap(mocker):
    mocker.patch.object(memory_introspect, "malloc_arenas", return_value=None)
    mocker.patch.object(memory_introspect, "top_types", return_value=[("dict", 10)])
    mocker.patch.object(memory_introspect, "tracemalloc_top", return_value=["site"])
    data = memory_introspect.gather(deep=True)
    assert data["top_types"] == [("dict", 10)]
    assert data["tracemalloc_top"] == ["site"]


@pytest.mark.parametrize("deep", [False, True])
def test_log_snapshot_emits_and_returns(mocker, deep):
    mocker.patch.object(memory_introspect, "malloc_arenas", return_value=2)
    mocker.patch.object(memory_introspect, "top_types", return_value=[("dict", 1)])
    mocker.patch.object(memory_introspect, "tracemalloc_top", return_value=["site"])
    info = mocker.spy(memory_introspect.logger, "info")
    data = memory_introspect.log_snapshot(deep=deep, tasks=2)
    assert {"rss_bytes", "malloc_arenas", "gc_objects", "tasks"} <= data.keys()
    assert info.called
