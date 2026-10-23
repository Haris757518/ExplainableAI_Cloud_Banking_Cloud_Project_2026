import hashlib
import json
import shutil
import pytest
from analysis.banking_replay import EVIDENCE, run_replay, summarize, diagnose, readable_report


def rewrite(folder, name, value):
    target=folder/name
    target.write_text(json.dumps(value))
    manifest=json.loads((folder/'manifest.json').read_text())
    manifest['files'][name]=hashlib.sha256(target.read_bytes()).hexdigest()
    (folder/'manifest.json').write_text(json.dumps(manifest))


def test_actual_workload_produces_readable_evidence_and_scoped_recovery():
    result=run_replay()
    assert result['submitted_requests']==3025
    assert {'capacity','database','traffic','balance'} <= {i['id'] for i in result['incidents']}
    assert result['recovery_verified'] is True
    balance=next(i for i in result['incidents'] if i['id']=='balance')
    assert balance['permanent_fix_verified'] is False
    assert 'investigator' in balance['origin'].lower()
    assert 'banking-domain GNN' in result['model_status']
    assert 'Deeper explanation:' in readable_report(result)


def test_tampered_evidence_is_rejected(tmp_path):
    shutil.copytree(EVIDENCE,tmp_path/'evidence')
    (tmp_path/'evidence/measurements.jsonl').write_text('{}')
    with pytest.raises(ValueError,match='integrity'):run_replay(tmp_path/'evidence')


def test_ledger_reconciliation_is_recomputed_not_assumed_from_summary(tmp_path):
    folder=tmp_path/'evidence';shutil.copytree(EVIDENCE,folder)
    ledger=json.loads((folder/'ledger-after.json').read_text())
    rewrite(folder,'ledger-after.json',ledger[1:])
    result=run_replay(folder)
    assert result['ledger_matches']==3024
    assert result['ledger_integrity_verified'] is False
    assert result['recovery_verified'] is False


def test_snapshot_and_request_not_visible_until_completed():
    rows=[{'instrument':'periodic_snapshot','timestamp':10,'collection_elapsed_ms':20000,'cgroups':{'ledgerwriter':{'cpu.max':'2000 100000'}}},
          {'instrument':'payment_request','timestamp':11,'completed_at':25,'latency_ms':14000}]
    before=summarize(rows,0,20)
    assert before['snapshots']==before['requests']==0
    assert before['cpu_limit_cores'] is None
    after=summarize(rows,0,31)
    assert after['snapshots']==after['requests']==1


def test_missing_instruments_do_not_invent_deeper_cause():
    base={'p95_ms':300,'cpu_limit_cores':.5,'arrival_rps':5}
    current={'requests':20,'p95_ms':6000,'cpu_limit_cores':None,'lock_wait_ms':0,'blocked_sessions':0,'arrival_rps':5}
    assert diagnose(current,base)=='unresolved'
    current.update(cpu_limit_cores=.02,lock_wait_ms=2000,blocked_sessions=2)
    assert diagnose(current,base)=='unresolved'


@pytest.mark.parametrize('change',['mismatch','earlier','duplicate_transfer'])
def test_recovery_requires_correct_later_independent_evidence(tmp_path,change):
    folder=tmp_path/'evidence';shutil.copytree(EVIDENCE,folder)
    name='balance-history-reconciliation.json';final=json.loads((folder/name).read_text())
    if change=='mismatch':final['accounts'][0]['api_balance_cents']+=1
    elif change=='earlier':final['checked_at']=0
    else:
        other=json.loads((folder/'recovery-transfer-0.json').read_text())
        rewrite(folder,'recovery-transfer-1.json',other)
    rewrite(folder,name,final)
    assert run_replay(folder)['recovery_verified'] is False


def test_read_only_workflow_and_download_endpoints():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from backend.cloud_investigation_api import router
    app=FastAPI();app.include_router(router)
    client=TestClient(app)
    response=client.post('/api/cloud-investigation/banking-replay')
    assert response.status_code==200
    assert response.json()['recovery_verified'] is True
    report=client.get('/api/cloud-investigation/banking-report')
    assert report.status_code==200
    assert 'attachment' in report.headers['content-disposition']
    assert 'The corrected readers passed all three:' in report.text
    assert response.json()['corrective_code']['verified'] is True
