"""Copy only allowlisted research inputs from the verified local export.

Cloud credentials, Kubernetes secrets, machine configuration and SQL backups
are never included in this portable research bundle.
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    report=json.loads((ROOT/'results/final_validation/report.json').read_text())
    source=Path(report['export_directory'])
    metadata=json.loads((source/'export-manifest.json').read_text())
    assert metadata['hash_verified'] and hashlib.sha256((source/'evidence.tar.gz').read_bytes()).hexdigest()==report['export_sha256']
    runs=list((source/'verified-files/telemetry').glob('final-controlled-*/summary.json'))
    assert len(runs)==1
    run=runs[0].parent
    summary=json.loads(runs[0].read_text())
    target=ROOT/'results/final_validation/raw'
    target.mkdir(exist_ok=True)
    selected=['measurements.jsonl','frontend-raw.log','ledger-after.json','executed-collector.py','interventions.jsonl','summary.json']
    hashes={}
    for name in selected:
        payload=(run/name).read_bytes()
        sha=hashlib.sha256(payload).hexdigest()
        if name!='summary.json':assert summary['files_sha256'][name]==sha
        destination=target/name
        if destination.exists():assert destination.read_bytes()==payload,'Never overwrite different evidence'
        else:destination.write_bytes(payload)
        hashes[name]=sha
    recovery=source/'verified-files/telemetry/final-recovery'
    receipts=sorted(recovery.glob('*/verification.json'))
    assert len(receipts)==3
    for name,path in [('recovery-balance-history.json',recovery/'balance-history-reconciliation.json'),*[(f'recovery-transfer-{i}.json',p) for i,p in enumerate(receipts)]]:
        payload=path.read_bytes();destination=target/name
        if destination.exists():assert destination.read_bytes()==payload
        else:destination.write_bytes(payload)
        hashes[name]=hashlib.sha256(payload).hexdigest()
    models={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (target.parent/'banking-models').glob('*.pt')}
    assert len(models)==6
    (target/'manifest.json').write_text(json.dumps({'source_archive_sha256':report['export_sha256'],'execution_id':summary['execution_id'],
        'source_instance':summary['instance'],'files':hashes,'model_files':models,'scope':'Allowlisted research inputs only; final SQL backup remains local.'},indent=2))
    print('Portable final validation inputs and six checkpoint hashes retained.')


if __name__=='__main__':main()
