"""Versioned grouped mechanism study; annotations read after feature construction."""
from pathlib import Path
import sys,json,hashlib,argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from dataset.benchmarks import manifest,load_case,labels_for_evaluation
from analysis.incident_engine import analyze_case

CLASSES=['cpu','mem','disk','delay','loss']
def feature(incident):
    # No resource ID, case ID, fault name or injection time is a predictor.
    vector=[]
    for metric in ('cpu','mem','latency','load','diskio','network_latency','packet_loss'):
        rows=[e for e in incident.evidence if e.metric.lower()==metric]
        for resource in [incident.candidates[0].resource if incident.candidates else None,None]:
            selected=[e for e in rows if resource is None or e.resource==resource]
            vector.extend([np.log1p(min(1000,max((e.score for e in selected),default=0))),sum(e.persistence>=2 and e.score>=3.5 for e in selected)/max(1,len(selected))])
    return vector

def metrics(rows,key):
    matrix={a:{b:0 for b in CLASSES+['unknown']} for a in CLASSES}
    for row in rows:matrix[row['truth']][row[key]]+=1
    f1=[]
    for c in CLASSES:
        tp=matrix[c][c];fp=sum(matrix[x][c] for x in CLASSES if x!=c);fn=sum(matrix[c][x] for x in CLASSES+['unknown'] if x!=c)
        f1.append(2*tp/max(1,2*tp+fp+fn))
    n=max(1,len(rows));return {'cases':len(rows),'accuracy':sum(r[key]==r['truth'] for r in rows)/n,'macro_f1':sum(f1)/5,'coverage':sum(r[key]!='unknown' for r in rows)/n,'abstention_rate':sum(r[key]=='unknown' for r in rows)/n,'joint_service_mechanism_accuracy':sum(r['top1'] and r[key]==r['truth'] for r in rows)/n,'root_service_top1':sum(r['top1'] for r in rows)/n,'root_service_top3':sum(r['top3'] for r in rows)/n,'confusion_matrix':matrix}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);args=parser.parse_args();out=Path(args.out)
    if out.exists():raise SystemExit('Choose a new output directory; old experiments are immutable.')
    out.mkdir(parents=True);rows=[]
    for entry in [e for e in manifest()['cases'] if e['source']=='rcaeval']:
        case=load_case(entry['id']);start=min(p.timestamp for s in case.series for p in s.observations);end=case.provenance['recording_end'];checkpoint=min(end,start+(end-start)/2+120)
        incident=analyze_case(case,checkpoint,forecast_enabled=False);features=feature(incident)
        mechanism=incident.explanation['diagnosis']['mechanism'];rule={'cpu_pressure':'cpu','memory_pressure':'mem','disk_degradation':'disk','network_delay':'delay','packet_loss':'loss'}.get(mechanism,'unknown')
        truth=labels_for_evaluation(entry['id']) # after prediction
        order=[c.resource for c in incident.candidates]
        rows.append({'case_id':case.id,'group':entry['group'],'published_split':entry['split'],'features':features,'truth':truth['fault'],'rule':rule,'top1':bool(order and order[0]==truth['root_cause_service']),'top3':truth['root_cause_service'] in order[:3],'checkpoint':checkpoint,'raw_sha256':entry['sha256']})
    # Six service/system groups per fault; all five repetitions stay together.
    assignment={}
    for fault in CLASSES:
        groups=sorted({r['group'] for r in rows if r['truth']==fault},key=lambda g:hashlib.sha256(('mechanism-v4:'+g).encode()).hexdigest())
        for i,group in enumerate(groups):assignment[group]='train' if i<4 else 'validation' if i==4 else 'test'
    for row in rows:row['split']=assignment[row['group']]
    train=[r for r in rows if r['split']=='train'];validation=[r for r in rows if r['split']=='validation']
    x=np.asarray([r['features'] for r in train]);mean=x.mean(0);scale=np.maximum(x.std(0),.1)
    centroids=np.asarray([np.mean([(np.asarray(r['features'])-mean)/scale for r in train if r['truth']==c],axis=0) for c in CLASSES])
    def prediction(row,margin):
        d=np.linalg.norm(centroids-(np.asarray(row['features'])-mean)/scale,axis=1);order=np.argsort(d)
        relative=(d[order[1]]-d[order[0]])/max(d[order[1]],1e-9)
        return CLASSES[int(order[0])] if relative>=margin else 'unknown'
    choices=[]
    for margin in (0,.1,.2,.3,.4):
        for row in validation:row['classifier']=prediction(row,margin)
        choices.append((metrics(validation,'classifier')['macro_f1'],margin))
    _,margin=max(choices,key=lambda pair:(pair[0],pair[1]))
    for row in rows:row['classifier']=prediction(row,margin)
    model={'version':'nearest-centroid-signature-v4','classes':CLASSES,'mean':mean.tolist(),'scale':scale.tolist(),'centroids':centroids.tolist(),'abstention_margin':margin,'features':'CPU, memory, latency, load, diskio, network latency, packet loss: leading-resource and whole-recording-prefix max log-deviation / persistent fraction','training_case_ids':[r['case_id'] for r in train],'note':'Experimental injected-label classifier; not an independently verified mechanism. Not used for dashboard mechanism claims.'}
    report={'protocol':'New fault-stratified system/service/fault group split: 100 train,25 validation,25 test; repetitions never cross partitions. Published V3 split unchanged. Recording midpoint+120s; frozen early baseline.','methods':{split:{method:metrics([r for r in rows if r['split']==split],key) for method,key in [('evidence_rules','rule'),('nearest_centroid','classifier')]} for split in ('train','validation','test')},'published_split_rules':metrics([r for r in rows if r['published_split']=='test'],'rule'),'cases':rows,'limitations':['Same systems and service identities may occur across groups; no cross-system generalization claim.','RE1 lacks direct disk I/O, network delay and packet-loss measurements. Classifier predicts injected annotations from correlated signatures, never verifies a physical mechanism.','Known-incident fixed checkpoint, not end-to-end detection accuracy; V3 pre-injection false alarms remain.','Only 25 cases (five service/fault groups) in the new test set; repetitions are dependent.']}
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8');(out/'model.json').write_text(json.dumps(model,indent=2),encoding='utf-8');print(json.dumps(report['methods']['test']))
if __name__=='__main__':main()
