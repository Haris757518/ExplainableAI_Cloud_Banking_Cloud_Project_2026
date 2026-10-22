from unittest.mock import Mock
import pytest
from aws import banking_dataset_store as store
from aws.banking_import_health import publish

def test_missing_bucket_does_not_claim_success(monkeypatch):
    monkeypatch.delenv('BANKING_DATASET_BUCKET',raising=False)
    monkeypatch.setattr(store,'configuration',lambda:'')
    with pytest.raises(ValueError,match='not configured'): store.upload({})

def test_s3_requires_readback_verification(tmp_path,monkeypatch):
    monkeypatch.setenv('BANKING_DATASET_BUCKET','test-only-bucket')
    monkeypatch.setattr(store,'ROOT',tmp_path); monkeypatch.setattr(store,'DATA',tmp_path/'receipts')
    (tmp_path/'raw.html').write_text('source'); (tmp_path/'data.csv').write_text('value\n1')
    client=Mock(); client.head_object.return_value={'Metadata':{},'ContentLength':6}
    manifest={'bank':'fixture','snapshot':'raw.html','normalized_csv':'data.csv','snapshot_sha256':'x'}
    with pytest.raises(ValueError,match='verification'): store.upload(manifest,client)
    assert not (tmp_path/'receipts/fixture-aws.json').exists()

def test_cloudwatch_publishes_current_health_only(monkeypatch,tmp_path):
    import aws.banking_import_health as h
    monkeypatch.setattr(h,'DATA',tmp_path)
    client=Mock(); client.put_metric_data.return_value={'ResponseMetadata':{'HTTPStatusCode':200}}
    result=publish(True,client)
    metrics=client.put_metric_data.call_args.kwargs['MetricData']
    assert {m['MetricName'] for m in metrics}=={'ImportSuccess','ImportFailure'}
    assert result['readback_verified'] is False
