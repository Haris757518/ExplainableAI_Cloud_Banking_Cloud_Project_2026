"""Two additional repetitions-1 RE2-OB services per fault, selected before analysis."""
import sys,json,hashlib
from pathlib import Path
from urllib.request import urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pyarrow.parquet as pq
from dataset.benchmarks import ROOT,manifest,digest
from dataset.re2 import entries
from dataset.real_banking.store import write_json

target=ROOT.parent/'research_probe';target.mkdir(exist_ok=True)
if (target/'manifest.json').exists():raise SystemExit('A completed subset exists; preserve it')
revision=manifest()['rcaeval_revision']
existing={e['display_name'] for e in entries()['cases']}
index=pq.read_table(ROOT/'rcaeval/cases.parquet').to_pylist()
selected=[]
for fault in ('cpu','mem','disk','delay','loss'):
    eligible=sorted([r for r in index if r['dataset']=='RE2-OB' and r['fault']==fault and r['repetition']==1 and r['case'] not in existing],key=lambda r:r['case'])[:2]
    selected.extend(eligible)
completed=[]
for row in selected:
    folder=target/row['case'];folder.mkdir(exist_ok=True);checksums={}
    for name in ['metrics.parquet','traces.parquet','inject_time.txt']:
        path=folder/name
        if not path.exists():
            for attempt in range(3):
                try:
                    with urlopen(f"https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/{revision}/{row['case']}/{name}",timeout=60) as response:
                        partial=path.with_suffix(path.suffix+'.partial')
                        with partial.open('wb') as stream:
                            while block:=response.read(1024*1024):stream.write(block)
                        partial.replace(path)
                    break
                except Exception:
                    if attempt==2:raise
        checksums[name]=digest(path)
    completed.append({'id':hashlib.sha256(('probe:'+row['case']).encode()).hexdigest()[:20],
        'source':'rcaeval','display_name':row['case'],'system':'ob','split':'prespecified_expanded_re2_compatibility',
        'file':row['case']+'/metrics.parquet','sha256':checksums['metrics.parquet'],'checksums':checksums,'truth':row})
    print('Imported',row['case'],flush=True)
write_json(target/'manifest.json',{'revision':revision,'selection':'Two additional lexicographically first RE2-OB repetition-1 services per five infrastructure faults, excluding prior imported cases; selected before analysis. Not representative random sampling.', 'cases':completed})
