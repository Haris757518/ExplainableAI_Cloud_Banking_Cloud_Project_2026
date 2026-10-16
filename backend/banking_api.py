"""Banking gateway, measured investigation and explicitly triggered local controls."""
import json,time,uuid,ipaddress,os
from pathlib import Path
import httpx
from fastapi import APIRouter,HTTPException,Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel,Field
from banking import store
from banking.service import Operation
from banking.tracing import Span
router=APIRouter(prefix='/api/banking',tags=['Academic digital banking'])
_downstream=httpx.Client(timeout=5,trust_env=False)
_health=httpx.Client(timeout=.5,trust_env=False)

def local_operator(request):
    if request.client and request.client.host not in ('127.0.0.1','::1','testclient'):raise HTTPException(403,'Dedicated loopback academic environment only.')
    origin=request.headers.get('origin')
    if origin and origin not in ('http://127.0.0.1:8000','http://localhost:8000','http://127.0.0.1:5173','http://localhost:5173'):raise HTTPException(403,'Local operator origin required.')

@router.post('/execute')
def execute(body:Operation,request:Request):
    local_operator(request);store.initialize();trace=uuid.uuid4().hex
    if not body.transfer_id:body.transfer_id=uuid.uuid4().hex
    target='ledger-service' if body.operation=='transfer' else 'account-service';port=8102 if body.operation=='transfer' else 8101
    try:
        with Span('banking-api','server',body.operation,trace) as root:
            with Span(target,'client',body.operation,caller='banking-api') as child:
                response=_downstream.post(f'http://127.0.0.1:{port}/execute',json=body.model_dump(),headers={'x-trace-id':trace,'x-parent-span-id':child.id})
                child.status=response.status_code;root.status=response.status_code
                try:result=response.json()
                except ValueError:result={'detail':'Local service returned a non-JSON error.'}
        with store.connect() as db:db.execute('INSERT INTO requests(trace_id,operation,ts,duration_ms,success,status) VALUES(?,?,?,?,?,?)',(trace,body.operation,root.end,root.duration_ms,int(response.status_code<400),response.status_code))
        payload={'trace_id':trace,'operation':body.operation,'success':response.status_code<400,'response_status':response.status_code,'result':result.get('result'),'error':result.get('detail'),'measured_handler_ms':root.duration_ms,'observed_at':root.end,'environment':'Local test funds; dedicated SQLite fallback'}
        return JSONResponse(payload,status_code=response.status_code)
    except httpx.HTTPError as exc:raise HTTPException(503,'Local banking service unavailable. Run scripts/start_banking.ps1.') from exc

class WorkloadRequest(BaseModel):
    confirm_local_test:bool=False
    per_operation:int=Field(default=90,ge=40,le=150)
class DelayRequest(BaseModel):
    confirm_local_test:bool=False
    duration_seconds:int=Field(default=12,ge=3,le=30)
    delay_ms:int=Field(default=150,ge=50,le=250)

@router.post('/workload')
def workload(body:WorkloadRequest,request:Request):
    local_operator(request)
    if not body.confirm_local_test:raise HTTPException(422,'Explicit local test trigger required.')
    from banking.workload import launch
    try:return {'job_id':launch('normal',per_operation=body.per_operation)}
    except store.BankingError as exc:raise HTTPException(exc.status,exc.message) from exc

@router.post('/experiments/application-delay')
def application_delay(body:DelayRequest,request:Request):
    local_operator(request)
    if not body.confirm_local_test:raise HTTPException(422,'Explicit local experiment trigger required.')
    from banking.workload import launch
    try:return {'job_id':launch('application-delay',duration=body.duration_seconds,delay_ms=body.delay_ms)}
    except store.BankingError as exc:raise HTTPException(exc.status,exc.message) from exc

@router.post('/experiments/database-lock')
def database_lock(request:Request):
    local_operator(request)
    raise HTTPException(409,'Blocked: no verified dedicated PostgreSQL test database. SQLite locking is not PostgreSQL wait evidence. No fault was started.')

