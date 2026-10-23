"""Read-only, reproducible investigation of executed banking measurements.

Intervention names and model labels are deliberately not diagnostic inputs.
This is a transparent rules-based banking replay, not a trained banking GNN.
"""
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'results/aws_workload/replay'


def load_evidence(folder=EVIDENCE):
    manifest = json.loads((folder / 'manifest.json').read_text())
    contents = {}
    for name, checksum in manifest['files'].items():
        data = (folder / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != checksum:
            raise ValueError('The retained evidence failed its integrity check.')
        contents[name] = data
    return contents, manifest


def percentile(values, fraction=.95):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)] if ordered else None


def quota(snapshot, service='ledgerwriter'):
    try:
        amount, period = snapshot['cgroups'][service]['cpu.max'].split()
        return None if amount == 'max' else int(amount) / int(period)
    except (KeyError, ValueError, TypeError):
        return None


def summarize(rows, start, end):
    requests = [r for r in rows if r.get('instrument') == 'payment_request'
                and start <= r['timestamp'] < end and r.get('completed_at', float('inf')) <= end]
    snapshots = [r for r in rows if r.get('instrument') == 'periodic_snapshot'
                 and start <= r['timestamp'] and r['timestamp'] + r.get('collection_elapsed_ms', 0)/1000 <= end]
    latencies = [r['latency_ms'] for r in requests if isinstance(r.get('latency_ms'), (int, float))]
    limits = [q for r in snapshots if (q := quota(r)) is not None]
    waits = [float(w.get('lock_wait_ms') or 0) for r in snapshots for w in r.get('postgres_lock_waits', [])]
    blocked = [sum(bool(a.get('blocking_pids')) for a in r.get('postgres_activity', [])) for r in snapshots]
    # Arrival rate counts actual recorded starts, independently of completion time.
    start_events = any(r.get('instrument') == 'payment_start' and r['timestamp'] < end for r in rows)
    arrival_instrument = 'payment_start' if start_events else 'payment_request'
    arrivals = sum(r.get('instrument') == arrival_instrument and start <= r['timestamp'] < end for r in rows)
    return dict(start=start, end=end, requests=len(requests), snapshots=len(snapshots),
                p95_ms=percentile(latencies), median_ms=statistics.median(latencies) if latencies else None,
                arrival_rps=arrivals/(end-start), cpu_limit_cores=min(limits) if limits else None,
                lock_wait_ms=max(waits, default=0), blocked_sessions=max(blocked, default=0),
                transport_errors=sum(r.get('http_status') is None for r in requests))


def diagnose(observed, baseline):
    """Only measured signatures; absent instruments cannot establish a driver."""
    if observed['requests'] < 10 or not baseline.get('p95_ms') or observed['p95_ms'] is None:
        return 'insufficient'
    if observed['p95_ms'] <= baseline['p95_ms'] * 3:
        return 'normal'
    candidates = []
    if observed['cpu_limit_cores'] is not None and baseline['cpu_limit_cores'] is not None and observed['cpu_limit_cores'] < baseline['cpu_limit_cores'] * .5:
        candidates.append('capacity')
    if observed['lock_wait_ms'] > 1000 and observed['blocked_sessions'] > 0:
        candidates.append('database')
    if observed['arrival_rps'] > baseline['arrival_rps'] * 1.8:
        candidates.append('traffic')
    return candidates[0] if len(candidates) == 1 else 'unresolved'


