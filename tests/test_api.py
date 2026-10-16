from fastapi.testclient import TestClient
from backend.main import app

client=TestClient(app)

def test_health():
    r=client.get('/api/health')
    assert r.status_code==200
    assert r.json()['status']=='ok'


def test_config_exposes_transaction_types():
    r=client.get('/api/config')
    assert r.status_code==200
    assert len(r.json()['transaction_types'])==5
    assert "ALIBABA_BENCHMARK" not in r.json()['transaction_types']

def test_simulate_rejects_alibaba_benchmark():
    r = client.post("/api/simulate?scenario=NORMAL&tx_type=ALIBABA_BENCHMARK")
    assert r.status_code == 403
    assert "disabled" in r.json()["detail"]

def test_alibaba_analyze_succeeds():
    import unittest.mock as mock
    from dataset.alibaba_adapter import AlibabaGraphSnapshot
    fake_snapshot = AlibabaGraphSnapshot(
        source="alibaba_mock",
        trace_id="test",
        timestamp=1000,
        nodes=[{"id": "A"}],
        edges=[],
        telemetry=[{"node_id": "A", "observed_metrics": ["cpu_percent"]}],
        metadata={}
    )
    with mock.patch("backend.main.build_snapshot", return_value=fake_snapshot):
        r = client.post("/api/alibaba/analyze")
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "alibaba"
    assert data["transaction"]["type"] == "ALIBABA_BENCHMARK"
    assert len(data["graph"]["nodes"]) >= 1

def test_simulation_is_disabled_by_default():
    r = client.post("/api/simulate?scenario=NORMAL&tx_type=UPI_PAYMENT")
    assert r.status_code == 403

def test_existing_aws_status_works(monkeypatch):
    monkeypatch.setattr("backend.main.AWSDiscovery.status", lambda self: {"connected": False, "region": "ap-south-1", "error": "test session unavailable"})
    r = client.get("/api/aws/status")
    assert r.status_code == 200
    assert "connected" in r.json()


def test_self_hosted_postgres_snapshot_is_persisted(monkeypatch):
    from backend.main import settings
    monkeypatch.setattr(settings, 'aws_mode', True)
    monkeypatch.setattr('backend.main._aws_discovery', lambda: {'ec2':[{'id':'i-monitored'}],'rds':[]})
    monkeypatch.setattr('aws.ssm_postgres.collect_postgres', lambda *args: {'status':'observed','source':'aws_ssm_postgresql','observation':{'blocked_sessions':0,'activity':[]}})
    response=client.post('/api/aws/database/diagnostics?instance_id=i-monitored')
    assert response.status_code==200
    assert response.json()['snapshot_id']>0
    response=client.post('/api/aws/database/diagnostics?instance_id=i-not-discovered')
    assert response.status_code==404
