"""OpenTelemetry setup — no-op when OTEL_EXPORTER_OTLP_ENDPOINT is unset."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator


def setup_otel(app) -> None:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        return

    service = os.environ.get("OTEL_SERVICE_NAME", "pegazus-api")
    resource = Resource.create({"service.name": service})
    provider = TracerProvider(resource=resource)
    # Accept bare host:port or full URL
    if endpoint.startswith("http"):
        exporter = OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
    else:
        exporter = OTLPSpanExporter(endpoint=f"http://{endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


@contextmanager
def span(name: str, **attrs: object) -> Iterator[None]:
    try:
        from opentelemetry import trace
    except ImportError:
        yield
        return
    tracer = trace.get_tracer("pegazus")
    with tracer.start_as_current_span(name) as sp:
        for k, v in attrs.items():
            if v is not None:
                sp.set_attribute(k, str(v))
        yield
