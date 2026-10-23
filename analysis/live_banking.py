"""Live demonstration detector. Intervention records are never detector inputs."""
import math
from statistics import median


def assess(rows, baseline, *, now):
    def valid(r):
        return all(isinstance(r.get(k), (int, float)) and math.isfinite(r[k]) for k in ('timestamp', 'completed_at', 'latency_ms')) and r['timestamp'] <= r['completed_at'] <= now and r['latency_ms'] >= 0
    observed = [r for r in rows if valid(r)]
    if not observed or now-max(r['completed_at'] for r in observed)>25:
        return {'status':'stale', 'explanation':'Fresh AWS measurements are unavailable. No current health claim is made.'}
    recent = [r for r in observed if r['completed_at'] >= now-30]
    reference = [r['latency_ms'] for r in baseline if valid(r)]
    if len(reference)<30:
        return {'status':'warming_up','explanation':'Collecting at least 30 baseline requests before detecting deviations.'}
    if any(r.get('outcome')!='acknowledged_success' for r in baseline):
        return {'status':'invalid_baseline','explanation':'Baseline requests did not all succeed. Diagnose the deployment before starting a fresh reference.'}
    if len(recent)<5:
        return {'status':'insufficient_data','explanation':'Fewer than five completed requests in the current window.'}
    center=median(reference); mad=median(abs(v-center) for v in reference)
    threshold=max(100, center*3, center+6*mad)
    values=sorted(r['latency_ms'] for r in recent)
    p95=values[min(len(values)-1, math.ceil(.95*len(values))-1)]
    failed=sum(r.get('outcome')!='acknowledged_success' for r in recent)
    anomaly=p95>threshold or failed/len(recent)>.1
    return {'status':'anomaly' if anomaly else 'normal','p95_ms':round(p95,1),
            'threshold_ms':round(threshold,1),'baseline_median_ms':round(center,1),
            'requests':len(recent),'unacknowledged':failed,
            'explanation':('Recent responses exceed the frozen latency threshold or more than 10% lack success acknowledgement.' if anomaly else 'Recent responses are within this demonstration’s frozen reference.'),
            'cause':'Not established by request latency alone. Inspect resource and database evidence.',
            'recovery':'Latency normalization alone does not verify balance or transaction integrity.'}
