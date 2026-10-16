"""Self-supervised graph reconstruction trained exclusively on measured series."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from torch import nn

FEATURES = ['latency_ms', 'server_latency_ms', 'db_latency_ms', 'cpu_percent']


class MeasuredGraphAutoencoder(nn.Module):
    def __init__(self, width=16):
        super().__init__()
        self.encoder = nn.Linear(len(FEATURES)*2, width)
        self.decoder = nn.Linear(width, len(FEATURES))

    def forward(self, values, mask, adjacency):
        encoded = torch.relu(self.encoder(torch.cat([values, mask], dim=-1)))
        return self.decoder(adjacency @ encoded)


def train_observed(sample, output, *, epochs=100, seed=42):
    if sample.source not in {'alibaba_trace', 'alibaba', 'aws_cloudwatch'}:
        raise ValueError('Training requires observed dataset or AWS series.')
    series = sample.metadata.get('series', {})
    nodes = [n.id for n in sample.nodes]
    times = sorted({p['timestamp_ms'] for metrics in series.values() for feature, points in metrics.items() if feature in FEATURES for p in points})
    if len(times) < 20:
        raise ValueError('At least 20 chronological windows are needed; use --window-ms 5000 for the Alibaba training slice.')
    indexes, time_indexes = {n:i for i,n in enumerate(nodes)}, {t:i for i,t in enumerate(times)}
    values = np.zeros((len(times), len(nodes), len(FEATURES)), dtype=np.float32)
    mask = np.zeros_like(values)
    for node, metrics in series.items():
        if node not in indexes:
            continue
        for feature, points in metrics.items():
            if feature not in FEATURES:
                continue
            for p in points:
                i,j,k = time_indexes[p['timestamp_ms']], indexes[node], FEATURES.index(feature)
                values[i,j,k] = np.log1p(p['value'])
                mask[i,j,k] = 1
    train_end, val_end = int(len(times)*0.6), int(len(times)*0.8)
    means, scales = [], []
    for k in range(len(FEATURES)):
        observed = values[:train_end,:,k][mask[:train_end,:,k].astype(bool)]
        means.append(float(observed.mean()) if observed.size else 0.)
        scales.append(max(float(observed.std()), 0.1) if observed.size else 1.)
    values = ((values-np.asarray(means))/np.asarray(scales))*mask
    x, m = torch.tensor(values, dtype=torch.float32), torch.tensor(mask)
    adjacency = torch.eye(len(nodes))
    for edge in sample.edges:
        if edge.source in indexes and edge.target in indexes:
            i,j = indexes[edge.source], indexes[edge.target]
            adjacency[i,j] = adjacency[j,i] = 1
    adjacency = adjacency / adjacency.sum(dim=1, keepdim=True)
    torch.manual_seed(seed)
    model = MeasuredGraphAutoencoder()
    optimizer = torch.optim.Adam(model.parameters(), lr=.01)
    def loss(a,b,msk):
        return (((a-b)**2)*msk).sum()/msk.sum().clamp_min(1)
    if any(not m[a:b].sum() for a,b in [(0,train_end),(train_end,val_end),(val_end,len(times))]):
        raise ValueError('A chronological partition contains no observed targets.')
    best, best_loss = None, float('inf')
    for _ in range(epochs):
        model.train(); optimizer.zero_grad()
        loss(model(x[:train_end], m[:train_end], adjacency), x[:train_end], m[:train_end]).backward()
        optimizer.step(); model.eval()
        with torch.no_grad():
            validation = loss(model(x[train_end:val_end], m[train_end:val_end], adjacency), x[train_end:val_end], m[train_end:val_end]).item()
        if validation < best_loss:
            best_loss, best = validation, copy.deepcopy(model.state_dict())
    model.load_state_dict(best)
    with torch.no_grad():
        pred = model(x[val_end:], m[val_end:], adjacency)
        test_mse = loss(pred,x[val_end:],m[val_end:]).item()
        baseline = loss(torch.zeros_like(x[val_end:]),x[val_end:],m[val_end:]).item()
        residual = ((pred-x[val_end:])**2*m[val_end:]).sum(dim=0)
    provenance = hashlib.sha256(json.dumps(series,sort_keys=True).encode()).hexdigest()
    report = {'source':sample.source, 'series_sha256':provenance, 'seed':seed, 'features':FEATURES,
              'windows':len(times), 'train_windows':train_end, 'validation_windows':val_end-train_end,'test_windows':len(times)-val_end,
              'time_boundaries_ms':{'train_end':times[train_end-1],'validation_start':times[train_end],'test_start':times[val_end]},
              'test_observed_targets':int(m[val_end:].sum()), 'validation_mse':best_loss,'test_masked_mse':test_mse,'train_mean_baseline_test_mse':baseline,
              'supervised_accuracy':None,'rca_top1_accuracy':None,'ground_truth_available':False,
              'topology_partitioning':sample.metadata.get('topology_partitioning','Transductive: fixed topology selected from the entire bounded slice; future topology is not held out.'),
              'explanation_kind':'Exact decomposition of reconstruction squared error across measured node features',
              'largest_test_residuals':sorted([{'node':node,'feature':feature,'squared_error_sum':float(residual[i,k])} for i,node in enumerate(nodes) for k,feature in enumerate(FEATURES) if m[val_end:,i,k].sum()], key=lambda row: row['squared_error_sum'],reverse=True)[:10],
              'limitations':'Self-supervised reconstruction is not verified fault detection. Chronological partitions share a bounded topology; no banking or causal labels. Zero internal mask fillers are excluded from loss and are not exported as observations.'}
    output = Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    torch.save({'state_dict':model.state_dict(),'means':means,'scales':scales,'node_ids':nodes,'features':FEATURES,'report':report},output)
    output.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def explain_observed_checkpoint(sample, path='results/observed/observed_gnn.pt'):
    """Apply only the measured-data checkpoint to its exact documented trace slice.

    This is held-out reconstruction evidence, not a cross-domain fault classifier.
    """
    if sample.source not in {'alibaba', 'alibaba_trace', 'alibaba_microservices_v2021'}:
        return {'status':'not_applied','reason':'No validated measured-data checkpoint for this source/domain.'}
    path=Path(path)
    if not path.exists():
        return {'status':'not_applied','reason':'Measured-data checkpoint is unavailable.'}
    series=sample.metadata.get('series',{})
    checksum=hashlib.sha256(json.dumps(series,sort_keys=True).encode()).hexdigest()
    state=torch.load(path,map_location='cpu',weights_only=True)
    if checksum!=state['report']['series_sha256']:
        return {'status':'not_applied','reason':'Trace slice or aggregation differs from the documented model study; retraining and validation are required.'}
    nodes=state['node_ids'];indexes={n:i for i,n in enumerate(nodes)}
    latest=max(p['timestamp_ms'] for metrics in series.values() for feature,points in metrics.items() if feature in FEATURES for p in points)
    if latest<state['report']['time_boundaries_ms']['test_start']:
        return {'status':'not_applied','reason':'Latest window is not in the documented held-out partition.'}
    values=np.zeros((len(nodes),len(FEATURES)),dtype=np.float32);mask=np.zeros_like(values)
    for node,metrics in series.items():
        if node not in indexes:
            continue
        for feature,points in metrics.items():
            if feature not in FEATURES:
                continue
            for p in points:
                if p['timestamp_ms']==latest:
                    values[indexes[node],FEATURES.index(feature)]=np.log1p(p['value'])
                    mask[indexes[node],FEATURES.index(feature)]=1
    x=torch.tensor(((values-np.asarray(state['means']))/np.asarray(state['scales']))*mask,dtype=torch.float32)
    m=torch.tensor(mask)
    if not m.sum():
        return {'status':'not_applied','reason':'No measured targets in the latest held-out window.'}
    adjacency=torch.eye(len(nodes))
    for edge in sample.edges:
        if edge.source in indexes and edge.target in indexes:
            i,j=indexes[edge.source],indexes[edge.target];adjacency[i,j]=adjacency[j,i]=1
    adjacency=adjacency/adjacency.sum(dim=1,keepdim=True)
    model=MeasuredGraphAutoencoder();model.load_state_dict(state['state_dict']);model.eval()
    with torch.no_grad():
        residual=(model(x,m,adjacency)-x).square()*m
    contributions=sorted([{'node':node,'feature':feature,'squared_error':float(residual[i,k])} for i,node in enumerate(nodes) for k,feature in enumerate(FEATURES) if mask[i,k]],key=lambda r:r['squared_error'],reverse=True)
    return {'status':'evaluated','source':'measured-trace graph autoencoder','latest_window_ms':latest,'latest_window_held_out':True,
            'latest_measured_targets':int(m.sum()),'latest_masked_mse':float(residual.sum()/m.sum()),
            'contributions':contributions[:12], 'calibrated_failure_probability':None,
            'interpretation':'Exact measured-feature reconstruction error contributions. Additional model evidence; not causal confirmation or a fault label.'}
