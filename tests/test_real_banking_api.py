from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.real_banking_api import router

app=FastAPI(); app.include_router(router)
client=TestClient(app)

def test_read_routes_do_not_import_or_write_to_aws(monkeypatch):
    import backend.real_banking_api as api
    def forbidden(*args,**kwargs): raise AssertionError('Read triggered a mutation')
    monkeypatch.setattr(api,'import_bank',forbidden)
    monkeypatch.setattr(api,'upload',forbidden)
    monkeypatch.setattr(api,'publish',forbidden)
    for path in ['sources','metrics?bank=monzo&metric=latency','aws-status','incidents']:
        assert client.get('/api/banking-real/'+path).status_code==200

def test_invalid_selection_rejected():
    assert client.get('/api/banking-real/metrics?bank=monzo&start=2026-06-30&end=2026-01-01').status_code==422
    assert client.post('/api/banking-real/import',json={'bank':'unknown'}).status_code==422

def test_partial_cloud_failure_retains_successful_local_import(monkeypatch):
    import backend.real_banking_api as api
    monkeypatch.setattr(api,'import_bank',lambda bank:{'bank':bank})
    def unavailable(*args): raise ValueError('permission denied')
    monkeypatch.setattr(api,'upload',unavailable)
    result=client.post('/api/banking-real/import',json={'bank':'monzo','upload_to_s3':True}).json()
    assert result['local_status']=='validated' and result['aws']['status']=='failed'
