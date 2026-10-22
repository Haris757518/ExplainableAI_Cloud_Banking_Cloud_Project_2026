from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import os
import tempfile
import uuid
from urllib.request import urlopen, Request
from .parser import parse
from .schema import SOURCES
from .validate import validate

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'results'/'real_banking'

def write_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=path.parent,suffix='.tmp')
    with os.fdopen(fd,'w',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False)
    os.replace(name,path)

def read_json(path, fallback):
    p=Path(path)
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else fallback

def import_bank(bank, content=None, retrieved_at=None):
    if bank not in SOURCES: raise ValueError('Unsupported bank')
    retrieved_at=retrieved_at or datetime.now(timezone.utc).isoformat()
    if content is None:
        with urlopen(Request(SOURCES[bank],headers={'User-Agent':'PublicBankResearch/1.0'}),timeout=60) as response:
            content=response.read()
    checksum=hashlib.sha256(content).hexdigest()
    previous=read_json(DATA/f'{bank}-current.json',{})
    # Preserve even a rejected snapshot for source-format investigation.
    snapshot=DATA/'raw'/f'{bank}-{checksum}.html'
    snapshot.parent.mkdir(parents=True,exist_ok=True); snapshot.write_bytes(content)
    if bank=='starling':
        from .starling_importer import extract
        rows=extract(content.decode('utf-8'),retrieved_at,checksum)
    else:
        rows=parse(content.decode('utf-8'),bank,retrieved_at,checksum)
    validation=validate(rows)
    rows.sort(key=lambda r:(r['date'],r['service'],r['metric']))
    run=DATA/'imports'/f'{bank}-{uuid.uuid4().hex}'
    run.mkdir(parents=True)
    write_json(run/'observations.json',rows)
    with (run/'observations.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    manifest={'bank':bank,'source_url':SOURCES[bank],'retrieved_at':retrieved_at,
              'snapshot':str(snapshot.relative_to(ROOT)), 'snapshot_sha256':checksum,
              'normalized_sha256':hashlib.sha256((run/'observations.csv').read_bytes()).hexdigest(),
              'normalized_csv':str((run/'observations.csv').relative_to(ROOT)),
              'observations':str((run/'observations.json').relative_to(ROOT)),
              'start_date':rows[0]['date'],'end_date':rows[-1]['date'],
              'reporting_quarters':sorted({r['date'][:4]+'-Q'+str((int(r['date'][5:7])-1)//3+1) for r in rows}),
              'validation':validation,'schema_version':'public-bank-v1',
              'previous_snapshot_sha256':previous.get('snapshot_sha256'),
              'source_changed_since_previous_import':bool(previous and previous.get('snapshot_sha256')!=checksum),
              'limitations':['Aggregated public statistics; internal infrastructure cause unavailable.',
                  'Monzo omitted trailing CBPII daily cells are null.' if bank=='monzo' else 'Quarter dates validated against official embedded report filenames and day counts. Initial server-rendered table disagrees with heading and is excluded. Dedicated and Open Banking field names are retained as distinct series.']}
    write_json(run/'manifest.json',manifest)
    # Readers see either the previous validated import or this complete generation.
    write_json(DATA/f'{bank}-current.json',manifest)
    return manifest

def sources():
    return [{'bank':b,'source_url':u,'manifest':read_json(DATA/f'{b}-current.json',None)} for b,u in SOURCES.items()]

def metrics(bank=None, service=None, metric=None, start=None, end=None):
    rows=[]
    for s in sources():
        if bank and s['bank']!=bank.lower(): continue
        if s['manifest']: rows.extend(read_json(ROOT/s['manifest']['observations'],[]))
    return [r for r in rows if (not service or r['service']==service) and
            (not metric or r['metric']==metric) and (not start or r['date']>=start) and (not end or r['date']<=end)]
