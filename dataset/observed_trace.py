"""Bounded, streaming import of measured Alibaba call durations. No injections."""
from __future__ import annotations

import csv
import io
import math
import tarfile
from collections import Counter, defaultdict
from pathlib import Path


def rows(path):
    path = Path(path)
    if path.name.endswith(('.tar.gz', '.tgz', '.tar')):
        # Stream mode avoids scanning/decompressing the entire 1.3 GB member first.
        with tarfile.open(path, 'r|*') as archive:
            for member in archive:
                if member.isfile() and member.name.endswith(('.csv', '.tsv', '.txt')):
                    with archive.extractfile(member) as stream:
                        first = stream.readline().decode('utf-8-sig')
                        delimiter = '\t' if '\t' in first else ','
                        reader = csv.DictReader((line.decode('utf-8') for line in stream), fieldnames=next(csv.reader([first], delimiter=delimiter)), delimiter=delimiter)
                        yield from reader
    else:
        with path.open(encoding='utf-8-sig', newline='') as stream:
            first = stream.readline()
            delimiter = '\t' if '\t' in first else ','
            yield from csv.DictReader(stream, fieldnames=next(csv.reader([first], delimiter=delimiter)), delimiter=delimiter)


def measured_snapshot(root, *, trace_id=None, timestamp=None, max_services=40, max_edges=80, max_rows=100000, window_ms=30000, selection_end_ms=None):
    from dataset.alibaba_adapter import AlibabaGraphSnapshot, discover_sources, load_msresource_metrics
    sources = discover_sources(root)
    if sources.callgraph is None:
        raise FileNotFoundError('No Alibaba MSCallGraph archive found. Configure ALIBABA_ROOT.')
    counts = Counter()
    calls = []
    seen = set()
    rejected = 0
    scanned = 0
    for row in rows(sources.callgraph):
        scanned += 1
        if scanned > max_rows:
            break
        row = {str(k).lower(): v for k, v in row.items() if k is not None}
        try:
            ts, duration = int(float(row['timestamp'])), float(row['rt'])
            upstream, downstream = row['um'], row['dm']
            if not math.isfinite(duration) or ts < 0:
                raise ValueError('Invalid observation')
        except (KeyError, ValueError, TypeError):
            rejected += 1
            continue
        if upstream in ('', 'NAN', 'nan', '(?)') or downstream in ('', 'NAN', 'nan', '(?)'):
            rejected += 1
            continue
        if trace_id is not None and row.get('traceid') != trace_id:
            continue
        if timestamp is not None and ts != timestamp:
            continue
        # Keep caller-positive and server-negative observations distinct. Deduplicate
        # only a repeated recording of the same span on the same side.
        rpc = row.get('rpctype', 'unknown').lower()
        side = 'server' if duration < 0 else 'client'
        key = (row.get('traceid'), row.get('rpcid'), upstream, downstream, rpc, side, ts)
        if key in seen:
            continue
        seen.add(key)
        if selection_end_ms is None or ts <= selection_end_ms:
            counts[(upstream, downstream, rpc)] += 1
        calls.append((upstream, downstream, rpc, ts, abs(duration), side))
    if not calls:
        raise ValueError('No usable measured calls in selected trace slice.')
    degree = Counter()
    for (upstream, downstream, _), count in counts.items():
        degree[upstream] += count
        degree[downstream] += count
    selected = set(n for n, _ in degree.most_common(max_services))
    chosen_edges = [(key, count) for key, count in counts.most_common() if key[0] in selected and key[1] in selected][:max_edges]
    included = set(key for key, _ in chosen_edges)
    selected = {n for key in included for n in key[:2]}
    if not selected:
        raise ValueError('Selected slice contains no connected service pairs.')
    bins = defaultdict(list)
    protocols = defaultdict(set)
    for upstream, downstream, rpc, ts, duration, side in calls:
        if (upstream, downstream, rpc) not in included:
            continue
        # Positive duration measures downstream latency from the caller; negative
        # duration measures downstream server processing, per the upstream schema.
        metric = 'server_latency_ms' if side == 'server' else 'latency_ms'
        bins[(downstream, metric, (ts // window_ms) * window_ms)].append(duration)
        if side == 'client' and rpc == 'db':
            bins[(downstream, 'db_latency_ms', (ts // window_ms) * window_ms)].append(duration)
        protocols[downstream].add(rpc)
    series = defaultdict(lambda: defaultdict(list))
    for (node, metric, ts), values in sorted(bins.items()):
        series[node][metric].append({'timestamp_ms': ts, 'value': sum(values) / len(values), 'count': len(values)})
    metric_timestamp = timestamp if timestamp is not None else max(c[3] for c in calls)
    resource_metrics = load_msresource_metrics(sources.msresource, selected, timestamp=metric_timestamp) if sources.msresource else {}
    telemetry = []
    for sid in sorted(selected):
        values = {key: points[-1]['value'] for key, points in series[sid].items() if points and key != 'server_latency_ms'}
        values.update(resource_metrics.get(sid, {}))
        telemetry.append({'node_id': sid, **values, 'observed_metrics': sorted(values)})
    first_ts, last_ts = min(c[3] for c in calls), max(c[3] for c in calls)
    return AlibabaGraphSnapshot(
        source='alibaba_microservices_v2021', trace_id=trace_id, timestamp=last_ts,
        nodes=[{'id': sid, 'label': f'Alibaba {sid[:8]}', 'type': 'database' if 'db' in protocols[sid] else 'cache' if protocols[sid] == {'mc'} else 'microservice', 'layer': 'data' if 'db' in protocols[sid] else 'service'} for sid in sorted(selected)],
        edges=[{'source': key[0], 'target': key[1], 'relationship': 'CALLS', 'communication': key[2], 'weight': count} for key, count in chosen_edges],
        telemetry=telemetry,
        metadata={'timestamp_kind': 'relative_trace_milliseconds', 'time_range_ms': [first_ts, last_ts], 'window_ms': window_ms,
                  'rows_scanned': min(scanned, max_rows), 'row_limit': max_rows, 'bounded_prefix': scanned > max_rows,
                  'topology_selection_end_ms': selection_end_ms, 'invalid_rows': rejected, 'measured_calls': len(calls), 'series': dict(series),
                  'raw_sources': {k: str(v) if v else None for k, v in sources.__dict__.items()},
                  'ground_truth_available': False, 'banking_data': False,
                  'notes': 'Observed call durations; DB type inferred from recorded DB protocol. No failure labels. Relative timestamps are not calendar dates.'})
