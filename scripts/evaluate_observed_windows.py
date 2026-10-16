"""Unlabelled temporal consistency on disjoint windows of the downloaded trace."""
from pathlib import Path
import sys,json,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dataset.alibaba_adapter import build_snapshot
from analysis.observed import deviation

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);args=parser.parse_args()
    sample=build_snapshot('dataset/raw/alibaba',max_rows=100000,window_ms=5000).to_analysis_sample()
    rows=[]
    for start,end in [(0,100000),(100000,200000),(200000,300000)]:
        results=[]
        for node,metrics in sample.metadata['series'].items():
            for metric,points in metrics.items():
                d=deviation([p for p in points if start<=p['timestamp_ms']<end])
                if d:results.append({'node':node,'metric':metric,**d})
        rows.append({'start_ms_inclusive':start,'end_ms_exclusive':end,'eligible_series':len(results),'relative_deviations':sum(r['robust_z']>=3.5 for r in results),'evidence':results})
    report={'source':'Alibaba downloaded production traces','rows_scanned':sample.metadata['rows_scanned'],'windows':rows,'fault_labels':None,'accuracy':None,'limitations':'Disjoint time windows within one bounded production-trace prefix; shared selected topology. This measures relative-deviation consistency, not independent-dataset generalization or false-positive rate.'}
    out=Path(args.out)
    if out.exists():raise SystemExit('Choose a new output path; existing research artifacts are immutable.')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k!='evidence'} for r in rows],indent=2))

if __name__=='__main__':main()
