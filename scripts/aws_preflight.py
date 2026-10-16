from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.config import get_settings
from aws.discovery import AWSDiscovery
from aws.cloudwatch_adapter import CloudWatchAdapter


def main() -> int:
    settings = get_settings()
    discovery_client = AWSDiscovery(settings.aws_region, settings.profile)
    status = discovery_client.status()
    print(f"AWS_CONNECTED={status['connected']}")
    print(f"AWS_REGION={status['region']}")
    if status.get("account_id"):
        print(f"AWS_ACCOUNT_ID={status['account_id']}")
    if not status["connected"]:
        print(f"AWS_ERROR={status.get('error')}")
        return 2

    discovery = discovery_client.discover()
    print(f"EC2_COUNT={discovery['counts']['ec2']}")
    print(f"RDS_COUNT={discovery['counts']['rds']}")
    ec2_ids = [x["id"] for x in discovery["ec2"]]
    rds_ids = [x["id"] for x in discovery["rds"]]
    if settings.ec2_ids:
        ec2_ids = [x for x in ec2_ids if x in settings.ec2_ids]
    if settings.rds_ids:
        rds_ids = [x for x in rds_ids if x in settings.rds_ids]
    raw = CloudWatchAdapter(
        settings.aws_region,
        max(60, settings.cloudwatch_lookback_minutes),
        settings.cloudwatch_period_seconds,
        settings.profile,
    ).collect(ec2_ids, rds_ids, include_application=settings.collect_application_metrics)
    print(f"CLOUDWATCH_OBSERVED_METRICS={raw['observed_metric_count']}")
    if not ec2_ids and not rds_ids:
        print('PREFLIGHT_OK=false: no configured/discovered resources')
        return 3
    if raw.get('errors') or not raw['observed_metric_count']:
        print('PREFLIGHT_OK=false: telemetry unavailable or incomplete')
        return 4
    print("PREFLIGHT_OK=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
