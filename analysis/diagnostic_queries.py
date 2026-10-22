"""Deterministic, cost-bounded evidence selection, never an infrastructure action."""
FAMILIES={
 'demand_exceeds_capacity':('request_rate','queue_depth','worker_count','capacity_rps','cpu_per_request','retry_rate','cpu_percent'),
 'expensive_execution':('cpu_per_request','request_rate','worker_count','retry_rate','cpu_percent'),
 'reduced_capacity':('worker_count','cpu_limit','throttling','request_rate','queue_depth'),
 'retry_storm':('retry_rate','timeouts','external_request_rate','request_rate','queue_depth'),
 'garbage_collection':('memory_percent','gc_pause_ms','request_rate','latency_ms'),
 'blocking_transaction':('db_latency_ms','lock_wait_ms','blocked_sessions','transaction_age_seconds'),
}
COST={'request_rate':1,'queue_depth':1,'worker_count':1,'capacity_rps':2,'cpu_per_request':2,
      'retry_rate':1,'throttling':1,'cpu_limit':1,'external_request_rate':1,
      'timeouts':1,'memory_percent':1,'gc_pause_ms':2,'transaction_age_seconds':3,
      'db_latency_ms':1,'lock_wait_ms':2,'blocked_sessions':1,'cpu_percent':1,'latency_ms':1}

def choose_next(available,examined,hypotheses,remaining_budget):
    """Select a real available series that distinguishes unresolved hypotheses.

    Utility is an explicit coverage heuristic, not estimated information gain.
    Cost units count measured-column inspections, not money or API billing.
    """
    choices=[]
    for metric in sorted(set(available)-set(examined)):
        affected=[h for h in hypotheses if metric in FAMILIES[h]]
        cost=COST.get(metric,1)
        if affected and cost<=remaining_budget:
            choices.append({'metric':metric,'cost':cost,'utility':len(affected)/cost,
                'distinguishes':affected,'reason':'Distinguishes '+', '.join(h.replace('_',' ') for h in affected)})
    return sorted(choices,key=lambda q:(-q['utility'],q['cost'],q['metric']))[:1]
