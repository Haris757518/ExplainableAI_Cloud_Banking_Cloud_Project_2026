"""Per-recording normal-prefix GNN; small illustrative study, no transfer."""
from pathlib import Path
import sys,json,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from dataset.re2 import entries,load_re2,truth_re2
from ai_models.observed_gnn import MeasuredGraphAutoencoder

def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);args=parser.parse_args();out=Path(args.out)
    if out.exists():raise SystemExit('Preserve prior outputs; choose a new directory.')
    out.mkdir(parents=True);results=[];torch.set_num_threads(2)
    for entry in entries()['cases']:
        case=load_re2(entry['id']);times=sorted({p.timestamp for s in case.series for p in s.observations});first,end=times[0],times[-1];train_end=first+.2*(end-first);val_end=first+.3*(end-first);checkpoint=first+.5*(end-first)+120
        features=('cpu','mem','latency-90','workload');nodes=sorted({s.resource for s in case.series if s.metric in features});ni={n:i for i,n in enumerate(nodes)};ti={t:i for i,t in enumerate(times)}
        values=np.zeros((len(times),len(nodes),4),dtype=np.float32);mask=np.zeros_like(values)
        for s in case.series:
            if s.resource not in ni or s.metric not in features:continue
            for p in s.observations:
                if p.value is not None:
                    values[ti[p.timestamp],ni[s.resource],features.index(s.metric)]=np.sign(p.value)*np.log1p(abs(p.value));mask[ti[p.timestamp],ni[s.resource],features.index(s.metric)]=1
        a=sum(t<=train_end for t in times);b=sum(t<=val_end for t in times);c=sum(t<=checkpoint for t in times)
        mean=np.array([values[:a,:,k][mask[:a,:,k]>0].mean() if mask[:a,:,k].sum() else 0. for k in range(4)],dtype=np.float32);scale=np.array([max(.1,values[:a,:,k][mask[:a,:,k]>0].std()) if mask[:a,:,k].sum() else 1. for k in range(4)],dtype=np.float32)
        x=torch.tensor((values-mean)/scale*mask);m=torch.tensor(mask);adj=torch.eye(len(nodes));used=[]
        for edge in case.edges:
            if edge.observed_at<=train_end and edge.source in ni and edge.target in ni:
                adj[ni[edge.source],ni[edge.target]]=1;adj[ni[edge.target],ni[edge.source]]=1;used.append(edge.model_dump())
        adj=adj/adj.sum(1,keepdim=True);models={}
        for name,graph in [('identity',torch.eye(len(nodes))),('recorded_graph',adj)]:
            torch.manual_seed(42);model=MeasuredGraphAutoencoder();optim=torch.optim.Adam(model.parameters(),lr=.01);best=float('inf');state=None
            def loss(pred,target,mask):return (((pred-target)**2)*mask).sum()/mask.sum().clamp_min(1)
            # Predict next observation, avoiding the identity reconstruction shortcut.
            for epoch in range(100):
                optim.zero_grad();error=loss(model(x[:a-1],m[:a-1],graph),x[1:a],m[1:a]);error.backward();optim.step()
                with torch.no_grad():validation=float(loss(model(x[a:b-1],m[a:b-1],graph),x[a+1:b],m[a+1:b]))
                if validation<best:best=validation;state=copy.deepcopy(model.state_dict())
            model.load_state_dict(state)
            with torch.no_grad():
                residual=(model(x[max(b,c-21):c-1],m[max(b,c-21):c-1],graph)-x[max(b,c-21)+1:c])**2*m[max(b,c-21)+1:c]
                scores=(residual.sum((0,2))/m[max(b,c-21)+1:c].sum((0,2)).clamp_min(1)).numpy();order=sorted(nodes,key=lambda n:(-float(scores[ni[n]]),n))
            models[name]={'ranking':order,'validation_next_step_mse':best,'mean_recent_next_step_mse':float(residual.sum()/m[max(b,c-21)+1:c].sum().clamp_min(1))}
            torch.save({'state_dict':state,'features':features,'nodes':nodes,'mean':mean.tolist(),'scale':scale.tolist(),'raw_sha256':entry['sha256'],'trace_sha256':entry['checksums']['traces.parquet'],'train_end':train_end,'validation_end':val_end,'checkpoint':checkpoint,'graph':graph.tolist(),'seed':42},out/(case.id+'_'+name+'.pt'))
        truth=truth_re2(case.id) # no labels used during fitting/ranking
        for model in models.values():
            rank=model['ranking'].index(truth['root_cause_service'])+1 if truth['root_cause_service'] in model['ranking'] else None
            model.update(rank=rank,top1=rank==1,top3=rank is not None and rank<=3)
        results.append({'case_id':case.id,'models':models,'edges':used,'train_end':train_end,'validation_end':val_end,'checkpoint':checkpoint,'truth':truth,'warmup_precedes_injection':val_end<truth['inject_time']});print(case.id,flush=True)
    report={'protocol':'Five preselected RE2-OB recordings; independent per-case normal-prefix training20%, validation next10%, fixed midpoint+120s diagnosis. Actual parent-child topology restricted to completed training-prefix spans. Same seed42, architecture,100epochs; best validation weights. Four source metrics, training-only scaling. No cross-recording weights or labels used in model fitting.','cases':results,'summary':{name:{'cases':len(results),'top1':sum(r['models'][name]['top1'] for r in results)/len(results),'top3':sum(r['models'][name]['top3'] for r in results)/len(results)} for name in ('identity','recorded_graph')},'limitations':['Five illustrative recordings, not a representative accuracy benchmark; no superiority inference.','Graph is symmetrized for message passing; UI retains original recorded direction.','Metrics only; trace topology is not proof of a propagation mechanism.','Underlying mechanisms evaluated separately; no causal confidence or cross-domain transfer.']}
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report['summary']))
if __name__=='__main__':main()
