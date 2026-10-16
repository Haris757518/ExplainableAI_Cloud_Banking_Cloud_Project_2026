from pathlib import Path
import sys,json,argparse,time,platform
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis.benchmark_evaluation import microsoft,rcaeval

def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=['microsoft','rcaeval','all'],default='all');p.add_argument('--out',required=True);args=p.parse_args()
    out=Path(args.out)
    if out.exists():raise SystemExit('Choose a new output directory; historical results are immutable.')
    out.mkdir(parents=True);started=time.perf_counter();started_at=datetime.now(timezone.utc).isoformat()
    for name,function in [('microsoft',microsoft),('rcaeval',rcaeval)]:
        if args.dataset not in ('all',name):continue
        result=function();(out/(name+'.json')).write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
        print(name,json.dumps(result.get('methods',result.get('splits',{})).get('test',result.get('methods',{})),default=str)[:2500],flush=True)
    (out/'run.json').write_text(json.dumps({'started_at':started_at,'completed_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-started,'python':platform.python_version(),'hardware':platform.processor(),'labels_used_for':'Microsoft validation-only threshold selection and held-out scoring; RCA labels accessed after predictions only','synthetic_telemetry_used':False},indent=2),encoding='utf-8')

if __name__=='__main__':main()
