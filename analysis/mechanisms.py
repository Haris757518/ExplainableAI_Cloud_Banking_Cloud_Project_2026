"""Label-blind, resource-local mechanism hypotheses. Never asserts causality."""
import re

# Presence of a latency column is deliberately insufficient for these hypotheses.
RULES = {
 'application_processing_delay': (('server_latency_ms','processing_ms','application_processing_ms','self_time_ms'), 'paired caller/server spans and dependency timing', 'Compare measured application processing with dependency and network timing.', 'Optimize application work only after isolating measured execution overhead.', 'Application processing and caller timing return toward reference.'),
 'cpu_pressure': (('cpu','cpu_percent','cpuutilization'), 'workload, process CPU, throttling and documented capacity', 'Compare process CPU with request demand and throttling.', 'Consider capacity or workload changes if sustained saturation is independently established.', 'CPU and request timing return toward their earlier references.'),
 'memory_pressure': (('mem','memory','memory_percent'), 'capacity limits, allocation and workload trend', 'Inspect memory growth, allocation, garbage collection and capacity limits.', 'Change allocation or capacity only after confirming sustained pressure.', 'Memory pressure and dependent request timing decline.'),
 'disk_degradation': (('disk_latency','diskio','io_wait','disk_queue'), 'storage latency, queue depth and demand', 'Compare storage timing, queues and I/O demand.', 'Adjust storage or workload only after confirming the bottleneck.', 'Storage latency and queueing return toward reference.'),
 'network_delay': (('network_latency','network_delay','rtt','retransmissions'), 'network spans and retransmission context', 'Compare measured network timing with application spans.', 'Change routing or network capacity only after confirming a network bottleneck.', 'Network timing and retransmissions return toward reference.'),
 'packet_loss': (('packet_loss','packets_dropped','packet_drop_rate'), 'packet counts, direction and capture interval', 'Inspect measured loss and affected network paths.', 'Repair the measured path only after validating sustained packet loss.', 'Direct loss measurements return toward reference.'),
 'database_query_delay': (('db_latency_ms','query_latency','query_duration'), 'query plans, waits and server execution spans', 'Inspect slow query execution and measured wait events.', 'Tune a query only after identifying its measured bottleneck.', 'Query execution and caller latency return toward reference.'),
 'lock_contention': (('blocked_sessions','lock_waits','lock_wait_ms'), 'blocking transaction identities and matching query timing', 'Inspect blocking sessions and long-running transactions.', 'Resolve a blocking transaction only after operator review of its impact.', 'Blocking sessions clear and query timing improves.'),
 'connection_delay': (('db_connection_ms','connection_latency','connection_acquisition_ms'), 'pool occupancy, admission, authentication and network timing', 'Compare connection establishment with query and admission timing.', 'Change connection handling only after isolating the delay.', 'Connection acquisition time returns toward reference.'),
 'pool_exhaustion': (('pool_waiters','pool_wait_ms'), 'measured active connections and configured pool limit', 'Compare pool waiters with measured occupancy and the actual limit.', 'Change pool limits only after confirming capacity and connection behaviour.', 'Waiters clear and acquisition timing improves.'),
 'request_overload': (('request_rate','load','workload','requests_per_second'), 'capacity, concurrency, queues and resource pressure', 'Compare incoming demand with queues, concurrency and resource pressure.', 'Apply backpressure or scale only if demand exceeds measured capacity.', 'Queues and request timing improve under measured demand.'),
 'service_failures': (('errors','error','error_rate','timeouts','http_5xx'), 'error responses, logs and matching execution traces', 'Inspect measured failures and correlated execution logs.', 'Mitigate the confirmed failure after identifying its origin.', 'Error rate and caller timing return toward reference.'),
}

def matching(metric, names):
    value=metric.lower()
    return value in names or any(value.endswith('_'+n) for n in names)

