"""Banking-only next-request GNN and identity comparison; no transferred weights."""
import json,hashlib,copy
import numpy as np
import torch
from banking import store
from ai_models.observed_gnn import MeasuredGraphAutoencoder
FEATURES=('latency_ms','processing_ms','db_latency_ms','db_connection_ms')

def arrays(case):
    nodes=sorted({s.resource for s in case.series});times=sorted({p.timestamp for s in case.series for p in s.observations});ni={n:i for i,n in enumerate(nodes)};ti={t:i for i,t in enumerate(times)}
    x=np.zeros((len(times),len(nodes),4),dtype=np.float32);mask=np.zeros_like(x)
    for s in case.series:
        if s.metric not in FEATURES:continue
        for p in s.observations:
            if p.value is not None:x[ti[p.timestamp],ni[s.resource],FEATURES.index(s.metric)]=np.log1p(max(0,p.value));mask[ti[p.timestamp],ni[s.resource],FEATURES.index(s.metric)]=1
    return nodes,times,x,mask

def train(case,calibration):
    torch.set_num_threads(2);nodes,times,raw,mask=arrays(case)
    a=sum(t<=calibration['reference_end'] for t in times);b=sum(t<=calibration['validation_end'] for t in times)
    if a<20 or b-a<5 or len(times)-b<5:return {'status':'insufficient_normal_training_history'}
    mean=np.array([raw[:a,:,k][mask[:a,:,k]>0].mean() if mask[:a,:,k].sum() else 0 for k in range(4)],dtype=np.float32)
    scale=np.array([max(.1,raw[:a,:,k][mask[:a,:,k]>0].std()) if mask[:a,:,k].sum() else 1 for k in range(4)],dtype=np.float32)
    x=torch.tensor((raw-mean)/scale*mask);m=torch.tensor(mask);adj=torch.eye(len(nodes));ni={n:i for i,n in enumerate(nodes)}
    edges=[e for e in case.edges if e.observed_at is not None and e.observed_at<=calibration['reference_end']]
    for e in edges:adj[ni[e.source],ni[e.target]]=1;adj[ni[e.target],ni[e.source]]=1
    adj=adj/adj.sum(1,keepdim=True);results={}
    def loss(pred,target,observed):return (((pred-target)**2)*observed).sum()/observed.sum().clamp_min(1)
    for name,graph in [('identity',torch.eye(len(nodes))),('graph',adj)]:
        torch.manual_seed(42);model=MeasuredGraphAutoencoder();opt=torch.optim.Adam(model.parameters(),lr=.01);best=float('inf');state=None
        for epoch in range(100):
            opt.zero_grad();error=loss(model(x[:a-1],m[:a-1],graph),x[1:a],m[1:a]);error.backward();opt.step()
            with torch.no_grad():validation=float(loss(model(x[a:b-1],m[a:b-1],graph),x[a+1:b],m[a+1:b]))
            if validation<best:best=validation;state=copy.deepcopy(model.state_dict())
        model.load_state_dict(state)
        with torch.no_grad():
            pred=model(x[b:-1],m[b:-1],graph);test_loss=float(loss(pred,x[b+1:],m[b+1:]))
            val=((model(x[a:b-1],m[a:b-1],graph)-x[a+1:b])**2*m[a+1:b]).sum((1,2))/m[a+1:b].sum((1,2)).clamp_min(1)
            threshold=float(torch.quantile(val,.95))
            test=((pred-x[b+1:])**2*m[b+1:]).sum((1,2))/m[b+1:].sum((1,2)).clamp_min(1)
        artifact={'state_dict':state,'nodes':nodes,'features':list(FEATURES),'mean':mean.tolist(),'scale':scale.tolist(),'adjacency':graph.tolist(),'calibration_id':calibration['id'],'source':'banking-local','operation':'transfer','train_end':calibration['reference_end'],'training_digest':case.provenance['telemetry_sha256'],'validation_threshold':threshold,'edges':[(e.source,e.target) for e in edges]}
        target=store.root()/f"{calibration['id']}-{name}.pt";torch.save(artifact,target)
        # Verify saved weights perform identically, with no serialized executable objects.
        restored=torch.load(target,map_location='cpu',weights_only=True);clone=MeasuredGraphAutoencoder();clone.load_state_dict(restored['state_dict'])
        with torch.no_grad():verified=bool(torch.allclose(clone(x[b:-1],m[b:-1],graph),pred))
        results[name]={'validation_next_request_mse':best,'heldout_next_request_mse':test_loss,'normal_heldout_predictions':len(test),'normal_false_alarm_rate':float((test>threshold).float().mean()),'validation_residual_threshold':threshold,'serialization_verified':verified}
    report={'status':'trained_and_evaluated','calibration_id':calibration['id'],'source':'banking-local','task':'Next-request masked prediction, not same-point reconstruction. Separate models trained from measured normal banking requests only.','features':FEATURES,'nodes':nodes,'requests':len(times),'split_counts':{'train':a,'validation':b-a,'test':len(times)-b},'seed':42,'epochs':100,'comparison':results,'edge_direction':'Original directed call graph displayed; symmetrized row-normalized message passing only for model comparison.','ranking_used':False,'reason':'No independently validated incremental localization benefit. Predictions are separate graph evidence, not a claimed GNN root cause.','limitations':['Small local normal dataset; no production generalization or calibrated fault probability.','Per-request windows under a documented workload, not fixed-period CloudWatch windows.','Different node features are masked; missing values are not reported as measured zero.']}
    (store.root()/'graph-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report

def infer(case):
    cal=case.provenance.get('calibration_id')
    if case.source.id!='banking-local' or case.provenance.get('operation')!='transfer':return {'status':'domain_not_compatible','ranking_used':False}
    paths={name:store.root()/f'{cal}-{name}.pt' for name in ('identity','graph')}
    if not all(p.exists() for p in paths.values()):return {'status':'not_trained_for_current_baseline','ranking_used':False}
    nodes,times,raw,mask=arrays(case)
    if len(times)<2:return {'status':'insufficient_history','ranking_used':False}
    output={}
    for name,path in paths.items():
        state=torch.load(path,map_location='cpu',weights_only=True)
        if times[-2]<state['train_end']:return {'status':'prefix_precedes_training_completion','ranking_used':False}
        if state['source']!=case.source.id or state['calibration_id']!=cal or state['nodes']!=nodes or state['features']!=list(FEATURES):return {'status':'domain_mismatch','ranking_used':False}
        if set(map(tuple,state['edges']))!={(e.source,e.target) for e in case.edges}:return {'status':'topology_mismatch','ranking_used':False}
        x=torch.tensor((raw[-2:]-np.asarray(state['mean']))/np.asarray(state['scale'])*mask[-2:],dtype=torch.float32);m=torch.tensor(mask[-2:]);adj=torch.tensor(state['adjacency'])
        model=MeasuredGraphAutoencoder();model.load_state_dict(state['state_dict']);model.eval()
        with torch.no_grad():
            squared=(model(x[:1],m[:1],adj)-x[1:])**2*m[1:];score=(squared.sum((0,2))/m[1:].sum((0,2)).clamp_min(1)).numpy()
        order=sorted(nodes,key=lambda n:(-float(score[nodes.index(n)]),n))
        output[name]={'node_residuals':{n:float(score[i]) for i,n in enumerate(nodes)},'ranking':order,'target_time':times[-1],'input_latest_time':times[-2],'feature_squared_errors':squared[0].tolist(),'residual_definition':'Masked squared error in training-normalized log1p metrics; not milliseconds or fault probability.'}
    return {'status':'evaluated','source':'banking-local','calibration_id':cal,'ranking_used':False,'models':output,'role':'Actual next-request model inference evidence; primary location uses measured exclusive-time attribution.'}
