from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.cloud_investigation_api import router
from dataset.banking_cloud_schema import BankingCloudRecording
import pytest

app=FastAPI();app.include_router(router);client=TestClient(app)

def test_overview_has_unknown_live_numbers_and_explicit_partition_boundary(monkeypatch,tmp_path):
    monkeypatch.setattr('backend.cloud_investigation_api.AWS_STATUS_PATH',tmp_path/'missing.json')
    r=client.get('/api/cloud-investigation/overview').json()
    assert all(v is None for v in r['summary'].values())
    assert r['monitoring_status']=='not_deployed'
    assert r['aws']['new_compute_budget_inr']==0

def test_aws_status_requires_intact_verified_transfer_receipt(monkeypatch,tmp_path):
    import hashlib,json
    status=tmp_path/'status.json';proof=tmp_path/'first-transfer-verification.json'
    monkeypatch.setattr('backend.cloud_investigation_api.AWS_STATUS_PATH',status)
    proof.write_text(json.dumps({'status':'verified','history_record_found':True,'ledger_new_records':1}))
    status.write_text(json.dumps({'source':'executed-aws-bank-of-anthos','evidence_status':'verified_transfer',
        'proof_sha256':hashlib.sha256(proof.read_bytes()).hexdigest(),'transaction_id':66,'experiment_status':'Pending analysis.',
        'pods_ready':8,'payment_roundtrip_ms':1768.66,'verified_transfers':1,'approved_budget_usd':5}))
    response=client.get('/api/cloud-investigation/overview').json()
    assert response['monitoring_status']=='recorded_aws_execution'
    assert response['summary']['verified_transfers']==1 and response['summary']['active_issues'] is None
    proof.write_text('{}')
    assert client.get('/api/cloud-investigation/overview').json()['monitoring_status']=='not_deployed'

def test_recording_selector_does_not_reveal_ground_truth():
    r=client.get('/api/cloud-investigation/recordings').json()
    assert len(r['recordings'])>=5
    assert all('fault' not in row and 'root_cause_service' not in row for row in r['recordings'])

def test_invalid_query_budget_cannot_trigger_unbounded_inspection():
    assert client.post('/api/cloud-investigation/investigate',json={'case_id':'unknown','query_budget':1000}).status_code==422

def test_recording_contract_does_not_accept_fault_annotations():
    with pytest.raises(Exception):
        BankingCloudRecording.model_validate({'root_cause_service':'payment','fault':'cpu'})