def diagnose(incident):
    """Only supplied chronological evidence is inspected; no case names or labels."""
    if not incident.candidates:
        return {'resource':None,'mechanism':'unknown','status':'insufficient_evidence','hypotheses':[], 'symptom':None,'verified':False,'next_check':'Collect sufficient chronological measurements.'}
    resource=incident.candidates[0].resource
    threshold=incident.explanation.get('detector_threshold',3.5)
    required=incident.explanation.get('required_persistence',2)
    local=[e for e in incident.evidence if e.resource==resource]
    abnormal=lambda e:e.score>=threshold and e.persistence>=required
    hypotheses=[]
    for name,(names,missing,action,mitigation,verification) in RULES.items():
        measured=[e for e in local if matching(e.metric,names)]
        supports=[e.model_dump() for e in measured if abnormal(e)]
        contradicts=[e.model_dump() for e in measured if not abnormal(e)]
        # Demand alone does not establish overload; pool waits alone do not establish exhaustion.
        additional=True
        if name=='request_overload':
            additional=any(abnormal(e) and matching(e.metric,('cpu','cpu_percent','queue_depth','concurrency')) for e in local)
        if name=='pool_exhaustion':
            used=next((e for e in local if e.metric=='pool_active'),None)
            limit=next((e for e in local if e.metric=='pool_limit'),None)
            additional=bool(used and limit and limit.value>0 and used.value>=limit.value)
        status='supported_hypothesis' if supports and additional else 'contradicted_by_current_measurements' if contradicts and not supports else 'insufficient_evidence'
        hypotheses.append({'mechanism':name,'status':status,'supporting_evidence':supports,'contradictory_evidence':contradicts,'missing_evidence':missing,'investigation_action':action,'conditional_mitigation':mitigation,'verification_signal':verification,'verified':False})
    # Dependencies must be documented and abnormal at both endpoints; temporal compatibility is exposed.
    edges=incident.graph.get('edges',[])
    dependency=[e for e in edges if e['source']==resource and e['target'] in incident.affected_services]
    if dependency:
        dependency_metrics=[e for e in incident.evidence if e.resource in {edge['target'] for edge in dependency} and abnormal(e)]
        failed=any(matching(e.metric,('errors','error','error_rate','timeouts','http_5xx')) for e in dependency_metrics)
        hypotheses.append({'mechanism':'dependency_failure' if failed else 'dependency_degradation','status':'supported_hypothesis','supporting_evidence':dependency+[e.model_dump() for e in dependency_metrics],'contradictory_evidence':[], 'missing_evidence':'Paired execution spans and independent failure evidence; ordering alone is not causality.','investigation_action':'Inspect the recorded abnormal dependency and compare onset times.','conditional_mitigation':'Mitigate a dependency only after confirming its failure.','verification_signal':'Dependency and caller measurements improve.','verified':False})
    supported=[h for h in hypotheses if h['status']=='supported_hypothesis']
    supported.sort(key=lambda h:-max((e.get('score',0) for e in h['supporting_evidence']),default=0))
    leading=supported[0] if supported else None
    symptoms=[e for e in local if abnormal(e)]
    symptom=max(symptoms,key=lambda e:e.score).model_dump() if symptoms else None
    # Conflicting mechanisms remain visible; no probability or saturation is inferred from a z-score.
    return {'resource':resource,'mechanism':leading['mechanism'] if leading else 'unknown','status':'hypothesis_only' if leading else 'insufficient_evidence','verified':False,'symptom':symptom,'hypotheses':supported+[h for h in hypotheses if h not in supported],'next_check':leading['investigation_action'] if leading else 'Compare service execution, resource pressure and network timing; mechanism-specific measurements are missing.','uncertainty':'Relative deviations support investigation, not verified causality or saturation. '+('Competing hypotheses remain.' if len(supported)>1 else 'Independent mechanism confirmation is unavailable.')}

def mechanism_actions(diagnosis):
    from common.research import RecommendedAction
    supported=[h for h in diagnosis['hypotheses'] if h['status']=='supported_hypothesis'][:3]
    if not supported and diagnosis.get('resource'):
        return [RecommendedAction(category='unknown_mechanism',evidence=['Measured deviation on the leading candidate; no mechanism-specific corroboration.'],mechanism_status='unknown',diagnostic_action=diagnosis['next_check'],proposed_mitigation='Defer operational changes until discriminating evidence is available.',purpose='Distinguish causes from symptoms.',verification_metric='Original abnormal metric and newly collected mechanism evidence')]
    return [RecommendedAction(category=h['mechanism'],evidence=[str(e.get('metric',e.get('relationship','recorded relationship'))) for e in h['supporting_evidence']],mechanism_status='supported hypothesis; not verified',diagnostic_action=h['investigation_action'],proposed_mitigation=h['conditional_mitigation'],purpose='Investigate a measured mechanism signature.',verification_metric=h['verification_signal']) for h in supported]

def resource_labels(resources):
    """Names only from recorded identifiers; opaque identifiers get stable aliases."""
    known={'cartservice':'Cart Service','paymentservice':'Payment Service','recommendationservice':'Recommendation Service','checkoutservice':'Checkout Service','adservice':'Ad Service','frontend':'Frontend','redis':'Redis','postgresql':'PostgreSQL'}
    output={}
    for index,resource in enumerate(sorted(resources)):
        lower=resource.lower()
        if lower in known:label=known[lower]
        elif lower.startswith('ts-') and lower.endswith('-service'):label=resource[3:].replace('-',' ').title()
        elif lower.startswith('i-') and re.fullmatch(r'i-[0-9a-f]+',lower):label=f'EC2 Instance {index+1:02d}'
        elif lower=='recorded-series':label='Recorded Series'
        elif len(resource)<=24 and re.fullmatch(r'[a-zA-Z][a-zA-Z-]+',resource):label=resource.replace('-',' ').title()
        else:label=f'Resource {index+1:02d}'
        output[resource]=label
    return output
