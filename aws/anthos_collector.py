"""Read-only OTLP JSON file collector, with no fabricated request counters."""
import json,hashlib
from pathlib import Path
from dataset.banking_cloud_schema import MeasuredPoint,RecordedSpan
from aws.banking_telemetry import check_metric

def collect_file(path):
    raw=Path(path).read_bytes();payload=json.loads(raw)
    measurements=[MeasuredPoint.model_validate(p) for p in payload['measurements']]
    for p in measurements:check_metric(p.metric,p.unit,p.value)
    spans=[RecordedSpan.model_validate(s) for s in payload.get('spans',[])]
    return {'execution_id':payload['execution_id'],'measurements':[p.model_dump() for p in measurements],
        'spans':[s.model_dump() for s in spans],'source_sha256':hashlib.sha256(raw).hexdigest(),
        'scope':'Validated retained collector file; no remote infrastructure was contacted.'}
