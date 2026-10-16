import sys, json, random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from dataset.generator import generate_sequence, SCENARIOS, TX_TYPES
from graph.temporal import build_temporal_graph
from ai_models.gcn import TemporalGCN


def train(epochs=18, sequences=60, steps=8, seed=42, out_path="ai_models/checkpoints/temporal_gcn.pt"):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    items=[]
    anomaly_scenarios=list(SCENARIOS.keys())[1:]
    for i in range(sequences):
        tx=TX_TYPES[i%len(TX_TYPES)]; scenario=anomaly_scenarios[i%len(anomaly_scenarios)]
        items.append((generate_sequence(scenario,steps=steps,seed=seed+i,anomaly_start=max(2,steps//2-1),tx_type=tx,topology_change=True),1))
    normal=[(generate_sequence("NORMAL",steps=steps,seed=seed+5000+i,anomaly_start=steps,tx_type=TX_TYPES[i%len(TX_TYPES)],topology_change=False),0) for i in range(max(20,sequences//2))]
    items=normal+items; random.shuffle(items); split=int(.8*len(items)); train_items=items[:split]; test_items=items[split:]
    model=TemporalGCN(in_features=20,hidden=48,temporal_hidden=40); opt=torch.optim.Adam(model.parameters(),lr=.004,weight_decay=1e-4)
    for _ in range(epochs):
        model.train()
        for seq,label in train_items:
            graphs=build_temporal_graph(seq).graphs
            target=torch.tensor([float(label)]); opt.zero_grad(); logit=model(graphs)
            loss=torch.nn.functional.binary_cross_entropy_with_logits(logit,target); loss.backward(); opt.step()
    model.eval(); y=[]; p=[]
    with torch.no_grad():
        for seq,label in test_items:
            graphs=build_temporal_graph(seq).graphs; score=torch.sigmoid(model(graphs)).item(); y.append(label); p.append(int(score>=.5))
    metrics={"accuracy":accuracy_score(y,p),"precision":precision_score(y,p,zero_division=0),"recall":recall_score(y,p,zero_division=0),"f1":f1_score(y,p,zero_division=0),"epochs":epochs,"sequences":len(items),"steps":steps,"seed":seed,"model_version":"temporal-transaction-gcn-v2"}
    Path(out_path).parent.mkdir(parents=True,exist_ok=True); torch.save({"model_state":model.state_dict(),"metrics":metrics,"model_version":metrics["model_version"]},out_path)
    Path("results/runtime/temporal_metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    return metrics

if __name__=="__main__": print(json.dumps(train(),indent=2))
