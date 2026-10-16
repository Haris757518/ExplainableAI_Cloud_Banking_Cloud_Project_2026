"""Serialize the deterministic training-only AR models used by evaluation."""
from pathlib import Path
import sys,json,argparse
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dataset.benchmarks import manifest,load_case
from analysis.forecasting import fit_models,predict

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args();out=Path(args.out)
    if out.exists():raise SystemExit('Choose a new model artifact path')
    models=[]
    for entry in manifest()['cases']:
        if entry['source']!='microsoft':continue
        case=load_case(entry['id']);series=case.series[0];values=[p.value for p in series.observations];end=int(.6*len(values));state=fit_models(values,end)
        if state is None:continue
        serialized={k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in state.items()}
        restored={**serialized,'coef':np.asarray(serialized['coef'])}
        idx=len(values)-1;original=predict(values,idx,state,'ridge_ar12');reloaded=predict(values,idx,restored,'ridge_ar12')
        if original!=reloaded:raise ValueError('Forecast model serialization changed prediction')
        models.append({'case_id':case.id,'source_sha256':case.collection,'training_rows':[0,end],'model':'ridge_ar12','ridge_penalty':1,'lag_count':12,'state':serialized,'serialization_verified':True})
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'models':models,'source_revision':manifest()['microsoft_revision'],'labels_used':False,'semantics':'First60% observed rows fit coefficients; next20% selects method/calibrates residuals; final20% is held out. Model states reproduce the fixed evaluation fits.'},indent=2,allow_nan=False),encoding='utf-8');print('Serialized and round-trip verified',len(models),'training-only forecast models')

if __name__=='__main__':main()
