"""Chronological held-out alert timing; labels are consulted only after alerts."""
from pathlib import Path
import sys,json,argparse
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dataset.benchmarks import manifest,load_case,labels_for_evaluation

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);args=parser.parse_args();out=Path(args.out)
    if out.exists():raise SystemExit('Choose a new output path')
    rows=[]
    for entry in manifest()['cases']:
        if entry['source']!='rcaeval' or entry['split']!='test':continue
        case=load_case(entry['id']);first=min(s.observations[0].timestamp for s in case.series);last=case.provenance['recording_end'];reference_end=first+min(600,.2*(last-first));alerts=set()
        for series in case.series:
            points=[p for p in series.observations if p.value is not None]
            reference=[p.value for p in points if p.timestamp<=reference_end][-256:]
            if len(reference)<12:continue
            center=float(np.median(reference));scale=max(1.4826*float(np.median(abs(np.asarray(reference)-center))),abs(center)*.05,1e-8)
            preceding=False
            for point in points:
                if point.timestamp<=reference_end:continue
                score=max(0,point.value-center)/scale
                current=score>=3.5
                if current and preceding:alerts.add(point.timestamp)
                preceding=current
        # No root, fault or injection annotation is used above this line.
        truth=labels_for_evaluation(entry['id']);after=sorted(t for t in alerts if t>=truth['inject_time']);before=sorted(t for t in alerts if t<truth['inject_time'])
        rows.append({'case_id':entry['id'],'post_injection_detection_delay_seconds':after[0]-truth['inject_time'] if after else None,'pre_injection_alert_timestamps':len(before),'pre_injection_any_alert':bool(before),'post_injection_detected':bool(after),'label_source':truth['label_source']})
    delays=[r['post_injection_detection_delay_seconds'] for r in rows if r['post_injection_detected']]
    report={'dataset':'RCAEval RE1 held-out recordings','cases':len(rows),'detected_cases':len(delays),'mean_detected_case_delay_seconds':float(np.mean(delays)) if delays else None,'median_detected_case_delay_seconds':float(np.median(delays)) if delays else None,'cases_with_pre_injection_alerts':sum(r['pre_injection_any_alert'] for r in rows),'protocol':'Frozen first min(600s,20% recording duration) reference; positive robust deviation >=3.5 sustained for two valid observations. Any-resource alert. No point adjustment.','limitations':['Post-injection delay is conditional on detection; pre-injection false alarms are reported separately.','No annotated recovery/end time is available, so post-injection points are not manufactured into precise duration labels.','Timing evaluation is separate from fixed-checkpoint localization.'],'cases_detail':rows}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='cases_detail'},indent=2))

if __name__=='__main__':main()
