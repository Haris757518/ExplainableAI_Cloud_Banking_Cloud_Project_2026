"""Operator-reviewed responses based on the deepest supported hypothesis."""
ACTIONS={
 'demand_exceeds_capacity':('Review worker availability, admission limits and autoscaling decisions.',
     'If confirmed, increase processing capacity within an approved budget or apply bounded admission control.'),
 'expensive_execution':('Profile the affected request path and compare CPU time per completed transaction.',
     'Review the expensive code path before proposing a measured optimization or rollback.'),
 'reduced_capacity':('Compare worker counts, CPU limits, deployment changes and measured throttling.',
     'Consider restoring the previously approved capacity only after operator review.'),
 'retry_storm':('Inspect retry amplification, timeout settings and idempotency keys.',
     'Consider bounded retries with backoff and admission control after validating payment state.'),
 'garbage_collection':('Inspect GC pauses, heap pressure and workload-correlated allocation.',
     'Profile allocation and retention before proposing a heap or application change.'),
 'blocking_transaction':('Inspect the measured blocking session and transaction age.',
     'An operator should review transaction impact before resolving a blocker.'),
 'cpu_pressure':('Collect request rate, queues, active workers, CPU limits and per-request CPU.',
     'Defer scaling or code changes until the underlying driver is distinguished.'),
 'database_pressure':('Compare query time, active connections and lock waits.',
     'Defer database changes until blocking, admission or execution overhead is supported.'),
 'unknown':('Collect the next discriminating measurements listed in the investigation.',
     'Do not change infrastructure or replay payments based on an unexplained deviation.'),
}

def recommend(reason):
    inspect,action=ACTIONS.get(reason,ACTIONS['unknown'])
    return {'diagnostic_step':inspect,'suggested_action':action,'automatic_execution':False,
        'banking_safety':'Check pending transaction state, duplicate processing, ledger reconciliation and balances before and after an approved change.',
        'verify':['Compare subsequent latency and queue measurements with the frozen baseline.',
                  'Check successful and failed transfers and required transaction-integrity checks.'],
        'approval':'An operator must authorize any corrective action separately.'}
