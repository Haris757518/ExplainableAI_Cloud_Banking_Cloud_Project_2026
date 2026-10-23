"""Mechanism evidence refines a symptom rank; no intervention labels are inputs."""
from statistics import median
from analysis.banking_replay import summarize

def localize(rows,*,start,baseline_end,as_of,gnn_ranking=(),budget=8):
    reference=summarize(rows,start,baseline_end)
    recent=summarize(rows,max(baseline_end,as_of-30),as_of)
    queries=[];spent=0
    def inspect(name,cost,value):
        nonlocal spent
        if spent+cost>budget:return None
        spent+=cost;queries.append({'measurement':name,'cost_units':cost,'value':value})
        return value
    def snapshots(left,right):
        return [r for r in rows if r.get('instrument')=='periodic_snapshot' and left<=r['timestamp'] and r['timestamp']+r.get('collection_elapsed_ms',0)/1000<=right]
    baseline=snapshots(start,baseline_end);observed=snapshots(max(baseline_end,as_of-30),as_of)
    def quotas(items):
        result={}
        for item in items:
            for service,data in item.get('cgroups',{}).items():
                try:
                    amount,period=data['cpu.max'].split()
                    if amount!='max':result.setdefault(service,[]).append(int(amount)/int(period))
                except (KeyError,ValueError,TypeError):continue
        return result
    before,after=quotas(baseline),quotas(observed)
    changes={service:{'before_cores':median(values),'after_cores':min(after[service])} for service,values in before.items() if service in after and min(after[service])<median(values)*.5}
    symptom=reference['p95_ms'] is not None and recent['p95_ms'] is not None and recent['requests']>=10 and recent['p95_ms']>3*reference['p95_ms']
    if not symptom:return {'status':'no_sustained_slowdown' if recent['requests']>=10 else 'insufficient_evidence','roots':[],
                           'gnn_symptom_ranking':list(gnn_ranking),'queries':[],'effort_units':0,'as_of':as_of,'causal_confirmation':False}
    roots=[]
    capacity=inspect('measured_cpu_allowance_changes',1,changes)
    rate=inspect('actual_arrival_rate',1,{'before_rps':reference['arrival_rps'],'after_rps':recent['arrival_rps']})
    if capacity and rate and abs(rate['after_rps']-rate['before_rps'])<=max(.5,.2*rate['before_rps']):
        for service,change in capacity.items():
            roots.append({'resource':service,'mechanism':'reduced_processing_capacity','evidence':change,
                          'explanation':'Processing allowance fell while incoming demand stayed close to its reference.'})
    wait=inspect('observed_database_lock_wait_ms',2,recent['lock_wait_ms'] if observed else None)
    if wait is not None and wait>1000:
        blocked=inspect('observed_blocked_database_sessions',1,recent['blocked_sessions'])
        if blocked:
            roots.append({'resource':'ledger-db','mechanism':'blocking_database_transaction','evidence':{'lock_wait_ms':wait,'blocked_sessions':blocked},
                          'explanation':'Measured PostgreSQL sessions were blocked behind database locks.'})
    if not roots and rate and rate['after_rps']>1.8*rate['before_rps']:
        roots.append({'resource':'incoming payment demand','mechanism':'increased_demand_contributor','evidence':rate,
                      'explanation':'Incoming demand rose; an exclusive internal bottleneck is not established.'})
    return {'status':'supported_contributor' if len(roots)==1 else 'multiple_supported_contributors' if roots else 'deeper_cause_unresolved',
            'roots':roots,'gnn_symptom_ranking':list(gnn_ranking),'queries':queries,'effort_units':spent,
            'as_of':as_of,'causal_confirmation':False,
            'limitations':['Direct signatures support contributors, not who changed configuration or every competing cause.',
                           'Cost units count recorded measurement groups inspected, not money, live API requests or information gain.',
                           'GNN symptom ranks are retained unchanged; measured mechanism evidence can nominate a different cause.']}
