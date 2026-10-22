"""Normalize business measurements emitted by executed workload instrumentation."""
METRICS={
 'transactions_per_minute':'count/minute','successful_transfers':'count','failed_transfers':'count',
 'active_requests':'count','request_rate':'requests/second','external_request_rate':'requests/second',
 'latency_ms':'milliseconds','processing_ms':'milliseconds','queue_wait_ms':'milliseconds','queue_depth':'count',
 'cpu_percent':'percent','memory_percent':'percent','throttling':'seconds/second','worker_count':'count',
 'cpu_limit':'cores','capacity_rps':'requests/second','cpu_per_request':'cpu_seconds/request',
 'db_latency_ms':'milliseconds','active_connections':'count','lock_wait_ms':'milliseconds',
 'blocked_sessions':'count','transaction_age_seconds':'seconds','timeouts':'count','retry_rate':'attempts/request',
 'gc_pause_ms':'milliseconds','network_latency':'milliseconds','duplicate_processing':'count',
 'unreconciled_transactions':'count',
}

def check_metric(name,unit,value):
    import math
    if name not in METRICS or METRICS[name]!=unit:raise ValueError('Unsupported metric definition or unit')
    if value is not None and (not math.isfinite(value) or value<0 or (unit=='percent' and value>100)):
        raise ValueError('Invalid measured value')
    return value
