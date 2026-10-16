"""Same measured split, seed and architecture, with topology versus identity."""
from pathlib import Path
import sys,json,argparse,time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dataset.alibaba_adapter import build_snapshot
from ai_models.observed_gnn import train_observed,MeasuredGraphAutoencoder,FEATURES
import numpy as np
import torch

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--epochs',type=int,default=100);parser.add_argument('--training-topology',action='store_true');args=parser.parse_args()
    out=Path(args.out)
    if out.exists():raise SystemExit('Choose a new output directory; preserve previous results.')
    out.mkdir(parents=True)
    if args.training_topology:
        from dataset.observed_trace import measured_snapshot
        sample=measured_snapshot('dataset/raw/alibaba',max_rows=100000,window_ms=5000,selection_end_ms=175000).to_analysis_sample()
        sample.metadata['topology_partitioning']='Node/edge selection uses only measured calls through 175000ms; no later call frequencies or edges choose the topology.'
        times=sorted({p['timestamp_ms'] for metrics in sample.metadata['series'].values() for points in metrics.values() for p in points})
        if times[int(.6*len(times))-1]<175000:raise ValueError('Topology cutoff exceeds actual training partition')
    else:sample=build_snapshot('dataset/raw/alibaba',max_rows=100000,window_ms=5000).to_analysis_sample()
    started=time.perf_counter()
    graph=train_observed(sample,out/'topology.pt',epochs=args.epochs)
    identity=train_observed(sample.model_copy(update={'edges':[]}),out/'identity.pt',epochs=args.epochs)
    state=torch.load(out/'topology.pt',map_location='cpu',weights_only=True);nodes=state['node_ids'];index={n:i for i,n in enumerate(nodes)}
    t=max(p['timestamp_ms'] for metrics in sample.metadata['series'].values() for metric,points in metrics.items() if metric in FEATURES for p in points)
    values=np.zeros((len(nodes),len(FEATURES)),dtype=np.float32);mask=np.zeros_like(values)
    for node,metrics in sample.metadata['series'].items():
        if node not in index:continue
        for metric,points in metrics.items():
            if metric not in FEATURES:continue
            for p in points:
                if p['timestamp_ms']==t:values[index[node],FEATURES.index(metric)]=np.log1p(p['value']);mask[index[node],FEATURES.index(metric)]=1
    x=torch.tensor(((values-np.asarray(state['means']))/np.asarray(state['scales']))*mask,dtype=torch.float32);m=torch.tensor(mask)
    model=MeasuredGraphAutoencoder();model.load_state_dict(state['state_dict']);model.eval()
    def adjacency(exclude=None):
        a=torch.eye(len(nodes))
        for i,e in enumerate(sample.edges):
            if i==exclude:continue
            a[index[e.source],index[e.target]]=a[index[e.target],index[e.source]]=1
        return a/a.sum(dim=1,keepdim=True)
    def loss(input_values,input_mask,a):
        with torch.no_grad():return float(((model(input_values,input_mask,a)-x).square()*m).sum()/m.sum())
    original=loss(x,m,adjacency());edge_sensitivity=[];feature_sensitivity=[]
    for i,e in enumerate(sample.edges):
        ablated=loss(x,m,adjacency(i));edge_sensitivity.append({'source':e.source,'target':e.target,'reconstruction_mse_delta':ablated-original})
    for k,metric in enumerate(FEATURES):
        xx=x.clone();mm=m.clone();xx[:,k]=0;mm[:,k]=0
        feature_sensitivity.append({'feature':metric,'reconstruction_mse_delta':loss(xx,mm,adjacency())-original})
    report={'dataset':'Alibaba measured bounded 100000-row trace','seed':42,'epochs':args.epochs,'architecture':'same width-16 masked graph autoencoder; directed recorded calls are symmetrized by this existing model','topology':graph,'no_graph_identity':identity,'train_mean_mse':graph['train_mean_baseline_test_mse'],'graph_minus_no_graph_test_mse':graph['test_masked_mse']-identity['test_masked_mse'],'explanation_fidelity':{'kind':'computed model-input/edge removal sensitivity, not causal intervention on source data','latest_heldout_mse':original,'feature_removal':feature_sensitivity,'edge_removal':sorted(edge_sensitivity,key=lambda e:abs(e['reconstruction_mse_delta']),reverse=True)},'limitations':['Reconstruction, not classification or localization accuracy.',graph['topology_partitioning'],'No graph-informed RCA accuracy comparison is possible from unlabelled Alibaba traces or metric-only RE1.','Zero mask fillers are internal tensors, never exported as observations.'],'elapsed_seconds':time.perf_counter()-started}
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:report[k] for k in ('graph_minus_no_graph_test_mse','train_mean_mse','elapsed_seconds')}));print('topology',graph['test_masked_mse'],'identity',identity['test_masked_mse'])

if __name__=='__main__':main()
