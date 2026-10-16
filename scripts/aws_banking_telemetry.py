"""Explicit AWS banking telemetry command. No application startup publication."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common.config import get_settings
from aws.banking_publisher import run_publisher, safe_error
from aws.banking_cloudwatch import collect

def main():
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--publish', action='store_true')
    mode.add_argument('--read', action='store_true')
    parser.add_argument('--confirm-publish', action='store_true')
    parser.add_argument('--database', type=Path, default=ROOT/'results/runtime/banking/telemetry.db')
    parser.add_argument('--checkpoint', type=Path, default=ROOT/'results/runtime/aws-banking-checkpoint.db')
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--lookback-minutes', type=int, default=1440)
    parser.add_argument('--region', default=settings.aws_region)
    args = parser.parse_args()
    if args.publish and not args.confirm_publish:
        parser.error('--publish requires --confirm-publish (bounded custom metric charges may apply)')
    try:
        if args.read:
            result = collect(args.region, settings.profile, args.lookback_minutes)
        else:
            result = run_publisher(args.database, args.checkpoint, args.region, profile=settings.profile, publish=args.publish, limit=args.limit)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result['status'] in ('dry_run', 'published', 'no_new_requests', 'observations_available') else 2
    except Exception as exc:
        print(json.dumps({'status': 'blocked', 'error_code': safe_error(exc)})); return 2

if __name__ == '__main__':
    raise SystemExit(main())
