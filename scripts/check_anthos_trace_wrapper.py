"""Instrumentation integration check, NOT banking execution or research data.

Uses a tiny local fixture to test real HTTP spans, parent linkage and export
redaction. Run with the D: TracingValidation dependency directory on PYTHONPATH.
"""
import contextlib
import importlib.util
import io
import json
import logging
from pathlib import Path
import sys
import threading
import types

from flask import Flask
import requests
from werkzeug.serving import make_server

receiver = Flask('trace-fixture-receiver')
logging.getLogger('werkzeug').setLevel(logging.ERROR)
receiver.add_url_rule('/transactions', view_func=lambda: ('ok',201), methods=['POST'])
server = make_server('127.0.0.1',0,receiver)
worker = threading.Thread(target=server.serve_forever,daemon=True)
worker.start()
app = Flask('trace-fixture-frontend')


@app.post('/payment')
def payment():
    response = requests.post(f'http://127.0.0.1:{server.server_port}/transactions?password=fixture-secret',
        headers={'Authorization':'Bearer fixture-token'}, timeout=5)
    return ('fixture',response.status_code)


fixture = types.ModuleType('frontend')
fixture.create_app = lambda: app
sys.modules['frontend'] = fixture
path = Path(__file__).resolve().parents[1]/'deploy/anthos_frontend_telemetry.py'
spec = importlib.util.spec_from_file_location('research_frontend',path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
output = io.StringIO()
exporter = module.ConsoleSpanExporter
module.ConsoleSpanExporter = lambda **kwargs: exporter(out=output, **kwargs)
try:
    with contextlib.redirect_stdout(output):
        instrumented = module.create_app()
        response = instrumented.test_client().post('/payment')
        assert response.status_code == 201
        module.trace.get_tracer_provider().force_flush()
    text = output.getvalue()
    assert 'fixture-secret' not in text and 'fixture-token' not in text
    spans = [json.loads(line[len('RESEARCH_SPAN '):]) for line in text.splitlines()
             if line.startswith('RESEARCH_SPAN ')]
    parent = next(s for s in spans if s['kind']=='SERVER' and s['attributes'].get('http.route')=='/payment')
    child = next(s for s in spans if s['kind']=='CLIENT')
    assert child['parent_span_id'] == parent['span_id']
    assert child['trace_id'] == parent['trace_id']
    assert child['end_time_unix_ns'] > child['start_time_unix_ns']
    assert '?' not in child['attributes'].get('http.url',child['attributes'].get('url.full',''))
    print('PASS: real fixture HTTP span timing, server/client parent linkage and credential redaction. Not an Anthos execution.')
finally:
    server.shutdown()
    worker.join(timeout=5)
    module.trace.get_tracer_provider().shutdown()
