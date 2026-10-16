"""Reproducible real-trace import, temporal diagnosis and chronological GNN study."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dataset.alibaba_adapter import build_snapshot
from analysis.observed import analyze_observed
from ai_models.observed_gnn import train_observed


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',default='dataset/raw/alibaba')
    parser.add_argument('--max-rows',type=int,default=100000)
    parser.add_argument('--window-ms',type=int,default=5000)
    parser.add_argument('--out',default='results/observed')
    parser.add_argument('--epochs',type=int,default=100)
    args=parser.parse_args()
    started=time.perf_counter()
    snapshot=build_snapshot(args.root,max_rows=args.max_rows,window_ms=args.window_ms)
    sample=snapshot.to_analysis_sample()
    diagnosis=analyze_observed(sample,period_seconds=max(1,args.window_ms//1000))
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    (out/'analysis.json').write_text(diagnosis.model_dump_json(indent=2),encoding='utf-8')
    gnn=train_observed(sample,out/'observed_gnn.pt',epochs=args.epochs)
    archive=Path(snapshot.metadata['raw_sources']['callgraph'])
    digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
    report={'source':snapshot.source,'archive_sha256':digest,'archive_bytes':archive.stat().st_size,
            'rows_scanned':snapshot.metadata['rows_scanned'],'bounded_prefix':snapshot.metadata['bounded_prefix'],
            'nodes':len(snapshot.nodes),'edges':len(snapshot.edges),'measured_calls':snapshot.metadata['measured_calls'],
            'diagnosis':diagnosis.assessment,'gnn':gnn,'elapsed_seconds':round(time.perf_counter()-started,3),
            'synthetic_measurements_used':False,'accuracy_claims':None}
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('diagnosis','gnn')},indent=2))
    print('GNN held-out measured-target MSE:',gnn['test_masked_mse'])


if __name__=='__main__':
    main()
