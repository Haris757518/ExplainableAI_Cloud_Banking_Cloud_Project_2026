"""Account and ledger run as distinct loopback FastAPI processes."""
import os,time,re
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request,HTTPException
from pydantic import BaseModel,Field,ConfigDict,StrictInt
from banking import store
from banking.tracing import Span,sql,database_connection

@asynccontextmanager
async def lifespan(app):store.initialize();yield
app=FastAPI(title='Academic Banking Test Service',lifespan=lifespan)
ROLE=os.environ.get('BANKING_SERVICE_ROLE','account')

class Operation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    operation:str=Field(pattern='^(balance|transfer|history)$')
    account:str=Field(default='test-a',pattern='^test-[ab]$')
    recipient:str=Field(default='test-b',pattern='^test-[ab]$')
    amount_cents:StrictInt=Field(default=1,ge=1,le=1000000)
    transfer_id:str=Field(default='',max_length=100,pattern='^[a-zA-Z0-9_-]*$')

@app.get('/health')
def health():return {'status':'ready','role':ROLE,'pid':os.getpid(),'database':'dedicated SQLite fallback','cloud':False}

@app.post('/execute')
def execute(body:Operation,request:Request):
    if (body.operation=='transfer')!=(ROLE=='ledger'):raise HTTPException(400,'Operation belongs to the other local service.')
    trace=request.headers.get('x-trace-id','')
    if not re.fullmatch('[a-f0-9]{32}',trace):raise HTTPException(422,'Valid local trace ID required.')
    service='ledger-service' if ROLE=='ledger' else 'account-service'
    try:
        with Span(service,'server',body.operation,trace,request.headers.get('x-parent-span-id'),caller='banking-api') as span:
            if ROLE=='ledger':
                # A real bounded wait executes only inside this dedicated local service.
                delay=store.active_delay()
                if delay:time.sleep(delay)
                result=store.transfer(body.account,body.recipient,body.amount_cents,body.transfer_id,sql,connection_factory=lambda:database_connection(body.operation,service))
            else:
                db=database_connection(body.operation,service)
                try:
                    account=sql(db,'SELECT id,name,balance_cents FROM accounts WHERE id=?',(body.account,)).fetchone()
                    if account is None:raise store.BankingError(404,'Unknown test account.')
                    result=dict(account) if body.operation=='balance' else {'account':body.account,'transactions':[dict(r) for r in sql(db,'SELECT * FROM transfers WHERE sender=? OR recipient=? ORDER BY created_at DESC LIMIT 20',(body.account,body.account)).fetchall()]}
                finally:db.close()
        return {'result':result,'trace_id':trace,'service_duration_ms':span.duration_ms}
    except store.BankingError as exc:raise HTTPException(exc.status,exc.message) from exc
