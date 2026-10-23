"""Chronological banking next-step study; no fault labels in fitting or inference."""
import hashlib,json,math,copy
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit
import numpy as np
import torch
from ai_models.observed_gnn import MeasuredGraphAutoencoder

FEATURES=('client_observed_latency_ms','cpu_usage_cores','memory_percent','cpu_allowance_cores')
PROTOCOL={'bin_seconds':2,'train_seconds':36,'validation_end_seconds':48,'normal_test_end_seconds':60,
          'epochs':100,'seeds':[42,43,44],'learning_rate':.01,'width':16,
          'threshold':'Maximum validation-window next-step error, frozen before evaluation',
          'graph':'Only completed frontend CLIENT spans observed by training cutoff; peer addresses establish client-observed edges, not backend server spans',
          'development_status':'Retrospective within-recording study after exploratory inspection; not independent banking generalization'}


def frames(rows,spans,start,end):
    step=PROTOCOL['bin_seconds'];count=math.ceil((end-start)/step)
    cutoff=start+PROTOCOL['train_seconds']
    nodes=sorted({service for r in rows if r.get('instrument')=='periodic_snapshot' and r['timestamp']+r.get('collection_elapsed_ms',0)/1000<=cutoff for service in r.get('cgroups',{})})
    index={n:i for i,n in enumerate(nodes)}
    values=np.zeros((count,len(nodes),4),dtype=np.float32);mask=np.zeros_like(values)
    observations=defaultdict(list);previous={};edges={}
    def put(available,node,k,value):
        if node not in index or not math.isfinite(value) or not start<available<=end:return
        i=min(count-1,max(0,math.ceil((available-start)/step)-1))
        observations[i,index[node],k].append((available,value))
    for row in sorted(rows,key=lambda r:r['timestamp']):
        if row.get('instrument')!='periodic_snapshot':continue
        available=row['timestamp']+row.get('collection_elapsed_ms',0)/1000
        for node,data in row.get('cgroups',{}).items():
            try:
                stats={k:int(v) for k,v in (line.split() for line in data['cpu.stat'].splitlines())}
                quota,period=data['cpu.max'].split()
                if quota!='max':put(available,node,3,int(quota)/int(period))
                if data['memory.max']!='max':put(available,node,2,100*int(data['memory.current'])/int(data['memory.max']))
                before=previous.get(node)
                if before and row['timestamp']>before[0] and stats['usage_usec']>=before[1]:
                    put(available,node,1,(stats['usage_usec']-before[1])/1e6/(row['timestamp']-before[0]))
                previous[node]=(row['timestamp'],stats['usage_usec'])
            except (KeyError,ValueError,TypeError):continue
    unique={}
    for span in spans:
        key=span['trace_id'],span['span_id']
        if key in unique and unique[key]!=span:raise ValueError('Conflicting span identity')
        unique[key]=span
    for span in unique.values():
        if span.get('kind')!='CLIENT':continue
        begin=span['start_time_unix_ns']/1e9;finish=span['end_time_unix_ns']/1e9
        if finish<begin:raise ValueError('Invalid span timing')
        parent=unique.get((span['trace_id'],span.get('parent_span_id')))
        peer=urlsplit(span.get('attributes',{}).get('http.url','')).hostname
        if peer not in index:continue
        put(finish,peer,0,1000*(finish-begin))
        if parent and parent.get('kind')=='SERVER' and parent.get('service') in index and parent['start_time_unix_ns']<=span['start_time_unix_ns'] and parent['end_time_unix_ns']>=span['end_time_unix_ns'] and max(finish,parent['end_time_unix_ns']/1e9)<=cutoff:
            edges[parent['service'],peer]=max(finish,parent['end_time_unix_ns']/1e9)
    for row in rows:
        if row.get('instrument')=='payment_request':
            put(row.get('completed_at',float('inf')),'frontend',0,float(row['latency_ms']))
    for (i,j,k),points in observations.items():
        values[i,j,k]=np.quantile([p[1] for p in points],.95) if k==0 else max(points)[1]
        mask[i,j,k]=1
    graph=np.eye(len(nodes),dtype=np.float32)
    for a,b in edges:graph[index[a],index[b]]=graph[index[b],index[a]]=1
    graph/=graph.sum(axis=1,keepdims=True)
    times=[start+(i+1)*step for i in range(count)]
    return values,mask,nodes,graph,times,[{'source':a,'target':b,'observed_at':t,'coverage':'client-observed outgoing HTTP call'} for (a,b),t in sorted(edges.items())]


