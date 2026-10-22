import csv
import io
import uuid
from datetime import date, datetime, timezone
from typing import Literal
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from dataset.real_banking.store import DATA, sources, metrics, import_bank, write_json, read_json
from analysis.banking_api_anomalies import analyze
from analysis.banking_api_forecasting import evaluate
from aws.banking_dataset_store import status, upload
from aws.banking_import_health import publish

router=APIRouter(prefix='/api/banking-real',tags=['Published real bank data'])

class ImportRequest(BaseModel):
    bank: Literal['monzo','starling']
    upload_to_s3: bool=False
    publish_health: bool=False

class AnalysisRequest(BaseModel):
    bank: Literal['monzo','starling']
    service: str | None=None
    metric: Literal['latency','availability','errors','downtime'] | None=None
    start: date | None=None
    end: date | None=None

@router.get('/sources')
def get_sources(): return {'sources':sources(),'data_origin':'published_real_bank'}

@router.post('/import')
def import_source(request: ImportRequest):
    try:
        manifest=import_bank(request.bank)
    except Exception as exc:
        if request.publish_health:
            try: publish(False)
            except Exception: pass
        raise HTTPException(422,f'Import failed; previous validated data retained: {exc}') from exc
    result={'local_status':'validated','manifest':manifest,'aws':{'status':'not_requested'}}
    if request.upload_to_s3:
        try: result['aws']=upload(manifest)
        except Exception as exc: result['aws']={'status':'failed','reason':str(exc)}
    if request.publish_health:
        try: result['cloudwatch']=publish(True)
        except Exception as exc: result['cloudwatch']={'status':'failed','reason':str(exc)}
    return result

@router.get('/metrics')
def get_metrics(bank: Literal['monzo','starling'] | None=None, service: str | None=None,
                metric: str | None=None, start: date | None=None, end: date | None=None,
                format: Literal['json','csv']='json'):
    if start and end and start>end: raise HTTPException(422,'Start date must precede end date')
    rows=metrics(bank,service,metric,start.isoformat() if start else None,end.isoformat() if end else None)
    if format=='csv':
        f=io.StringIO()
        if rows:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        return Response(f.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="published-bank-observations.csv"'})
    return {'observations':rows,'count':len(rows)}

@router.post('/analyze')
def run_analysis(request: AnalysisRequest):
    if request.start and request.end and request.start>request.end: raise HTTPException(422,'Start date must precede end date')
    rows=metrics(request.bank,request.service,request.metric,request.start.isoformat() if request.start else None,request.end.isoformat() if request.end else None)
    if not rows: raise HTTPException(422,'No imported observations in this selection')
    result=analyze(rows)
    if request.service and request.metric: result['forecast']=evaluate(rows)
    result.update({'run_id':uuid.uuid4().hex,'created_at':datetime.now(timezone.utc).isoformat(),
        'selection':request.model_dump(mode='json')})
    write_json(DATA/'analyses'/f"{result['run_id']}.json",result)
    return result

@router.get('/incidents')
def get_incidents():
    return {'analyses':[read_json(p,{}) for p in sorted((DATA/'analyses').glob('*.json'))],
            'interpretation':'Model-flagged deviations; no verified incident labels'}

@router.get('/aws-status')
def get_aws_status(): return status()
