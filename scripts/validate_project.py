import sys, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from dataset.generator import generate_sample, generate_sequence
from backend.services.pipeline import AnalysisPipeline
from analysis.temporal import analyze_temporal_window

SCENARIOS=["NORMAL","CPU_SPIKE","DATABASE_LATENCY","SERVICE_OVERLOAD","NETWORK_DEGRADATION","CASCADING_FAILURE"]
p=AnalysisPipeline(); status={"scenarios":{},"temporal":None}
for sc in SCENARIOS:
    r=p.analyze(generate_sample(sc,42,0,tx_type="UPI_PAYMENT"),source="validation")
    status["scenarios"][sc]={"is_anomaly":r.is_anomaly,"score":round(r.anomaly_score,4),"root":r.root_causes[0].node if r.root_causes else None}
t=analyze_temporal_window(p.engine,generate_sequence("DATABASE_LATENCY",8,42,3)); status["temporal"]={"onset_step":t["onset_step"],"peak":t["peak"],"recovered":t["recovered"]}
print(json.dumps(status,indent=2))
