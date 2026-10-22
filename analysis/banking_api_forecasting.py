"""Train-only forecasting rules evaluated on the same chronological test dates."""
from statistics import mean, median

def evaluate(rows):
    series=sorted([r for r in rows if r['value'] is not None],key=lambda r:r['date'])
    if len(series)<30: return {'status':'insufficient_history'}
    if len({(r['bank'],r['service'],r['metric']) for r in series})!=1:
        raise ValueError('Forecast evaluation requires exactly one series')
    a,b=int(len(series)*.6),int(len(series)*.8)
    train=[r['value'] for r in series[:a]]
    test=series[b:]; predictions=[]
    for i,r in enumerate(test,b):
        # Earlier measured observations only, including preceding test observations.
        predictions.append({'date':r['date'],'actual':r['value'],
            'training_median':median(train),'persistence':series[i-1]['value']})
    return {'status':'evaluated','target':'next recorded observation; calendar gaps are not filled',
        'test_start':test[0]['date'],'test_end':test[-1]['date'],'test_count':len(test),
        'methods':{method:{'mae':mean(abs(p['actual']-p[method]) for p in predictions),
            'mse':mean((p['actual']-p[method])**2 for p in predictions)} for method in ['training_median','persistence']},
        'predictions':predictions,'next_observation_forecast':series[-1]['value'],
        'method':'persistence reference; no claimed GNN advantage'}
