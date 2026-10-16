"""Session-isolated, measured 10-second CloudWatch demonstration evidence.

This module does not execute transfers or start conditions. The explicit CLI
owns those actions; this module validates and analyzes measurements only.
"""
from __future__ import annotations
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
import hashlib,json,math,os,re,sqlite3,time
from aws.banking_publisher import (NAMESPACE,DEMO_ENVIRONMENT,connect_readonly,
    source_id,row_metrics,run_publisher,client,dimensions,finite,safe_error)

PERIOD=10
SAMPLES=4
MAX_REQUESTS=60
FRESH_SECONDS=180
SESSION_PATTERN=re.compile(r'[a-z0-9][a-z0-9-]{2,63}')
# Read the sample counts separately to detect missing or duplicated publication.
SPECS={
    'requests':('banking-api','RequestCount','Sum','Count'),
    'errors':('banking-api','ErrorCount','Sum','Count'),
    'api_ms':('banking-api','RequestLatencyMilliseconds','Average','Milliseconds'),
    'api_samples':('banking-api','RequestLatencyMilliseconds','SampleCount','Milliseconds'),
    'ledger_ms':('ledger-service','ExclusiveProcessingMilliseconds','Average','Milliseconds'),
    'ledger_samples':('ledger-service','ExclusiveProcessingMilliseconds','SampleCount','Milliseconds'),
    'ledger_service_ms':('ledger-service','ServiceLatencyMilliseconds','Average','Milliseconds'),
    'db_sum_ms':('banking-db','DBQueryMilliseconds','Sum','Milliseconds'),
    'db_samples':('banking-db','DBQueryMilliseconds','SampleCount','Milliseconds'),
}

