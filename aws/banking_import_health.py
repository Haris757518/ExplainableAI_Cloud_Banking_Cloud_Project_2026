from datetime import datetime, timezone
from dataset.real_banking.store import DATA, write_json

def publish(success, client=None):
    if client is None:
        from aws.banking_dataset_store import aws_client
        client=aws_client('cloudwatch')
    now=datetime.now(timezone.utc)
    response=client.put_metric_data(Namespace='PublicBankDataset/ImportHealth',MetricData=[
        {'MetricName':'ImportSuccess','Value':int(success),'Unit':'Count','Timestamp':now},
        {'MetricName':'ImportFailure','Value':int(not success),'Unit':'Count','Timestamp':now}])
    status=response.get('ResponseMetadata',{}).get('HTTPStatusCode')
    if status!=200: raise ValueError('CloudWatch did not acknowledge the health write')
    receipt={'status':'write_acknowledged','timestamp':now.isoformat(),'import_success':success,
             'namespace':'PublicBankDataset/ImportHealth','readback_verified':False}
    write_json(DATA/'cloudwatch.json',receipt)
    return receipt
