"""In-memory SSE event buffers for Deep Research and materialize jobs."""

from __future__ import annotations

import threading
import time
from typing import Any
from uuid import UUID

BufferKey = UUID | str

_lock = threading.Lock()
_BUFFERS: dict[BufferKey, list[dict[str, Any]]] = {}
_DONE: dict[BufferKey, bool] = {}

_TERMINAL = frozenset({"graph_complete", "graph_failed", "node_ready", "materialize_failed"})


def reset_buffer(key: BufferKey) -> None:
    with _lock:
        _BUFFERS[key] = []
        _DONE[key] = False


def append_event(key: BufferKey, event: str, data: dict[str, Any]) -> int:
    with _lock:
        buf = _BUFFERS.setdefault(key, [])
        eid = len(buf) + 1
        buf.append({"id": eid, "event": event, "data": data})
        if event in _TERMINAL:
            _DONE[key] = True
        return eid


def get_events_after(key: BufferKey, after_id: int) -> list[dict[str, Any]]:
    with _lock:
        return [e for e in _BUFFERS.get(key, []) if e["id"] > after_id]


def is_complete(key: BufferKey) -> bool:
    with _lock:
        return _DONE.get(key, False)


def wait_for_events(
    key: BufferKey, after_id: int, *, timeout_s: float = 0.5
) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        ev = get_events_after(key, after_id)
        if ev:
            return ev
        if is_complete(key):
            return get_events_after(key, after_id)
        time.sleep(0.05)
    return get_events_after(key, after_id)
