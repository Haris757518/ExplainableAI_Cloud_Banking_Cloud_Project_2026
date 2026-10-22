"""Reproduce the banking explanation offline. Does not access AWS."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis.banking_replay import ROOT,run_replay,readable_report

if __name__=='__main__':
    result=run_replay()
    output=ROOT/'results/aws_workload'
    (output/'investigation-result.json').write_text(json.dumps(result,indent=2))
    (output/'investigation-report.md').write_text(readable_report(result),encoding='utf-8')
    print(readable_report(result))
