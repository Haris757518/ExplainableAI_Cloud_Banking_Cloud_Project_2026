"""Strict official-data import. Labels are read only by explicit evaluation calls."""
import csv, hashlib, json, math
from pathlib import Path
from datetime import datetime
from functools import lru_cache
from statistics import median
from common.research import DataSource,TelemetryCase,TelemetrySeries,TelemetryObservation,DependencyEdge

ROOT=Path(__file__).resolve().parents[1]/'dataset/raw/research'

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def manifest(root=ROOT):
    path=Path(root)/'manifest.json'
    if not path.exists():return {'cases':[],'status':'not_imported'}
    return json.loads(path.read_text(encoding='utf-8'))

def safe_file(root, relative):
    root=Path(root).resolve(); path=(root/relative).resolve()
    if not path.is_relative_to(root):raise ValueError('Source path outside dataset root')
    return path

def finite(value):
    if value is None or value=='':return None
    try:v=float(value)
    except (TypeError,ValueError):raise ValueError('Invalid numeric observation')
    return v if math.isfinite(v) else None

def parse_microsoft(path):
    values=[]; labels=[]; naive=False
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if set(reader.fieldnames or [])!={'TimeStamp','Value','Label'}:raise ValueError('Unsupported Microsoft CSV schema')
        for source_index,row in enumerate(reader):
            dt=datetime.fromisoformat(row['TimeStamp'].replace('Z','+00:00'))
            naive |= dt.tzinfo is None
            # An unspecified timezone is kept as a source-local coordinate, never
            # represented as verified UTC. Integer calendar arithmetic is stable.
            ts=(dt-datetime(1970,1,1)).total_seconds() if dt.tzinfo is None else dt.timestamp()
            if row['Label'] not in ('0','1'):raise ValueError('Invalid official anomaly label')
            values.append(TelemetryObservation(timestamp=ts,value=finite(row['Value']),source_rows=[source_index]))
            labels.append(int(row['Label']))
    # The published files contain identical duplicate rows. Keep their raw row
    # indices and unchanged label, but do not count them as extra time/history.
    grouped={}
    for point,label in zip(values,labels):
        if point.timestamp in grouped:
            previous,old_label=grouped[point.timestamp]
            if previous.value!=point.value:
                previous.value=None;previous.quality='conflicting_source_measurements'
            if old_label!=label:grouped[point.timestamp]=(previous,None)
            previous.source_rows.extend(point.source_rows)
        else:grouped[point.timestamp]=(point,label)
    ordered=[grouped[t] for t in sorted(grouped)]
    values=[p for p,_ in ordered];labels=[label for _,label in ordered]
    return values,labels,'source_local_time_timezone_unspecified' if naive else 'unix_seconds'

def period(observations):
    intervals=[b.timestamp-a.timestamp for a,b in zip(observations,observations[1:]) if b.timestamp>a.timestamp]
    return median(intervals) if intervals else None

@lru_cache(maxsize=2)
def load_case(case_id, root_string=str(ROOT)):
    root=Path(root_string); info=manifest(root)
    entry=next((r for r in info['cases'] if r['id']==case_id),None)
    if entry is None:
        from dataset.re2 import load_re2
        return load_re2(case_id)
    path=safe_file(root,entry['file'])
    if digest(path)!=entry['sha256']:raise ValueError('Raw benchmark checksum mismatch')
    if entry['source']=='microsoft':
        obs,_,kind=parse_microsoft(path)
        series=[TelemetrySeries(id='metric',resource='recorded-series',metric=entry['metric'],original_metric='Value',timestamp_kind=kind,period_seconds=period(obs),observations=obs)]
        source=DataSource(id='microsoft',kind='expert_labelled_series',reference='https://github.com/microsoft/cloud-monitoring-dataset',revision=info['microsoft_revision'])
        edges=[]
    else:
        import pyarrow.parquet as pq
        table=pq.read_table(path).to_pydict()
        times=table.pop('time',None)
        if times is None or any(b<=a for a,b in zip(times,times[1:])):raise ValueError('RCAEval timestamps must be strictly increasing')
        series=[]
        for name,values in table.items():
            resource,metric=name.rsplit('_',1) if '_' in name else (name,'unspecified')
            obs=[TelemetryObservation(timestamp=float(t),value=finite(v),quality='missing' if finite(v) is None else 'observed') for t,v in zip(times,values)]
            series.append(TelemetrySeries(id=name,resource=resource,metric=metric,original_metric=name,period_seconds=period([p for p in obs if p.value is not None]),observations=obs))
        source=DataSource(id='rcaeval',kind='recorded_controlled_benchmark',reference='https://huggingface.co/datasets/phamquiluan/RCAEval',revision=info['rcaeval_revision'])
        edges=[]
    # Only opaque identifiers, metric values and source provenance reach inference.
    # Original case names, fault type, injected service and injection time stay out.
    return TelemetryCase(id=case_id,source=source,collection=entry['sha256'],series=series,edges=edges,provenance={'sha256':entry['sha256'],'split':entry['split'],'recording_end':max(s.observations[-1].timestamp for s in series),'topology':'unavailable' if not edges else 'recorded','original_units':'Unspecified metric units are preserved as unknown; no assumed ms/percent conversions.'})

def labels_for_evaluation(case_id,root=ROOT):
    entry=next((r for r in manifest(root)['cases'] if r['id']==case_id),None)
    if entry is None:
        from dataset.re2 import truth_re2
        return truth_re2(case_id)
    if entry['source']=='microsoft':
        return {'point_labels':parse_microsoft(safe_file(root,entry['file']))[1],'label_source':'Official Microsoft CSV Label column'}
    truth=json.loads(safe_file(root,'labels/'+case_id+'.json').read_text())
    import pyarrow.parquet as pq
    official=next(r for r in pq.read_table(safe_file(root,'rcaeval/cases.parquet')).to_pylist() if r['case']==entry['display_name'])
    for key in ('root_cause_service','fault','inject_time','system'):
        if truth[key]!=official[key]:raise ValueError('Derived annotation differs from the original official case index')
    original_time=int(safe_file(root,entry['file']).with_name('inject_time.txt').read_text(encoding='utf-8').strip())
    if original_time!=truth['inject_time']:raise ValueError('Original fault timestamp differs from the official index')
    return {**truth,'label_source':'Official RCAEval case index and inject_time.txt; recorded controlled fault'}

def catalog(root=ROOT):
    rows=[{k:v for k,v in e.items() if k not in ('file','sha256')} for e in manifest(root)['cases']]
    if root==ROOT:
        from dataset.re2 import entries
        rows.extend({k:e[k] for k in ('id','source','display_name','system','split')} for e in entries()['cases'])
    return rows
