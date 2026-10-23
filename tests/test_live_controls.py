from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.live_banking_api import router

def test_remote_client_cannot_execute_demo_controls():
    app=FastAPI();app.include_router(router)
    with TestClient(app) as client:
        response=client.post('/api/live-banking/action/fault',headers={'Origin':'http://127.0.0.1:8012'})
    assert response.status_code==403

def test_missing_or_foreign_origin_cannot_execute_controls():
    app=FastAPI();app.include_router(router)
    with TestClient(app,client=('127.0.0.1',12345)) as client:
        assert client.post('/api/live-banking/action/run').status_code==403
        assert client.post('/api/live-banking/action/run',headers={'Origin':'https://example.com'}).status_code==403
