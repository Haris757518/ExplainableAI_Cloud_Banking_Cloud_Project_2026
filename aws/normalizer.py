from __future__ import annotations
from datetime import datetime, timezone
from dataset.generator import generate_sample
from common.schema import AnalysisSample

def _none_zero(v, default=0.0):
    return default if v is None else float(v)

def normalize_aws_observations(raw: dict) -> AnalysisSample:
    """Map a CloudWatch collection into the canonical graph schema.

    The mapping uses the first configured EC2 and RDS resources as EC2-01/RDS-01
    in the demonstration graph. Missing optional CloudWatch metrics keep a safe
    baseline value rather than inventing an observation.
    """
    sample = generate_sample("NORMAL", seed=7, index=0)
    sample.scenario = "NORMAL"
    sample.transaction.type = "UPI_PAYMENT"
    now = datetime.now(timezone.utc)
    by_id = {x["node_id"]: x for x in raw.get("ec2", []) + raw.get("rds", [])}
    ec2 = next(iter(raw.get("ec2", [])), None)
    rds = next(iter(raw.get("rds", [])), None)
    for t in sample.telemetry:
        if t.node_id == "ec2-01" and ec2:
            m=ec2.get("metrics",{})
            t.cpu_percent=min(max(_none_zero(m.get("cpu_percent"), t.cpu_percent),0),100)
            t.network_in_mbps=_none_zero(m.get("network_in_bytes"), t.network_in_mbps)/1024/1024/60
            t.network_out_mbps=_none_zero(m.get("network_out_bytes"), t.network_out_mbps)/1024/1024/60
            t.timestamp=now
        elif t.node_id == "rds-01" and rds:
            m=rds.get("metrics",{})
            t.cpu_percent=min(max(_none_zero(m.get("cpu_percent"), t.cpu_percent),0),100)
            read_ms=_none_zero(m.get("read_latency_s"),0.04)*1000
            write_ms=_none_zero(m.get("write_latency_s"),0.04)*1000
            t.db_latency_ms=max(read_ms, write_ms)
            t.latency_ms=max(t.latency_ms,t.db_latency_ms)
            t.disk_io=_none_zero(m.get("read_iops"),0)+_none_zero(m.get("write_iops"),0)
            t.timestamp=now
    return sample
