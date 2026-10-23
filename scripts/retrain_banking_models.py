"""Train fresh banking graph and identity models from the bundled raw run."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai_models import banking_study

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True,help='A new directory; existing results are never replaced')
    args=parser.parse_args()
    if args.out.exists():raise ValueError('Use a new output directory')
    raw=ROOT/'results/final_validation/raw'
    manifest=json.loads((raw/'manifest.json').read_text())
    for name,sha in manifest['files'].items():
        if name not in ('measurements.jsonl','frontend-raw.log','ledger-after.json','executed-collector.py','interventions.jsonl','summary.json','recovery-balance-history.json','recovery-transfer-0.json','recovery-transfer-1.json','recovery-transfer-2.json'):raise ValueError('Unexpected input name')
        assert hashlib.sha256((raw/name).read_bytes()).hexdigest()==sha,name
    rows=[json.loads(line) for line in (raw/'measurements.jsonl').read_text().splitlines()]
    spans=[json.loads(line.split('RESEARCH_SPAN ',1)[1]) for line in (raw/'frontend-raw.log').read_text().splitlines() if 'RESEARCH_SPAN ' in line]
    summary=json.loads((raw/'summary.json').read_text())
    banking_study.PROTOCOL.update(train_seconds=216,validation_end_seconds=288,normal_test_end_seconds=360)
    result=banking_study.fit_and_predict(rows,spans,summary,args.out)
    (args.out/'training-and-predictions.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'output':str(args.out),'source_hash':result['source_hash'],'methods':result['methods']},indent=2))


if __name__=='__main__':main()