TEXT = {
 'capacity': ('Payments slowed while processing capacity fell', 'Payment-writing service',
  'The service was allowed to use much less processor time, so payments took longer to finish.',
  'The recorded processor allowance fell from {base_cpu:g} to {cpu:g} CPU cores. This supports a capacity restriction. The measurements do not explain who changed it or why.',
  'Restore the previous processor allowance, then check payment speed and reconcile balances before declaring recovery.',
  'Keep minimum capacity settings under review and test configuration changes before applying them.'),
 'database': ('Payments waited for the database', 'Transaction database',
  'Database sessions were blocked while payments were slow.',
  'A database lock prevented other sessions from proceeding. The recording contains both waiting sessions and their lock waits. The transaction owner and business reason require further investigation.',
  'Identify the blocking transaction and its owner. Allow it to finish, or have an authorized operator cancel it safely; then check balances and payment speed.',
  'Keep transactions short and monitor long-running transactions and lock waits.'),
 'traffic': ('More payment requests arrived and responses slowed', 'Payment processing path',
  'The recorded arrival rate increased while payment response times rose.',
  'Higher demand is a supported contributor. The recording does not measure admission queues or enough per-request work to prove the exact internal bottleneck.',
  'Control the incoming rate or add verified capacity, then measure payment speed and check that transfers appear once in the ledger.',
  'Load-test expected peaks and define safe traffic limits using measured capacity.'),
 'unresolved': ('Payments slowed; the deeper cause is unresolved', 'Payment processing path',
  'Response times rose beyond the earlier reference.',
  'The available measurements do not distinguish one cause. Slow payments alone do not prove a database, processor or network fault.',
  'Collect queue depth, backend request traces and per-request processing measurements before choosing a corrective action.',
  'Improve coverage of the missing measurements.'),
}