def fit_and_predict(rows,spans,summary,output):
    torch.set_num_threads(2)
    values,mask,nodes,graph,times,edges=frames(rows,spans,summary['started_at'],summary['ended_at'])
    a=PROTOCOL['train_seconds']//2;b=PROTOCOL['validation_end_seconds']//2;c=PROTOCOL['normal_test_end_seconds']//2
    transformed=np.log1p(values);mean=[];scale=[]
    for k in range(4):
        observed=transformed[:a,:,k][mask[:a,:,k]>0]
        mean.append(float(observed.mean()) if observed.size else 0)
        scale.append(max(.1,float(observed.std())) if observed.size else 1)
    x=torch.tensor((transformed-np.array(mean,dtype=np.float32))/np.array(scale,dtype=np.float32)*mask)
    m=torch.tensor(mask);reports=[];predictions={};output=Path(output)
    if output.exists():raise ValueError('Preserve prior study output; use a new directory')
    output.mkdir(parents=True)
    (output/'frozen-protocol.json').write_text(json.dumps(PROTOCOL,indent=2))
    source_hash=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
    def loss(pred,target,weight):return ((pred-target).square()*weight).sum()/weight.sum().clamp_min(1)
    for method,adjacency in [('graph',graph),('identity',np.eye(len(nodes),dtype=np.float32))]:
        predictions[method]=[]
        for seed in PROTOCOL['seeds']:
            torch.manual_seed(seed);model=MeasuredGraphAutoencoder();optim=torch.optim.Adam(model.parameters(),lr=PROTOCOL['learning_rate'])
            adj=torch.tensor(adjacency);best=float('inf');state=None;epoch_selected=None
            for epoch in range(PROTOCOL['epochs']):
                optim.zero_grad();training=loss(model(x[:a-1],m[:a-1],adj),x[1:a],m[1:a]);training.backward();optim.step()
                with torch.no_grad():validation=float(loss(model(x[a-1:b-1],m[a-1:b-1],adj),x[a:b],m[a:b]))
                if validation<best:best=validation;state=copy.deepcopy(model.state_dict());epoch_selected=epoch+1
            model.load_state_dict(state)
            with torch.no_grad():
                residual=(model(x[:-1],m[:-1],adj)-x[1:]).square()*m[1:]
                errors=(residual.sum((1,2))/m[1:].sum((1,2)).clamp_min(1)).numpy()
                valid_targets=m[1:].sum((1,2)).numpy()>0
                threshold=float(max(errors[a-1:b-1][valid_targets[a-1:b-1]]))
                node_errors=(residual.sum(2)/m[1:].sum(2).clamp_min(1)).numpy()
            normal=errors[b-1:c-1][valid_targets[b-1:c-1]]
            normal_flags=[bool(e>threshold) for e in normal]
            reports.append({'method':method,'seed':seed,'selected_epoch':epoch_selected,'validation_mse':best,'threshold':threshold,
                            'normal_holdout_windows':len(normal_flags),'normal_holdout_alerts':sum(normal_flags),
                            'normal_holdout_mse':float(normal.mean()) if len(normal) else None})
            series=[]
            for i in range(b-1,len(errors)):
                eligible=[j for j in range(len(nodes)) if m[i+1,j].sum()>0]
                ranking=sorted(eligible,key=lambda j:(-node_errors[i,j],nodes[j]))
                series.append({'as_of':times[i+1],'score':float(errors[i]),'has_measured_targets':bool(valid_targets[i]),'alert':bool(valid_targets[i] and errors[i]>threshold),
                               'ranking':[nodes[j] for j in ranking],'node_errors':{nodes[j]:float(node_errors[i,j]) for j in eligible}})
            predictions[method].append({'seed':seed,'threshold':threshold,'windows':series})
            torch.save({'state_dict':state,'nodes':nodes,'features':FEATURES,'mean':mean,'scale':scale,'graph':adjacency.tolist(),
                        'source_hash':source_hash,'seed':seed,'train_end':summary['started_at']+PROTOCOL['train_seconds'],'validation_end':summary['started_at']+PROTOCOL['validation_end_seconds']},output/f'{method}-{seed}.pt')
    # Persistence uses the same target masks and chronological normal holdout.
    with torch.no_grad():
        for name,predicted in [('persistence',x[:-1]),('training_mean',torch.zeros_like(x[:-1]))]:
            errors=((predicted-x[1:]).square()*m[1:]).sum((1,2))/m[1:].sum((1,2)).clamp_min(1)
            available=m[1:].sum((1,2))>0
            threshold=float(errors[a-1:b-1][available[a-1:b-1]].max())
            normal=errors[b-1:c-1][available[b-1:c-1]]
            reports.append({'method':name,'seed':None,'threshold':threshold,'normal_holdout_windows':len(normal),'normal_holdout_alerts':int((normal>threshold).sum()),'normal_holdout_mse':float(normal.mean())})
    return {'protocol':PROTOCOL,'nodes':nodes,'features':FEATURES,'edges':edges,'frames':len(times),'observed_values':int(mask.sum()),
            'source_hash':source_hash,'methods':reports,'predictions':predictions,'test_is_independent_recording':False,
            'limitations':['One retrospectively inspected AWS recording; only six nominal normal holdout bins, some without observed targets.',
                'Graph has only measured frontend client-observed edges; database dependency edges were not instrumented.',
                'Missing values are masked; no interpolation or copied future observations. Client timings are not backend server timings.',
                'Ranking errors and anomaly thresholds are not causal confidence or a validated banking production detector.']}
