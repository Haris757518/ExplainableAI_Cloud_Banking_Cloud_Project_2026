"""Explicit local import of retained collector artifacts; labels stored separately."""
import argparse,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dataset.banking_cloud_import import normalize
from dataset.banking_cloud_schema import ExperimentLabel
from dataset.real_banking.store import ROOT,write_json

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--recording',required=True);parser.add_argument('--collector',required=True);parser.add_argument('--labels');args=parser.parse_args()
    recording=json.loads(Path(args.recording).read_text(encoding='utf-8'));raw=Path(args.collector).read_bytes()
    case=normalize(recording,raw)
    folder=ROOT/'results/banking_cloud_recordings'/case.collection
    if folder.exists():raise SystemExit('This collector artifact is already imported; existing records are immutable')
    annotation=None
    if args.labels:
        annotation=ExperimentLabel.model_validate_json(Path(args.labels).read_text(encoding='utf-8'))
        if annotation.execution_id!=recording['execution_id']:raise ValueError('Annotation execution differs from measured recording')
    folder.mkdir(parents=True)
    (folder/'collector.json').write_bytes(raw)
    write_json(folder/'case.json',case.model_dump(mode='json'))
    if annotation:write_json(ROOT/'results/banking_cloud_annotations'/f'{case.collection}.json',annotation.model_dump(mode='json'))
    write_json(folder/'manifest.json',{'collection':case.collection,'source':case.source.model_dump(),
        'environment':case.provenance['environment'],'measurements':sum(len(s.observations) for s in case.series),
        'series':len(case.series),'edges':len(case.edges),'execution_evidence_status':case.provenance['execution_evidence_status'],
        'labels_in_inference':False})
    print('Imported retained collector artifact. Deployment/execution attestation must be reviewed separately.')

if __name__=='__main__':main()
