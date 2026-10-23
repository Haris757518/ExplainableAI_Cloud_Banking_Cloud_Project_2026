"""Live masked GNN inference followed by bounded direct-evidence investigation.

The checkpoint is frozen from the earlier measured workload. Current labels,
control names and operator action records are never inputs to this module.
"""
import hashlib,math
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

@lru_cache(maxsize=1)
def model_bundle():
    import torch
    from ai_models.observed_gnn import MeasuredGraphAutoencoder
    path=Path(__file__).resolve().parents[1]/'results/final_validation/banking-models/graph-42.pt'
    checkpoint=torch.load(path,map_location='cpu',weights_only=True)
    model=MeasuredGraphAutoencoder();model.load_state_dict(checkpoint['state_dict']);model.eval()
    return model,checkpoint,hashlib.sha256(path.read_bytes()).hexdigest()

def stats(data):
    return {k:int(v) for k,v in (line.split() for line in data.get('cpu.stat','').splitlines())}

def rank(value,now):
    import torch
    samples=[s for s in value.get('resource_samples',[]) if s['timestamp']+s.get('collection_elapsed_ms',0)/1000<=now]
    if len(samples)<2:return {'status':'unavailable','reason':'Waiting for consecutive live resource samples.'}
    model,checkpoint,sha=model_bundle();nodes=checkpoint['nodes']
    def features(sample,prior):
        values=torch.zeros(len(nodes),4);mask=torch.zeros_like(values)
        cutoff=sample['timestamp']+sample.get('collection_elapsed_ms',0)/1000
        def put(node,k,v):
            if node in nodes and math.isfinite(v) and v>=0:values[nodes.index(node),k]=v;mask[nodes.index(node),k]=1
        for node,data in sample.get('cgroups',{}).items():
            try:
                q,p=data['cpu.max'].split()
                if q!='max':put(node,3,int(q)/int(p))
                if data['memory.max']!='max':put(node,2,100*int(data['memory.current'])/int(data['memory.max']))
                if prior and node in prior.get('cgroups',{}):
                    elapsed=sample['timestamp']-prior['timestamp']
                    if elapsed>0:put(node,1,(stats(data)['usage_usec']-stats(prior['cgroups'][node])['usage_usec'])/1e6/elapsed)
            except (KeyError,ValueError,TypeError):pass
        latencies=[r['latency_ms'] for r in value['requests'] if cutoff-15<=r.get('completed_at',float('inf'))<=cutoff]
        if latencies:put('frontend',0,max(latencies))
        for span in value.get('client_spans',[]):
            end=span['end_time_unix_ns']/1e9;begin=span['start_time_unix_ns']/1e9
            if end<=cutoff and end>=cutoff-15:put(urlsplit(span.get('attributes',{}).get('http.url','')).hostname,0,1000*(end-begin))
        x=(torch.log1p(values)-torch.tensor(checkpoint['mean']))/torch.tensor(checkpoint['scale'])*mask
        return x,mask
    previous,pm=features(samples[-2],samples[-3] if len(samples)>2 else None)
    current,cm=features(samples[-1],samples[-2])
    with torch.no_grad():
        residual=(model(previous,pm,torch.tensor(checkpoint['graph']))-current).square()*cm
        error=residual.sum(1)/cm.sum(1).clamp_min(1)
    ranking=sorted([{'service':node,'score':round(float(error[i]),4)} for i,node in enumerate(nodes) if cm[i].sum()>0],key=lambda r:-r['score'])
    return {'status':'evaluated','ranking':ranking,'checkpoint_sha256':sha,'source':'Frozen earlier AWS-trained graph-42; inference on current measurements','limits':'Sampling cadence differs from training; ranking is a symptom score, not a validated live cause probability. Frozen graph is prior measured topology.'}

def investigate_live(value,*,now):
    queries=[];causes=[]
    def inspect(name,evidence):
        if len(queries)>=8:return None
        queries.append({'measurement':name,'observed':evidence});return evidence
    try:gnn=rank(value,now)
    except (OSError,ValueError,KeyError,RuntimeError,ImportError,TypeError) as exc:gnn={'status':'unavailable','reason':type(exc).__name__}
    samples=value.get('resource_samples',[]);reference=value.get('resource_reference') or {}
    if samples and now-samples[-1]['timestamp']<25:
        for node,data in samples[-1].get('cgroups',{}).items():
            try:
                before=reference['cgroups'][node]['cpu.max'].split();after=data['cpu.max'].split()
                ratio_before=int(before[0])/int(before[1]);ratio_after=int(after[0])/int(after[1])
                if ratio_after<ratio_before*.5:
                    inspect('actual_cgroup_cpu_allowance',{'service':node,'before_cores':ratio_before,'now_cores':ratio_after})
                    prev=stats(samples[-2]['cgroups'][node]);curr=stats(data)
                    throttled=inspect('cgroup_throttling_delta',curr.get('throttled_usec',0)-prev.get('throttled_usec',0))
                    if throttled>0:causes.append({'service':node,'cause':'CPU restriction with measured throttling','deeper_cause':'The container exhausted its reduced CPU allowance and was throttled. Who changed the limit is not established.','recommendation':'Restore the approved CPU allowance; check latency and transaction integrity.'})
            except (KeyError,ValueError,TypeError,IndexError):pass
    database=value.get('database',{})
    if 0<=now-database.get('timestamp',0)<25:
        blocked=inspect('database_blocked_sessions',database.get('blocked_sessions'))
        if blocked:
            locks=inspect('database_lock_details',database.get('locks',[]))
            exclusive=any(r.get('granted') and r.get('mode')=='AccessExclusiveLock' and r.get('relation')=='transactions' for r in locks)
            causes.append({'service':'ledger-db','cause':'Database transactions are blocked','deeper_cause':'An open transaction holds an exclusive lock on the transactions table, preventing other transactions from proceeding.' if exclusive else 'Blocked sessions are observed; the exact blocking mechanism remains unresolved.','recommendation':'Inspect the blocking transaction. After it ends, verify balances against the ledger.'})
    return {'as_of':now,'gnn':gnn,'probe_xai':{'status':'supported_contributor' if causes else 'not_established','queries':queries,'measurement_groups_inspected':len(queries),'causes':causes,'driver_attribution':'Not established: no operator audit records supplied.'}}