def iso(ts):return datetime.fromtimestamp(ts,timezone.utc).isoformat()
def bucket(ts):return int(float(ts)//PERIOD)*PERIOD

def atomic_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')
    os.replace(temp,path)

def session_dir(root,name):
    if not SESSION_PATTERN.fullmatch(name):raise ValueError('Invalid demo session name.')
    return Path(root)/name

def create_session(root,name,database,region):
    directory=session_dir(root,name)
    if directory.exists():raise ValueError('Session already exists; use its evidence or choose a new name. Never reset it.')
    database=Path(database).resolve()
    with closing(connect_readonly(database)) as db:
        start_seq=db.execute('SELECT COALESCE(MAX(seq),0) FROM requests').fetchone()[0]
        sid=source_id(db,database)
    directory.mkdir(parents=True,exist_ok=False)
    with sqlite3.connect(directory/'checkpoint.db') as cp:
        cp.execute('CREATE TABLE publication(source TEXT,region TEXT,last_seq INTEGER NOT NULL DEFAULT 0,pending_seq INTEGER,PRIMARY KEY(source,region))')
        cp.execute('INSERT INTO publication VALUES(?,?,?,NULL)',(sid,region,start_seq))
    state={'session':name,'status':'prepared','region':region,'namespace':NAMESPACE,'environment':DEMO_ENVIRONMENT,
           'source':'local_measured_banking','hosting':'local','period_seconds':PERIOD,'storage_resolution':1,
           'created_at':iso(time.time()),'start_sequence':start_seq,'source_identity':sid,
           'database':str(database),'records':[],'windows':[],'publication':[],
           'baseline':None,'analysis':{'status':'insufficient_evidence'},'cloudwatch':None,
           'limits':{'max_requests':MAX_REQUESTS,'samples_per_window':SAMPLES,'normal_windows':10,'condition_windows':2,'followup_windows':3},
           'authorization_required':['test transfers','chargeable metric publication','bounded local application delay'],
           'note':'Prepared only. No transfers, metric publication or local condition was started.'}
    atomic_json(directory/'session.json',state)
    return state

def load_session(directory):
    state=json.loads((Path(directory)/'session.json').read_text(encoding='utf-8'))
    with closing(connect_readonly(state['database'])) as db:
        if source_id(db,state['database'])!=state['source_identity']:
            raise ValueError('Demo telemetry source identity changed; refusing to resume.')
    return state

def record_request(state,trace_id,window,phase):
    """Read existing measured gateway/span rows; never write banking storage."""
    if len(state['records'])>=MAX_REQUESTS:raise ValueError('Demo request safety limit reached.')
    with closing(connect_readonly(state['database'])) as db:
        row=db.execute('SELECT * FROM requests WHERE trace_id=?',(trace_id,)).fetchone()
        if row is None or row['seq']<=state['start_sequence'] or row['operation']!='transfer' or row['success']!=1:
            raise ValueError('A new successful measured transfer is required; no inferred measurement was accepted.')
        if row['seq'] in {r['sequence'] for r in state['records']}:
            raise ValueError('A measured request cannot be counted twice.')
        metrics=row_metrics(db,row)
    if any(bucket(m['Timestamp'].timestamp())!=window for m in metrics):
        raise ValueError('Measured request or child span crossed its planned observation bucket.')
    selected={}
    for field,(service,name,stat,_) in SPECS.items():
        values=[m['Value'] for m in metrics if m['MetricName']==name and any(x['Name']=='Service' and x['Value']==service for x in m['Dimensions'])]
        if not values:raise ValueError('Required measured demo feature missing: '+field)
        selected[field]=len(values) if stat=='SampleCount' else (sum(values) if stat=='Sum' else sum(values)/len(values))
    rec={'sequence':row['seq'],'timestamp':iso(row['ts']),'bucket_start':iso(window),'phase':phase,
         'values':selected,'metric_values':len(metrics)}
    state['records'].append(rec)
    return rec

def validate_source_windows(state,phase,now=None):
    now=time.time() if now is None else now
    windows=[]
    for stamp in sorted({r['bucket_start'] for r in state['records'] if r['phase']==phase}):
        records=[r for r in state['records'] if r['phase']==phase and r['bucket_start']==stamp]
        ts=datetime.fromisoformat(stamp).timestamp()
        if ts+PERIOD>now or len(records)!=SAMPLES:raise ValueError('Incomplete source observation window.')
        times=sorted(datetime.fromisoformat(r['timestamp']).timestamp() for r in records)
        if any(b-a<.5 for a,b in zip(times,times[1:])):raise ValueError('Independent paced measurements are required.')
        windows.append({'timestamp':stamp,'request_count':len(records),'sql_samples':sum(r['values']['db_samples'] for r in records)})
    if any(datetime.fromisoformat(b['timestamp']).timestamp()-datetime.fromisoformat(a['timestamp']).timestamp()!=PERIOD for a,b in zip(windows,windows[1:])):
        raise ValueError('Source windows are nonconsecutive.')
    return windows

def publish_new(state,directory,profile=None,cw=None):
    seqs=[r['sequence'] for r in state['records']]
    if not seqs:raise ValueError('No new measured session requests to publish.')
    if min(seqs)<=state['start_sequence']:raise ValueError('Session manifest contains historical backlog.')
    if sum(r['metric_values'] for r in state['records'])>2000:raise ValueError('Demo metric-value budget exceeded.')
    # Send complete phases outside timed measurement windows. Each call still
    # obeys the existing twenty-request bound and durable ambiguity safeguards.
    for _ in range(3):
        result=run_publisher(state['database'],Path(directory)/'checkpoint.db',state['region'],profile=profile,
                             publish=True,limit=20,cw=cw,environment=DEMO_ENVIRONMENT,storage_resolution=1,allowed_sequences=seqs)
        state['publication'].append(result)
        if result['status'] not in ('published','no_new_requests'):
            raise ValueError('Demo publication stopped: '+result['status']+' '+result.get('error_code',''))
        if result['status']=='no_new_requests' or result['last_confirmed_sequence']>=max(seqs):return result
    raise ValueError('Demo publication phase exceeded the bounded drain limit.')

def collect_demo(state,profile=None,cw=None,now=None):
    """Read the demo environment and original session interval, at 10 seconds."""
    now=time.time() if now is None else now
    starts=[datetime.fromisoformat(r['bucket_start']).timestamp() for r in state['records']]
    result={'source':'aws_cloudwatch','environment':DEMO_ENVIRONMENT,'period_seconds':PERIOD,
            'region':state['region'],'hosting':'local','collected_at':iso(now),'series':{},
            'collection_complete':False,'api_calls':0,'errors':[],'buckets':[]}
    if not starts:return result
    queries=[];statuses={};points={key:{} for key in SPECS}
    for key,(service,name,stat,unit) in SPECS.items():
        dims=[{**d,'Value':DEMO_ENVIRONMENT} if d['Name']=='Environment' else d for d in dimensions(service,'transfer')]
        queries.append({'Id':key,'MetricStat':{'Metric':{'Namespace':NAMESPACE,'MetricName':name,'Dimensions':dims},'Period':PERIOD,'Stat':stat,'Unit':unit},'ReturnData':True})
    try:
        cw=cw or client(state['region'],profile)
        token=None;seen=set()
        for _ in range(10):
            args={'MetricDataQueries':queries,'StartTime':datetime.fromtimestamp(min(starts),timezone.utc),
                  'EndTime':datetime.fromtimestamp(min(bucket(now),max(starts)+PERIOD),timezone.utc),
                  'ScanBy':'TimestampAscending','MaxDatapoints':10080}
            if token:args['NextToken']=token
            response=cw.get_metric_data(**args);result['api_calls']+=1
            result['errors'].extend({'code':x.get('Code','CloudWatchMessage')} for x in response.get('Messages',[]))
            for entry in response.get('MetricDataResults',[]):
                key=entry.get('Id')
                if key not in points:result['errors'].append({'code':'UnknownMetricId'});continue
                status=entry.get('StatusCode','omitted')
                # A later complete page must not erase an earlier partial/error status.
                statuses[key]=status if statuses.get(key,'Complete')=='Complete' else statuses[key]
                if entry.get('Messages'):result['errors'].append({'code':'MetricMessage','metric':key})
                if len(entry.get('Timestamps',[]))!=len(entry.get('Values',[])):
                    result['errors'].append({'code':'MismatchedMetricLengths','metric':key});continue
                for ts,value in zip(entry.get('Timestamps',[]),entry.get('Values',[])):
                    if not isinstance(ts,datetime) or not ts.tzinfo or not finite(value):
                        result['errors'].append({'code':'InvalidDatapoint','metric':key});continue
                    stamp=ts.timestamp()
                    if stamp!=bucket(stamp) or stamp<min(starts) or stamp+PERIOD>now or stamp>max(starts):
                        result['errors'].append({'code':'InvalidObservationPeriod','metric':key});continue
                    canonical=iso(stamp)
                    if canonical in points[key] and points[key][canonical]!=float(value):
                        result['errors'].append({'code':'ConflictingDuplicatePoint','metric':key})
                    points[key][canonical]=float(value)
            token=response.get('NextToken')
            if not token:break
            if token in seen:raise ValueError('Repeated pagination token.')
            seen.add(token)
        else:raise ValueError('Demo pagination safety limit reached.')
    except Exception as exc:result['errors'].append({'code':safe_error(exc)})
    result['collection_complete']=not result['errors'] and all(statuses.get(key)=='Complete' for key in SPECS)
    for key,spec in SPECS.items():
        result['series'][key]={'service':spec[0],'metric_name':spec[1],'statistic':spec[2],'unit':spec[3],
                               'response_status':statuses.get(key,'omitted'),'points':[{'timestamp':ts,'value':v} for ts,v in sorted(points[key].items())]}
    for stamp in sorted({r['bucket_start'] for r in state['records']}):
        records=[r for r in state['records'] if r['bucket_start']==stamp]
        expected=len(records);sql_expected=sum(r['values']['db_samples'] for r in records)
        values={k:v.get(stamp) for k,v in points.items()}
        complete=(result['collection_complete'] and expected==SAMPLES and all(v is not None for v in values.values())
                  and all(values[k]==expected for k in ('requests','api_samples','ledger_samples'))
                  and values['db_samples']==sql_expected)
        result['buckets'].append({'timestamp':stamp,'values':values,'complete':complete,
                                  'expected_requests':expected,'expected_sql_samples':sql_expected,
                                  'missing_metrics':[k for k,v in values.items() if v is None]})
    result['status']='observations_available' if result['collection_complete'] and all(b['complete'] for b in result['buckets']) else 'pending_or_incomplete_data'
    return result

def freeze_reference(state,cloud,now=None):
    now=time.time() if now is None else now
    windows=validate_source_windows(state,'normal',now)
    if len(windows)!=10:raise ValueError('Exactly ten consecutive normal windows and forty independent observations are required.')
    expected=[w['timestamp'] for w in windows]
    if now-(datetime.fromisoformat(expected[-1]).timestamp()+PERIOD)>FRESH_SECONDS:
        raise ValueError('Normal reference is stale for a new live condition.')
    rows=[b for b in cloud['buckets'] if b['timestamp'] in expected]
    if not cloud['collection_complete'] or len(rows)!=10 or any(not b['complete'] for b in rows):
        raise ValueError('CloudWatch baseline is pending or incomplete.')
    if any(b['values']['errors']!=0 for b in rows):raise ValueError('Normal baseline contains measured errors.')
    features={}
    for field in ('api_ms','ledger_ms','db_sum_ms'):
        vals=[r['values'][field]/r['values']['requests'] if field=='db_sum_ms' else r['values'][field] for r in rows]
        reference=vals[:6];calibration=vals[6:]
        center=median(reference);mad=median(abs(v-center) for v in reference)
        threshold=max(center+max(25.0,center*.75,6*1.4826*mad),max(calibration)*1.1)
        features[field]={'median':center,'mad':mad,'threshold':threshold,'reference_windows':6,'calibration_windows':4,
                         'normal_values':vals,'unit':'Milliseconds','aggregation':'SQL sum / measured requests' if field=='db_sum_ms' else 'CloudWatch Average'}
    normal={'status':'frozen','frozen_at':iso(now),'end':iso(datetime.fromisoformat(expected[-1]).timestamp()+PERIOD),
            'bucket_timestamps':expected,'request_count':40,'features':features,'source':'aws_cloudwatch',
            'rule':'Six chronological reference windows, four calibration windows; median/MAD threshold with 25 ms floor; two consecutive complete periods.'}
    normal['sha256']=hashlib.sha256(json.dumps(normal,sort_keys=True).encode()).hexdigest()
    return normal

def analyze_demo(cloud,baseline,now=None):
    """Predictions use frozen normal thresholds and CloudWatch values, never labels."""
    now=time.time() if now is None else now
    result={'status':'insufficient_evidence','affected_service':None,'root_cause':'not_established','gnn_used':False,
            'detected_periods':[],'evaluated':[],'followup':{'status':'not_established'},
            'verification_scope':'Measured application slowdown; CloudWatch aggregates do not confirm physical causality.'}
    if not baseline or baseline.get('status')!='frozen' or not cloud.get('collection_complete'):return result
    rows=[r for r in cloud['buckets'] if r['timestamp']>=baseline['end']]
    pairs=[]
    for row in rows:
        stamp=datetime.fromisoformat(row['timestamp']).timestamp()
        eligible=row['complete'] and 0<=now-(stamp+PERIOD)<=FRESH_SECONDS
        scores={};values={}
        if eligible:
            for feature in ('api_ms','ledger_ms','db_sum_ms'):
                value=row['values'][feature]/row['values']['requests'] if feature=='db_sum_ms' else row['values'][feature]
                reference=baseline['features'][feature]
                values[feature]=value;scores[feature]=(value-reference['median'])/(reference['threshold']-reference['median'])
        hit=eligible and scores['api_ms']>1 and scores['ledger_ms']>1 and row['values']['errors']==0
        result['evaluated'].append({'timestamp':row['timestamp'],'eligible':eligible,'scores':scores,'values':values,
                                    'deviation':bool(hit),'complete':row['complete']})
    for a,b in zip(result['evaluated'],result['evaluated'][1:]):
        consecutive=datetime.fromisoformat(b['timestamp']).timestamp()-datetime.fromisoformat(a['timestamp']).timestamp()==PERIOD
        if consecutive and a['deviation'] and b['deviation']:pairs.append([a,b])
    if not pairs:
        result['status']='no_persistent_deviation' if any(x['eligible'] for x in result['evaluated']) else 'insufficient_evidence'
        return result
    first=pairs[0];result.update(status='abnormal_latency_detected',affected_service='ledger-service',
                                detected_periods=[x['timestamp'] for x in first],detection_scores=[x['scores'] for x in first])
    later=[x for x in result['evaluated'] if x['timestamp']>first[-1]['timestamp'] and x['eligible']]
    for a,b in zip(later,later[1:]):
        if datetime.fromisoformat(b['timestamp']).timestamp()-datetime.fromisoformat(a['timestamp']).timestamp()!=PERIOD:continue
        if all(x['scores']['api_ms']<=1 and x['scores']['ledger_ms']<=1 for x in (a,b)):
            result['followup']={'status':'measured_return_toward_frozen_reference','periods':[a['timestamp'],b['timestamp']],
                                'values':[a['values'],b['values']],'causal_recovery':'not_established'};break
    return result

def trace_corroboration(state,analysis):
    stamps=set(analysis.get('detected_periods',[]))
    records=[r for r in state['records'] if r['bucket_start'] in stamps]
    if not records:return {'status':'insufficient_evidence'}
    return {'status':'measured_local_spans','requests':len(records),
            'ledger_exclusive_ms':sum(r['values']['ledger_ms'] for r in records)/len(records),
            'api_handler_ms':sum(r['values']['api_ms'] for r in records)/len(records),
            'sql_ms_per_request':sum(r['values']['db_sum_ms'] for r in records)/len(records),
            'source':'Original local HTTP/SQL spans matched to detected bucket timestamps; no control labels used.',
            'root_cause':'not_established'}

def public_report(state):
    """Do not expose local file paths or per-request/transaction identifiers to UI."""
    return {k:v for k,v in state.items() if k not in ('database','source_identity','records','authorization_required')}
