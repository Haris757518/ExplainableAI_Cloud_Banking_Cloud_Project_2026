"""Read-only banking cloud panel plus local publication preview."""
import os
from pathlib import Path
import json,time
from fastapi import APIRouter, Query
from common.config import get_settings
from aws.banking_publisher import run_publisher, safe_error
from aws.banking_cloudwatch import collect

router = APIRouter(prefix='/api/aws/banking', tags=['AWS measured banking'])
ROOT = Path(__file__).resolve().parents[1]

@router.get('/preview')
def preview():
    settings = get_settings()
    data = Path(os.environ.get('BANKING_DATA_DIR', ROOT/'results/runtime/banking'))
    try:
        telemetry=Path(os.environ.get('AWS_BANKING_TELEMETRY_DB',data/'telemetry.db'))
        return run_publisher(telemetry, ROOT/'results/runtime/aws-banking-checkpoint.db', settings.aws_region, limit=10)
    except Exception as exc:
        return {'status': 'preview_unavailable', 'error_code': safe_error(exc), 'published_requests': 0}

@router.get('/metrics')
def metrics(lookback_minutes: int = Query(1440, ge=1, le=20160)):
    settings = get_settings()
    return collect(settings.aws_region, settings.profile, lookback_minutes)

@router.get('/demo/latest')
def latest_demo():
    """Saved measured demo evidence only; this route never executes or publishes."""
    from aws.banking_demo import session_dir
    from datetime import datetime
    root=ROOT/'results/runtime/aws-demo'
    try:
        pointer=json.loads((root/'LATEST.json').read_text(encoding='utf-8'))
        report=json.loads((session_dir(root,pointer['session'])/'report.json').read_text(encoding='utf-8'))
        stamp=report.get('verified_at') or (report.get('cloudwatch') or {}).get('collected_at') or report['created_at']
        report['snapshot_age_seconds']=max(0,time.time()-datetime.fromisoformat(stamp).timestamp())
        report['display_scope']='saved measured experiment; not a current fault assertion'
        return report
    except FileNotFoundError:
        return {'status':'not_prepared','source':'local_measured_banking','hosting':'local','period_seconds':10}
    except (ValueError,KeyError,TypeError):
        return {'status':'evidence_unavailable','reason':'Demo evidence could not be validated. No values were substituted.'}
