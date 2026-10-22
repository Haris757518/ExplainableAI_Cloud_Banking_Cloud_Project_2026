"""Local-only frontend server/client spans; no cloud exporter or HTTP bodies.

Mounted alongside the unmodified upstream frontend. This is partial trace
coverage: backend server spans and database spans are not claimed.
"""
import json
from urllib.parse import urlsplit, urlunsplit

from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def span_line(span):
    """Export only measured identifiers/timing and allowlisted HTTP attributes."""
    attrs = {}
    for key in ('http.method', 'http.request.method', 'http.status_code',
                'http.response.status_code', 'http.route', 'server.address',
                'server.port', 'net.peer.name', 'net.peer.port'):
        if key in span.attributes:
            attrs[key] = span.attributes[key]
    for key in ('http.url', 'url.full'):
        if key in span.attributes:
            url = urlsplit(span.attributes[key])
            # Drop credentials, query strings and fragments from every span.
            host = url.hostname or ''
            if url.port:
                host += ':' + str(url.port)
            attrs[key] = urlunsplit((url.scheme, host, url.path, '', ''))
    return 'RESEARCH_SPAN ' + json.dumps({
        'trace_id': format(span.context.trace_id, '032x'),
        'span_id': format(span.context.span_id, '016x'),
        'parent_span_id': format(span.parent.span_id, '016x') if span.parent else None,
        'service': 'frontend', 'kind': span.kind.name,
        'start_time_unix_ns': span.start_time,
        'end_time_unix_ns': span.end_time,
        'status': span.status.status_code.name,
        'attributes': attrs,
        'coverage': 'frontend server and outbound HTTP client spans only',
    }, separators=(',', ':')) + '\n'


def create_app():
    from frontend import create_app as upstream_create_app
    # ENABLE_TRACING=false leaves the upstream GCP exporter disabled.
    app = upstream_create_app()
    provider = TracerProvider(resource=Resource.create({
        'service.name': 'frontend', 'deployment.environment.name': 'local-research',
    }))
    provider.add_span_processor(BatchSpanProcessor(
        ConsoleSpanExporter(formatter=span_line), schedule_delay_millis=1000))
    trace.set_tracer_provider(provider)
    FlaskInstrumentor().instrument_app(app, tracer_provider=provider)
    RequestsInstrumentor().instrument(tracer_provider=provider)
    return app
