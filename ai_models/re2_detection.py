"""Normal-prefix calibration for the existing per-recording RE2 GNN."""
import numpy as np
import torch
from ai_models.observed_gnn import MeasuredGraphAutoencoder
from ai_models.re2_inference import checkpoint_path

PROTOCOL={'rolling_points':3,'validation_max_multiplier':1.5,'minimum_validation_targets':5,
          'threshold_data':'Existing normal validation prefix only; not fault checkpoints',
          'scope':'Retrospective calibration audit on the already inspected RE2 collection; no production false-alarm guarantee'}

def calibrated_scores(case):
    state=torch.load(checkpoint_path(case.id,'recorded_graph'),map_location='cpu',weights_only=True)
    if state['raw_sha256']!=case.collection or state['trace_sha256']!=case.provenance.get('trace_sha256'):raise ValueError('Checkpoint provenance mismatch')
    nodes=state['nodes'];features=state['features'];ni={n:i for i,n in enumerate(nodes)}
    times=sorted({p.timestamp for s in case.series if s.resource in ni and s.metric in features for p in s.observations})
    ti={t:i for i,t in enumerate(times)};values=np.zeros((len(times),len(nodes),4),dtype=np.float32);mask=np.zeros_like(values)
    for series in case.series:
        if series.resource not in ni or series.metric not in features:continue
        for p in series.observations:
            if p.value is not None:
                i,j,k=ti[p.timestamp],ni[series.resource],features.index(series.metric)
                values[i,j,k]=np.sign(p.value)*np.log1p(abs(p.value));mask[i,j,k]=1
    x=torch.tensor((values-np.array(state['mean'],dtype=np.float32))/np.array(state['scale'],dtype=np.float32)*mask);m=torch.tensor(mask)
    model=MeasuredGraphAutoencoder();model.load_state_dict(state['state_dict']);model.eval()
    with torch.no_grad():
        errors=((model(x[:-1],m[:-1],torch.tensor(state['graph']))-x[1:]).square()*m[1:]).sum((1,2))/m[1:].sum((1,2)).clamp_min(1)
    points=[{'timestamp':times[i+1],'score':float(np.median(errors[max(0,i-2):i+1].numpy())),'has_targets':bool(m[i+1].sum())} for i in range(len(errors))]
    validation=[p['score'] for p in points if state['train_end']<p['timestamp']<=state['validation_end'] and p['has_targets']]
    if len(validation)<PROTOCOL['minimum_validation_targets']:return {'status':'insufficient_calibration','points':[],'threshold':None}
    threshold=max(validation)*PROTOCOL['validation_max_multiplier']
    return {'status':'calibrated','threshold':threshold,'points':points,'validation_end':state['validation_end'],'validation_targets':len(validation),
            'source_checksum':case.collection,'trace_checksum':state['trace_sha256'],'protocol':PROTOCOL}

def decide(calibration,as_of):
    if calibration.get('status')!='calibrated' or as_of<=calibration['validation_end']:
        return {'status':'insufficient_evidence','score':None,'threshold':None,'reason':'No future calibration is applied before its validation boundary.'}
    eligible=[p for p in calibration.get('points',[]) if p['timestamp']<=as_of and p['timestamp']>calibration['validation_end'] and p['has_targets']]
    if not eligible:return {'status':'insufficient_evidence','score':None,'threshold':calibration.get('threshold')}
    latest=eligible[-1]
    return {'status':'deviation_detected' if latest['score']>calibration['threshold'] else 'no_deviation_in_observed_metrics',
            'score':latest['score'],'threshold':calibration['threshold'],'timestamp':latest['timestamp'],
            'method':'Trailing three-point GNN residual with validation-prefix calibration'}
