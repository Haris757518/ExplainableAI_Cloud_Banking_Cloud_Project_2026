"""Compatible RE2 next-step model inference; never reuse Alibaba weights."""
from pathlib import Path
import numpy as np
import torch
from ai_models.observed_gnn import MeasuredGraphAutoencoder

ROOT=Path(__file__).resolve().parents[1]

def checkpoint_path(case_id,variant):
    updated=ROOT/'results/probe_xai/re2_models'/f'{case_id}_{variant}.pt'
    return updated if updated.exists() else ROOT/'results/research_v4/re2_graph_20261016_02'/f'{case_id}_{variant}.pt'

def infer(case,as_of,variant='recorded_graph'):
    if variant not in {'recorded_graph','identity'}:raise ValueError('Unknown model variant')
    path=checkpoint_path(case.id,variant)
    if not path.exists():return {'status':'not_applied','reason':'No compatible RE2 checkpoint for this recording.'}
    state=torch.load(path,map_location='cpu',weights_only=True)
    if state['raw_sha256']!=case.collection or state['trace_sha256']!=case.provenance.get('trace_sha256'):
        return {'status':'not_applied','reason':'Measured source checksum differs from checkpoint.'}
    if as_of<=state['validation_end']:return {'status':'not_applied','reason':'Observation must be later than model training and validation.'}
    nodes=state['nodes'];features=state['features'];ni={n:i for i,n in enumerate(nodes)}
    available=sorted({p.timestamp for s in case.series if s.resource in ni and s.metric in features for p in s.observations if p.timestamp<=as_of})
    first_target=next((i for i,t in enumerate(available) if t>state['validation_end']),len(available))
    times=available[max(0,first_target-1):][-21:]
    if len(times)<3:return {'status':'not_applied','reason':'Insufficient held-out temporal pairs.'}
    ti={t:i for i,t in enumerate(times)}
    values=np.zeros((len(times),len(nodes),len(features)),dtype=np.float32);mask=np.zeros_like(values)
    for s in case.series:
        if s.resource not in ni or s.metric not in features:continue
        for p in s.observations:
            if p.timestamp in ti and p.value is not None:
                i,j,k=ti[p.timestamp],ni[s.resource],features.index(s.metric)
                values[i,j,k]=np.sign(p.value)*np.log1p(abs(p.value));mask[i,j,k]=1
    x=torch.tensor((values-np.array(state['mean'],dtype=np.float32))/np.array(state['scale'],dtype=np.float32)*mask)
    m=torch.tensor(mask);adj=torch.tensor(state['graph'],dtype=torch.float32)
    model=MeasuredGraphAutoencoder();model.load_state_dict(state['state_dict']);model.eval()
    with torch.no_grad():
        residual=(model(x[:-1],m[:-1],adj)-x[1:]).square()*m[1:]
        targets=m[1:].sum((0,2));scores=residual.sum((0,2))/targets.clamp_min(1)
    ranking=sorted([n for n in nodes if targets[ni[n]]>0],key=lambda n:(-float(scores[ni[n]]),n))
    return {'status':'evaluated','variant':variant,'source_checksum':case.collection,'as_of':as_of,
        'ranking':ranking,'scores':[{'resource':n,'next_step_mse':float(scores[ni[n]])} for n in ranking],
        'training_end':state['train_end'],'validation_end':state['validation_end'],
        'model_role':'Measured next-step residual service ranking; not causal probability.',
        'explanation':[{'resource':n,'feature':f,'squared_error':float(residual[:,ni[n],k].sum())} for n in ranking[:3] for k,f in enumerate(features) if m[1:,ni[n],k].sum()],
        'training_scope':'Independent per-recording prefix. No claimed transfer to Bank of Anthos.',
        'topology':'Recorded training-prefix parent-child edges, symmetrized for this model.'}
