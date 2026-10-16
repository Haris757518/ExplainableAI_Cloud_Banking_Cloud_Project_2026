"""Evidence-constrained diagnosis over measured series, separate from synthetic GNNs."""
from __future__ import annotations

import math
from statistics import median
from common.schema import (AnalysisResult, AffectedNode, RootCause, Explanation,
                           FeatureImportance, CFAOResult, TelemetryPolicy)


def deviation(points, min_history=5):
    valid = [p for p in points if isinstance(p.get('value'), (int, float)) and math.isfinite(p['value'])]
    valid.sort(key=lambda p: p.get('timestamp_ms', 0))
    if len(valid) < min_history + 1:
        return None
    # Strictly earlier observations form the reference; the last point is held out.
    history = [p['value'] for p in valid[:-1]]
    center = median(history)
    mad = median(abs(v - center) for v in history)
    scale = max(1.4826 * mad, abs(center) * 0.05, 1e-6)
    z = max(0., (valid[-1]['value'] - center) / scale)
    return {'latest': valid[-1]['value'], 'reference_median': center, 'reference_mad': mad,
            'robust_z': z, 'history_count': len(history), 'timestamp_ms': valid[-1].get('timestamp_ms')}


def analyze_observed(sample, *, period_seconds=60):
    series = sample.metadata.get('series', {})
    evidence = []
    eligible = 0
    for node in sample.nodes:
        for metric, points in series.get(node.id, {}).items():
            # CPU/latency/queue rises are interpretable; a free-memory or free-space
            # rise is not degradation. Keep those raw series without reversing claims.
            if metric not in {'latency_ms', 'db_latency_ms', 'db_connection_ms', 'db_roundtrip_ms', 'write_latency_ms', 'server_latency_ms', 'cpu_percent', 'disk_queue_depth', 'db_connections'}:
                continue
            d = deviation(points)
            if d is None:
                continue
            eligible += 1
            evidence.append({'node': node.id, 'metric': metric, **d})
    evidence.sort(key=lambda x: x['robust_z'], reverse=True)
    anomalous = [e for e in evidence if e['robust_z'] >= 3.5]
    top_z = evidence[0]['robust_z'] if evidence else None
    score = (1 - math.exp(-top_z / 6)) if top_z is not None else None
    node_scores = {}
    roots = []
    for item in anomalous:
        node_scores[item['node']] = max(node_scores.get(item['node'], 0), 1 - math.exp(-item['robust_z'] / 6))
    for node, node_score in sorted(node_scores.items(), key=lambda pair: pair[1], reverse=True)[:5]:
        support = [e for e in anomalous if e['node'] == node]
        roots.append(RootCause(node=node, score=node_score, reason='Observed deviation candidate; causal confirmation requires further evidence.',
                              evidence=[f"{e['metric']}: {e['latest']:.4g}; earlier median {e['reference_median']:.4g}; robust z={e['robust_z']:.2f}" for e in support],
                              path_classification='OBSERVED_DEPENDENCY' if node in sample.transaction.path else 'RESOURCE_EVIDENCE'))
    frontier = {r.node for r in roots}
    # One-hop observed dependencies form the frontier, bounded by the recorded graph.
    for edge in sample.edges:
        if edge.source in node_scores or edge.target in node_scores:
            frontier.update((edge.source, edge.target))
    state = 'insufficient_evidence' if not eligible else 'deviation_detected' if anomalous else 'no_deviation_in_observed_metrics'
    reason = ('At least six aligned observations per resource and metric are required. Missing measurements are unknown.' if not eligible else
              'Only observed metrics were compared with their own earlier median/MAD. Scores measure relative deviation, not failure probabilities. Root causes remain hypotheses.')
    questions = []
    if any(e['metric'] in ('db_latency_ms', 'disk_queue_depth') for e in anomalous):
        questions += ['Collect database wait events and blocking sessions to distinguish query execution, lock contention, CPU pressure, and storage waits.']
    if any(e['metric'] == 'db_connection_ms' for e in anomalous):
        questions += ['Database connection time deviated: compare connection admission/authentication with the separately measured query time before blaming query execution.']
    if any(e['metric'] == 'db_roundtrip_ms' for e in anomalous):
        questions += ['Database round-trip time deviated: compare the connection and query segments, then inspect server waits. Round-trip timing also includes client/transaction overhead.']
    if any(e['metric'] == 'latency_ms' for e in anomalous):
        questions += ['Compare caller duration with server duration and application spans to distinguish processing from transport or queueing.']
    if not questions:
        questions = ['Collect longer aligned resource and application series before assigning a database or network cause.']
    observed_metrics = {metric for point in sample.telemetry for metric in point.observed_metrics}
    gaps = []
    if 'latency_ms' not in observed_metrics:
        gaps.append('Application end-to-end request latency is not measured by this collection.')
    if 'db_latency_ms' not in observed_metrics:
        gaps.append('Database latency is not observed. Do not infer a database fault from CPU or network metrics.')
    if not any(n.type in ('rds', 'database') for n in sample.nodes):
        gaps.append('No database resource is represented in this collection.')
    if sample.source == 'aws_cloudwatch' and not sample.edges:
        gaps.append('AWS application dependencies are not configured or observed.')
    features = [FeatureImportance(feature=f"{e['node']}:{e['metric']}", importance=e['robust_z']) for e in evidence[:8]]
    all_count, focused_count = len(sample.nodes), len(frontier)
    return AnalysisResult(
        anomaly_score=score, is_anomaly=bool(anomalous) if eligible else None,
        affected_nodes=[AffectedNode(node=n, score=s) for n, s in sorted(node_scores.items(), key=lambda x: x[1], reverse=True)],
        root_causes=roots, explanation=Explanation(important_features=features, important_nodes=[], dependency_path=sample.transaction.path, narrative=reason),
        cfao=CFAOResult(causal_frontier=sorted(frontier), trigger=state,
            telemetry_policy=TelemetryPolicy(resolution_seconds={n.id: period_seconds for n in sample.nodes}, baseline_resolution_seconds=period_seconds,
                focused_resolution_seconds=period_seconds, estimated_high_resolution_reduction_percent=0),
            refinement={'status': 'proposed_evidence_requests', 'questions': questions,
                        'selected_resources': focused_count, 'available_resources': all_count,
                        'proposed_query_reduction_percent': round(100 * (1 - focused_count / all_count), 2) if all_count and focused_count else None,
                        'measured_savings': None, 'sampling_changed': False}),
        source=sample.source, scenario='UNLABELED', transaction=sample.transaction, graph=sample,
        model_version='observed-median-mad-v1',
        assessment={'status': state, 'method': 'chronological median/MAD holdout', 'eligible_metric_series': eligible,
                    'ground_truth_available': False, 'score_kind': 'relative_deviation', 'causal_confirmation': False,
                    'evidence': evidence, 'next_evidence': questions, 'measurement_gaps': gaps,
                    'gnn_used': False, 'gnn_reason': 'Existing GNN checkpoints were trained on synthetic data and are excluded from observed-data inference.'})
