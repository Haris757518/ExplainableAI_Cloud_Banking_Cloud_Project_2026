"""Offline reproduction from immutable downloaded official snapshots."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
from datetime import datetime,timezone
from dataset.real_banking.store import DATA, metrics, sources, write_json
from analysis.banking_api_anomalies import analyze
from analysis.banking_api_forecasting import evaluate

def main():
    reports={}
    for bank,service in [('monzo','Open Banking Payment Initiation'),('starling','Payment Initiation (Open Banking)')]:
        rows=metrics(bank,service,'latency')
        result=analyze(rows)
        result['forecast']=evaluate(rows)
        result['selection']={'bank':bank,'service':service,'metric':'latency'}
        result['created_at']=datetime.now(timezone.utc).isoformat()
        result['run_id']='reproduced-'+bank
        write_json(DATA/'analyses'/f'reproduced-{bank}.json',result)
        reports[bank]=result
    write_json(DATA/'evaluation.json',reports)
    print(json.dumps({bank:{'split':r['series'][0]['counts'],'flags':len(r['series'][0]['findings']),
            'forecast_methods':r['forecast']['methods']} for bank,r in reports.items()},indent=2))

if __name__=='__main__': main()
