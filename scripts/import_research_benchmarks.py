"""Download deterministic, pinned official subsets. No telemetry generation."""
from pathlib import Path
import sys,json,hashlib,urllib.request,time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dataset.benchmarks import ROOT,digest

def fetch(url,path=None):
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'ExplainableAI-University-Research'})
            with urllib.request.urlopen(req,timeout=45) as response:data=response.read(20_000_000)
            if len(data)>=20_000_000:raise ValueError('File exceeds selected-subset size limit')
            if path:
                path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
                if path.exists() and path.read_bytes()!=data:raise ValueError('Refusing to overwrite different raw observations')
                if not path.exists():path.write_bytes(data)
            return data
        except Exception:
            if attempt==2:raise
            time.sleep(attempt+1)

def split(group):
    bucket=int(hashlib.sha256(group.encode()).hexdigest()[:8],16)%10
    return 'train' if bucket<6 else 'validation' if bucket<8 else 'test'

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    if (ROOT/'manifest.json').exists():
        existing=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
        for entry in existing['cases']:
            if digest(ROOT/entry['file'])!=entry['sha256']:raise ValueError('Existing raw checksum mismatch; no data overwritten')
        print('Pinned dataset already imported; all case checksums verified, raw files preserved.');return
    tree=json.loads(fetch('https://api.github.com/repos/microsoft/cloud-monitoring-dataset/git/trees/master?recursive=1'))
    ms_revision=tree['sha']
    hf=json.loads(fetch('https://huggingface.co/api/datasets/phamquiluan/RCAEval'))
    hf_revision=hf['sha']
    fetch(f'https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/{hf_revision}/cases.parquet',ROOT/'rcaeval/cases.parquet')
    fetch(f'https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/{hf_revision}/README.md',ROOT/'rcaeval/README.md')
    fetch(f'https://raw.githubusercontent.com/microsoft/cloud-monitoring-dataset/{ms_revision}/LICENSE',ROOT/'microsoft/LICENSE')
    fetch(f'https://raw.githubusercontent.com/microsoft/cloud-monitoring-dataset/{ms_revision}/README.md',ROOT/'microsoft/README.md')
    import pyarrow.parquet as pq
    index=pq.read_table(ROOT/'rcaeval/cases.parquet').to_pylist()
    selected=[]
    # First two lexicographic services in each RE1 system, every available fault
    # and repetition. Whole service/fault groups share a split. No score-based selection.
    for system in sorted({r['system'] for r in index if str(r['suite']).lower()=='re1'}):
        rows=[r for r in index if str(r['suite']).lower()=='re1' and r['system']==system]
        services=sorted({r['root_cause_service'] for r in rows})[:2]
        selected.extend(r for r in rows if r['root_cause_service'] in services)
    groups=sorted({f"{r['system']}:{r['root_cause_service']}:{r['fault']}" for r in selected},key=lambda g:hashlib.sha256(g.encode()).hexdigest())
    split_map={g:'train' if i<int(.6*len(groups)) else 'validation' if i<int(.8*len(groups)) else 'test' for i,g in enumerate(groups)}
    cases=[];jobs=[]
    for row in tree['tree']:
        name=row['path']
        if not name.endswith('.csv'):continue
        cid=hashlib.sha256(('microsoft/'+name).encode()).hexdigest()[:20]
        target='microsoft/'+name
        cases.append({'id':cid,'source':'microsoft','display_name':name.removeprefix('data/'),'file':target,'metric':name.split('/')[1],'group':name.split('/')[1],'split':'chronological_60_20_20','ground_truth_available':True})
        for suffix in ('','-metadata.json'):
            jobs.append((f'https://raw.githubusercontent.com/microsoft/cloud-monitoring-dataset/{ms_revision}/{name}{suffix}',ROOT/(target+suffix)))
    for row in selected:
        name=row['case'];cid=hashlib.sha256(('rcaeval/'+name).encode()).hexdigest()[:20]
        group=f"{row['system']}:{row['root_cause_service']}:{row['fault']}"
        cases.append({'id':cid,'source':'rcaeval','display_name':name,'file':'rcaeval/'+name+'/metrics.parquet','metric':'multivariate','group':group,'split':split_map[group],'system':row['system'],'ground_truth_available':True})
        for file in ('metrics.parquet','inject_time.txt'):
            jobs.append((f'https://huggingface.co/datasets/phamquiluan/RCAEval/resolve/{hf_revision}/{name}/{file}',ROOT/'rcaeval'/name/file))
        target=ROOT/'labels'/f'{cid}.json';target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps({'root_cause_service':row['root_cause_service'],'fault':row['fault'],'inject_time':int(row['inject_time']),'system':row['system'],'group':group}),encoding='utf-8')
    with ThreadPoolExecutor(max_workers=6) as pool:
        for i,_ in enumerate(pool.map(lambda job:fetch(*job),jobs),1):
            if i%50==0:print(f'Downloaded {i}/{len(jobs)} files',flush=True)
    for entry in cases:
        entry['sha256']=digest(ROOT/entry['file'])
        if entry['source']=='rcaeval':
            actual=int((ROOT/entry['file']).with_name('inject_time.txt').read_text().strip())
            truth=json.loads((ROOT/'labels'/f"{entry['id']}.json").read_text())
            if actual!=truth['inject_time']:raise ValueError('Official index and fault timestamp disagree')
    out={'microsoft_revision':ms_revision,'rcaeval_revision':hf_revision,'selection':'All 60 official Microsoft CSV series; first two lexicographic RE1 root services per system, all 5 faults and 5 repetitions. Group hashing prevents repeated fault settings crossing splits. No performance-based selection.','cases':cases}
    (ROOT/'manifest.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps({'microsoft_series':sum(c['source']=='microsoft' for c in cases),'rcaeval_cases':sum(c['source']=='rcaeval' for c in cases),'microsoft_revision':ms_revision,'rcaeval_revision':hf_revision},indent=2))

if __name__=='__main__':main()
