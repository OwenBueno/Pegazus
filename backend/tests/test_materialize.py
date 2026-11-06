"""Materialize buffer key + scaffold helpers."""

from app.pipeline.materialize_node import materialize_buffer_key
from uuid import uuid4


def test_materialize_buffer_key_stable():
    p, n = uuid4(), uuid4()
    assert materialize_buffer_key(p, n) == f"mat:{p}:{n}"
