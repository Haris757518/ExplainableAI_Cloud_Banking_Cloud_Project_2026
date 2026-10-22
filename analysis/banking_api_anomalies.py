"""Chronological reference and calibration; deviations are unlabelled findings."""
from statistics import median
import hashlib
import json

VERSION='public-bank-mad-v1'

def analyze(rows):
    groups={}
    for row in rows:
        if row['value'] is not None:
            groups.setdefault((row['bank'],row['service'],row['metric']),[]).append(row)
    results=[]
    for key, series in sorted(groups.items()):
        series=sorted(series,key=lambda r:r['date']); n=len(series)
        if n<30:
            results.append({'bank':key[0],'service':key[1],'metric':key[2],'status':'insufficient_history','observations':n}); continue
        a,b=int(n*.6),int(n*.8)
        train=[r['value'] for r in series[:a]]; center=median(train)
        scale=max(1.4826*median(abs(v-center) for v in train),.01)
        def deviation(v):
            return max(0,center-v) if key[2]=='availability' else max(0,v-center)
        scores=sorted(deviation(r['value'])/scale for r in series[a:b])
        threshold=max(3.5,scores[min(len(scores)-1,int(.99*len(scores)))])
        findings=[]; persistence=0; previous=None
        from datetime import date
        for row in series[b:]:
            score=deviation(row['value'])/scale
            if score>threshold:
                persistence=persistence+1 if previous and (date.fromisoformat(row['date'])-date.fromisoformat(previous)).days==1 else 1
                previous=row['date']
                findings.append({'date':row['date'],'observed':row['value'],'reference':center,
                    'deviation':row['value']-center,'score':score,'consecutive_flagged_days':persistence,
                    'evidence':row,'status':'model_flagged_deviation','verified_incident':False,
                    'explanation':f"{key[1]} {key[2]} deviated from its historical reference. Internal infrastructure cause is unknown: public data contains no CPU, database or distributed trace evidence."})
            else: persistence=0; previous=None
        results.append({'bank':key[0],'service':key[1],'metric':key[2],'status':'evaluated',
            'split':{'training':[series[0]['date'],series[a-1]['date']], 'calibration':[series[a]['date'],series[b-1]['date']], 'test':[series[b]['date'],series[-1]['date']]},
            'counts':{'training':a,'calibration':b-a,'test':n-b},'reference':center,'scale':scale,
            'threshold':threshold,'findings':findings,'precision':None,'recall':None,
            'limitations':'No incident labels; flags do not establish banking faults or root causes.'})
    return {'model_version':VERSION,'input_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),
            'configuration':{'training_fraction':.6,'calibration_fraction':.2,'test_fraction':.2,'minimum_score':3.5,'calibration_quantile':.99},'series':results}
