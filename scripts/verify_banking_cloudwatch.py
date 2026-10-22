"""Read back recent importer-health metrics without publishing more values."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import datetime,timedelta,timezone
from dataset.real_banking.store import DATA,read_json,write_json
from aws.banking_dataset_store import aws_client
import json

receipt=read_json(DATA/'cloudwatch.json',{})
if not receipt.get('timestamp'):raise SystemExit('No acknowledged import-health write')
timestamp=datetime.fromisoformat(receipt['timestamp'])
client=aws_client('cloudwatch');observed={}
for metric in ['ImportSuccess','ImportFailure']:
    result=client.get_metric_statistics(Namespace='PublicBankDataset/ImportHealth',MetricName=metric,
        StartTime=timestamp-timedelta(minutes=1),EndTime=datetime.now(timezone.utc)+timedelta(minutes=1),Period=60,Statistics=['Sum'])
    points=result.get('Datapoints',[])
    observed[metric]=[{'timestamp':p['Timestamp'].isoformat(),'sum':p['Sum']} for p in points]
verified=bool(observed['ImportSuccess'] and observed['ImportFailure']) and any(p['sum']>=1 for p in observed['ImportSuccess'])
receipt.update({'readback_verified':verified,'readback_checked_at':datetime.now(timezone.utc).isoformat(),'readback':observed})
if verified:receipt['status']='verified'
write_json(DATA/'cloudwatch.json',receipt)
deployment=read_json(DATA/'deployment.json',{})
deployment['cloudwatch']=receipt
write_json(DATA/'deployment.json',deployment)
print(json.dumps(receipt,indent=2))