@router.post('/stop')
def stop(request:Request):
    local_operator(request);store.stop_experiments()
    with store.connect('controls.db') as db:db.execute("UPDATE jobs SET status='stopping' WHERE status='running'")
    return {'status':'stop_requested','bounded_inflight_delay_ms':250}

@router.get('/verify/{job_id}')
def verification(job_id:str):
    from banking.workload import verify
    try:return verify(job_id)
    except store.BankingError as exc:raise HTTPException(exc.status,exc.message) from exc

@router.get('/state')
def state(operation:str='transfer'):
    if operation not in ('balance','transfer','history'):raise HTTPException(422,'Unknown banking operation.')
    store.initialize();services={}
    for role,port in [('account-service',8101),('ledger-service',8102)]:
        try:
            r=_health.get(f'http://127.0.0.1:{port}/health');r.raise_for_status();services[role]=r.json()
        except httpx.HTTPError:services[role]={'status':'unavailable'}
    from banking.analysis import investigate,recovery
    current,requests=investigate(operation)
    previous=store.rows('SELECT payload FROM snapshots WHERE operation=? ORDER BY ts DESC LIMIT 30',(operation,))
    incidents=[json.loads(r['payload']) for r in previous if json.loads(r['payload'])['status']=='deviation_detected'][:8]
    if incidents:
        incidents[0]['recovery']=recovery(incidents[0],operation)
    jobs=[{**r,'payload':json.loads(r['payload'])} for r in store.rows('SELECT * FROM jobs ORDER BY rowid DESC LIMIT 8',name='controls.db')]
    cal=store.calibration();report_path=store.root()/'graph-report.json'
    # Status exposes whether a control is active, but not its fault category/target to inference.
    active=bool(store.rows('SELECT 1 FROM experiments WHERE ended IS NULL AND expires>?',(time.time(),),name='controls.db'))
    return {'environment':{'kind':'isolated local academic banking application','database':'Dedicated SQLite fallback','postgres_lock_scenario':'blocked','cloud_deployment':False,'fictitious_funds_only':True},'services':services,'operation':operation,'current':current,'history':requests[-120:],'last_request':requests[-1] if requests else None,'recent_incidents':incidents,'jobs':jobs,'condition_active':active,'baseline':{k:v for k,v in cal.items() if not k.endswith('trace_ids')} if cal else None,'graph_model_report':json.loads(report_path.read_text()) if report_path.exists() else None,'observed_edges':current['graph']['edges'],'accounts':[{'id':'test-a','name':'Test Account A'},{'id':'test-b','name':'Test Account B'}]}


@router.get('/results')
def banking_results():
    import hashlib
    project=Path(__file__).resolve().parents[1]
    pointer=project/'results/banking/FINAL.json'
    if not pointer.exists():return {'status':'not_evaluated','report':None}
    info=json.loads(pointer.read_text(encoding='utf-8'));report=(project/info['report']).resolve()
    if not report.is_relative_to(project/'results/banking') or not report.exists():raise HTTPException(424,'Frozen banking report unavailable.')
    content=report.read_bytes().replace(b'\r\n',b'\n')
    if hashlib.sha256(content).hexdigest()!=info['sha256']:raise HTTPException(424,'Frozen banking report checksum differs.')
    return {'status':'evaluated','report':json.loads(content)}


@router.get('/incidents/{snapshot_id}')
def saved_banking_incident(snapshot_id:str):
    snapshots=store.rows('SELECT operation,payload FROM snapshots WHERE id=?',(snapshot_id,))
    if not snapshots:raise HTTPException(404,'Measured banking snapshot not found.')
    incident=json.loads(snapshots[0]['payload'])
    from banking.analysis import recovery
    incident['recovery']=recovery(incident,snapshots[0]['operation'])
    return incident
