"""Bounded, pinned official RE2 recordings; separate V4 manifest, no V3 edits."""
from pathlib import Path
import sys,json,hashlib,urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pyarrow.parquet as pq
from dataset.benchmarks import ROOT,manifest,digest

def main():
    root=ROOT.parent/'research_v4';root.mkdir(exist_ok=True)
    if (root/'manifest.json').exists():raise SystemExit('RE2 manifest exists; preserve it.')
    revision=manifest()['rcaeval_revision'];rows=pq.read_table(ROOT/'rcaeval/cases.parquet').to_pylist();index=[r for r in rows if r['dataset']=='RE2-OB'];services=sorted({r['root_cause_service'] for r in index});entries=[]
    for i,fault in enumerate(('cpu','mem','disk','delay','loss')):
        row=next(r for r in index if r['fault']==fault and r['root_cause_service']==services[i%len(services)] and r['repetition']==1)
        folder=root/row['case'];folder.mkdir(exist_ok=True);checksums={}
        for filename in ('metrics.parquet','traces.parquet','inject_time.txt'):
            path=folder/filename
            if not path.exists():urllib.request.urlretrieve(f"https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/{revision}/{row['case']}/{filename}",path)
            checksums[filename]=digest(path)
        case_id=hashlib.sha256(('v4:'+row['case']).encode()).hexdigest()[:20]
        entries.append({'id':case_id,'source':'rcaeval','display_name':row['case'],'system':'ob','split':'illustrative_re2_graph','file':row['case']+'/metrics.parquet','sha256':checksums['metrics.parquet'],'checksums':checksums,'truth':row})
        print(row['case'],flush=True)
    (root/'manifest.json').write_text(json.dumps({'revision':revision,'selection':'One RE2-OB repetition-1 recording per five published faults, paired with sorted distinct root services; selected before inference. Illustrative cases, not representative aggregate accuracy.','cases':entries},indent=2),encoding='utf-8')
if __name__=='__main__':main()