def run_replay(folder=EVIDENCE):
    files, manifest = load_evidence(folder)
    rows = [json.loads(line) for line in files['measurements.jsonl'].splitlines()]
    summary = json.loads(files['summary.json'])
    requests = [r for r in rows if r.get('instrument') == 'payment_request']
    context = manifest['execution_context']
    ledger = json.loads(files['ledger-after.json'])
    ledger_counts = Counter(t['amount'] for t in ledger if t['from_acct'] == context['sender_account'] and t['to_acct'] == context['recipient_account'] and t['from_route'] == context['local_routing_number'] and t['to_route'] == context['local_routing_number'])
    amounts = [r['amount_cents'] for r in requests]
    if len(set(amounts)) != len(amounts) or len({r['operation_uuid'] for r in requests}) != len(requests):
        raise ValueError('Unique request-to-ledger matching is not established.')
    ledger_matches = sum(ledger_counts[amount] == 1 for amount in amounts)
    ledger_integrity = ledger_matches == len(requests)
    start, end = summary['started_at'], summary['ended_at']
    baseline = summarize(rows, start, start + 60)
    incidents = []
    windows = []
    # Fixed 30-second windows, first 60 seconds reserved for reference only.
    for offset in range(60, int(end-start)-29, 30):
        measured = summarize(rows, start+offset, start+offset+30)
        kind = diagnose(measured, baseline)
        windows.append(dict(measured, finding=kind))
        if kind not in TEXT or any(i['category'] == kind for i in incidents):
            continue
        title, location, mechanism, why, action, prevention = TEXT[kind]
        later = [summarize(rows, start+t, start+t+30) for t in range(offset+30, int(end-start)-29, 30)]
        speed_returned = any(w['requests'] >= 10 and w['p95_ms'] is not None and w['p95_ms'] <= baseline['p95_ms']*1.5 for w in later)
        incidents.append(dict(id=kind, category=kind, title=title, location=location,
            what=f"The 95th-percentile recorded request duration was {measured['p95_ms']/1000:.2f} seconds, compared with {baseline['p95_ms']/1000:.2f} seconds in the reference window. Durations include timed-out requests; they are not all successful payment response times.",
            mechanism=mechanism, deeper_cause=why.format(base_cpu=baseline.get('cpu_limit_cores') or 0, cpu=measured.get('cpu_limit_cores') or 0),
            confidence='Supported by recorded measurements; not exclusive causal proof',
            recommendation=action, prevention=prevention, measurements=measured,
            recovery=('Later windows returned close to the earlier payment speed. This does not by itself prove balance correctness or a permanent fix.' if speed_returned else 'Later payment-speed recovery is not established by the available windows.'),
            origin='Automatic measured-signature replay', status='Recorded incident'))
    probe = json.loads(files['commit-order-probe.json'])
    final = json.loads(files['balance-history-reconciliation.json'])
    gap = probe['after_earlier_id_commit']['difference_cents']
    clean_before = probe['before_probe']['difference_cents'] == 0
    reproduced = clean_before and probe['held_process_exit'] == 0 and gap == probe['observed_skipped_earlier_amount_cents'] and gap != 0
    after_probe = probe['after_earlier_id_commit']['timestamp']
    final_ok = final.get('checked_at', 0) > after_probe and len(final.get('accounts', [])) >= 2 and all(a['balance_matches'] and a['history_unique_ids'] and a['api_balance_cents'] == a['ledger_expected_balance_cents'] for a in final['accounts'])
    receipts = [json.loads(v) for n,v in files.items() if n.startswith('recovery-transfer-')]
    transfers_ok = len(receipts) >= 3 and len({r['transaction_id'] for r in receipts}) == len(receipts) and all(r['status']=='verified' and r['ledger_new_records']==1 and r['history_record_found'] and any(q['path']=='/payment' and q['start_time_unix_ns']/1e9 > after_probe for q in r.get('requests', [])) for r in receipts)
    performance_ok = len(final.get('observations', [])) >= 3 and all(o['http_status']==200 and o['timestamp'] > after_probe for o in final['observations']) and final['blocked_database_sessions']==0
    recovery_ok = final_ok and transfers_ok and performance_ok and ledger_integrity
    if reproduced:
        incidents.append(dict(id='balance',category='integrity',title='The displayed balance missed a committed transfer',location='Balance-reading service',
            what=f'The controlled test produced a {gap}-cent difference between the displayed balance and the ledger.',
            mechanism='A transfer with a higher number became visible before an earlier transfer finished.',
            deeper_cause='The balance updater remembers the highest transaction number it has seen. If that transfer finishes first, an earlier-numbered transfer that finishes later can be skipped. The controlled test reproduced a missed transfer; it does not prove that every earlier balance difference had this cause.',
            confidence='Reproduced in an investigator-assisted controlled test',origin='Investigator-assisted test; arithmetic verified automatically',status='Temporary recovery verified' if recovery_ok else 'Recovery not verified',
            recommendation='Rebuild the displayed balances from the ledger and compare both accounts with their recorded transfers. This temporary recovery action was completed in the isolated demo.',
            prevention='Change the updater so it processes every completed transfer, even when transfers finish out of number order. Test reversed completion order, restarts and repeated delivery before releasing the fix.',
            recovery='After resynchronization, both account balances matched the ledger, three new transfers each appeared once in the ledger and history, and three balance reads succeeded with no blocked database sessions. A permanent application fix has not been implemented.' if recovery_ok else 'The recorded checks do not establish recovery.',
            measurements={'missed_cents':gap}, permanent_fix_verified=False))
    return dict(status='completed', source='Executed AWS Bank of Anthos', mode='Read-only replay of retained measurements',
        execution_id=summary['execution_id'], evidence_sha256=manifest['archive_sha256'], baseline=baseline,
        incidents=incidents, windows=windows, submitted_requests=len(requests),
        ledger_matches=ledger_matches, ledger_integrity_verified=ledger_integrity, recovery_verified=recovery_ok,
        model_status='Transparent measured-signature rules. No banking-domain GNN is validated; separate RE2 model results remain in Research & Validation.',
        limitations=['The reference is the first 60 seconds; alert threshold is three times its 95th-percentile response time. This is a demo rule, not a calibrated production SLO.',
          'One executed workload; no independent banking test-set accuracy or novel-method advantage is established.',
          'Payment acknowledgement flags were excluded because the original collector parsed them incorrectly. Ledger matching does not establish what each caller saw.',
          'Backend and SQL traces, admission queue depth and per-request processor attribution are missing.',
          'Diagnostic evidence is separated from intervention labels. Findings use only measurements available by each window end. Final recovery uses separately identified later evidence.'])


def readable_report(result):
    lines = ['# Banking investigation report', '', result['mode'], '', f"{result['submitted_requests']:,} submitted requests; {result['ledger_matches']:,} matching ledger records.", '']
    for item in result['incidents']:
        lines += ['## '+item['title'], '', 'What happened: '+item['what'], '', 'Where: '+item['location'], '', 'Why: '+item['mechanism'], '', 'Deeper explanation: '+item['deeper_cause'], '', 'Action: '+item['recommendation'], '', 'Prevention: '+item['prevention'], '', 'Recovery: '+item['recovery'], '', 'Evidence status: '+item['confidence'], '']
    lines += ['## Limits', '', *['- '+x for x in result['limitations']], '', result['model_status']]
    return '\n'.join(lines)
