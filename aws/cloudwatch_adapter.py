from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

EC2_METRICS = {
    "CPUUtilization": "cpu_percent",
    "NetworkIn": "network_in_bytes",
    "NetworkOut": "network_out_bytes",
}
RDS_METRICS = {
    "CPUUtilization": "cpu_percent",
    "DatabaseConnections": "db_connections",
    "ReadLatency": "read_latency_s",
    "WriteLatency": "write_latency_s",
    "ReadIOPS": "read_iops",
    "WriteIOPS": "write_iops",
    "FreeStorageSpace": "free_storage_bytes",
}

class CloudWatchAdapter:
    def __init__(self, region: str, lookback_minutes: int = 15, period_seconds: int = 60):
        self.region = region
        self.lookback_minutes = lookback_minutes
        self.period_seconds = period_seconds
        self.client = boto3.client("cloudwatch", region_name=region)

    def _latest(self, namespace: str, metric_name: str, dimensions: list[dict[str, str]]) -> float | None:
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=self.lookback_minutes)
        response = self.client.get_metric_statistics(
            Namespace=namespace, MetricName=metric_name, Dimensions=dimensions,
            StartTime=start, EndTime=end, Period=self.period_seconds, Statistics=["Average"]
        )
        points = response.get("Datapoints", [])
        if not points: return None
        points.sort(key=lambda x: x["Timestamp"])
        return float(points[-1]["Average"])

    def collect_ec2(self, instance_id: str) -> dict[str, Any]:
        out={"node_id": instance_id, "source":"aws_cloudwatch", "metrics":{}, "error":None}
        try:
            dims=[{"Name":"InstanceId","Value":instance_id}]
            for metric, target in EC2_METRICS.items():
                out["metrics"][target]=self._latest("AWS/EC2", metric, dims)
        except (BotoCoreError, ClientError, NoCredentialsError) as exc:
            out["error"]=str(exc)
        return out

    def collect_rds(self, db_instance_id: str) -> dict[str, Any]:
        out={"node_id": db_instance_id, "source":"aws_cloudwatch", "metrics":{}, "error":None}
        try:
            dims=[{"Name":"DBInstanceIdentifier","Value":db_instance_id}]
            for metric, target in RDS_METRICS.items():
                out["metrics"][target]=self._latest("AWS/RDS", metric, dims)
        except (BotoCoreError, ClientError, NoCredentialsError) as exc:
            out["error"]=str(exc)
        return out

    def collect(self, ec2_ids: list[str], rds_ids: list[str]) -> dict[str, Any]:
        return {
            "region": self.region,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ec2": [self.collect_ec2(i) for i in ec2_ids],
            "rds": [self.collect_rds(i) for i in rds_ids],
        }
