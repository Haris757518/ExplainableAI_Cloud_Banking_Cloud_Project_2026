"""Ephemeral contract fixtures, excluded from recorded research outcomes."""
import hashlib,json
import pytest
from dataset.banking_cloud_schema import MeasuredPoint
from dataset.banking_cloud_import import normalize

def payload():
    points=[MeasuredPoint(timestamp=t,service='ledger',metric='latency_ms',value=None if t==15 else 10,
        unit='milliseconds',observation_id=str(t),origin='executed_workload',collector='contract-fixture').model_dump() for t in range(30)]
    artifact={'execution_id':'fixture','measurements':points,'spans':[]}
    raw=json.dumps(artifact).encode()
    record={'recording_id':'fixture','application':'instrumented_banking_application','environment':'local',
        'infrastructure_id':'unit-test','execution_id':'fixture','baseline_end':19,'measurements':points,
        'spans':[],'collector_version':'test','source_artifact_sha256':hashlib.sha256(raw).hexdigest()}
    return record,raw

def test_retained_collector_identity_and_nulls_preserved():
    record,raw=payload();case=normalize(record,raw)
    assert case.series[0].observations[15].value is None
    assert case.source.id=='banking-local-recording'
    assert not {'fault','underlying_driver','root_cause_service'} & case.provenance.keys()

def test_changed_measurement_cannot_keep_source_checksum():
    record,raw=payload();record['measurements'][0]['value']=999
    with pytest.raises(ValueError,match='differs'):normalize(record,raw)

def test_labels_cannot_be_imported_as_inference_fields():
    record,raw=payload();record['underlying_driver']='heavy_traffic'
    with pytest.raises(ValueError):normalize(record,raw)

def test_unsupported_unit_cannot_be_normalized():
    record,raw=payload();record['measurements'][0]['unit']='invented';artifact=json.loads(raw);artifact['measurements']=record['measurements'];raw=json.dumps(artifact).encode();record['source_artifact_sha256']=hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError,match='unit'):normalize(record,raw)
