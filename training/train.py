import sys, json, random
from pathlib import Path as _Path
ROOT=_Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from pathlib import Path
import numpy as np
import torch
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from dataset.generator import generate_dataset
from graph.builder import build_graph
from ai_models.gcn import BaselineGCN


def set_seed(seed:int):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)


def run_training(epochs:int=30, samples:int=600, seed:int=42, out_path:str="ai_models/checkpoints/baseline_gcn.pt"):
    set_seed(seed)
    data=generate_dataset(samples,seed=seed)
    split=int(samples*0.8); train=data[:split]; test=data[split:]
    model=BaselineGCN(in_features=20,hidden=48)
    opt=torch.optim.Adam(model.parameters(),lr=0.006,weight_decay=1e-4)
    losses=[]
    for epoch in range(epochs):
        random.shuffle(train); total=0.0; model.train()
        for sample in train:
            graph=build_graph(sample); opt.zero_grad()
            graph_logit,node_logits=model(graph.x,graph.edge_index,graph.edge_weight)
            graph_target=torch.tensor(float(sample.scenario!="NORMAL"))
            node_target=graph.node_labels
            graph_loss=torch.nn.functional.binary_cross_entropy_with_logits(graph_logit,graph_target)
            pos=node_target.sum(); neg=node_target.numel()-pos
            pos_weight=(neg/max(pos,torch.tensor(1.0))).clamp(max=8.0)
            node_loss=torch.nn.functional.binary_cross_entropy_with_logits(node_logits,node_target,pos_weight=pos_weight)
            loss=0.65*graph_loss+0.35*node_loss
            loss.backward(); opt.step(); total+=float(loss.item())
        losses.append(total/max(1,len(train)))
    model.eval(); graph_true=[]; graph_pred=[]; node_true=[]; node_pred=[]
    with torch.no_grad():
        for sample in test:
            graph=build_graph(sample); glogit,nlogits=model(graph.x,graph.edge_index,graph.edge_weight)
            graph_true.append(int(sample.scenario!="NORMAL")); graph_pred.append(int(torch.sigmoid(glogit).item()>=0.5))
            node_true.extend(graph.node_labels.int().tolist()); node_pred.extend((torch.sigmoid(nlogits)>=0.5).int().tolist())
    metrics={
        "graph_accuracy":accuracy_score(graph_true,graph_pred),"graph_precision":precision_score(graph_true,graph_pred,zero_division=0),"graph_recall":recall_score(graph_true,graph_pred,zero_division=0),"graph_f1":f1_score(graph_true,graph_pred,zero_division=0),
        "node_accuracy":accuracy_score(node_true,node_pred),"node_precision":precision_score(node_true,node_pred,zero_division=0),"node_recall":recall_score(node_true,node_pred,zero_division=0),"node_f1":f1_score(node_true,node_pred,zero_division=0),
        "graph_confusion_matrix":confusion_matrix(graph_true,graph_pred).tolist(),"epochs":epochs,"samples":samples,"seed":seed,"final_loss":losses[-1],"feature_dim":20,"model_version":"transaction-conditioned-gcn-v3",
    }
    out=Path(out_path); out.parent.mkdir(parents=True,exist_ok=True)
    torch.save({"model_state":model.state_dict(),"threshold":0.5,"metrics":metrics,"model_version":metrics["model_version"]},out)
    Path("results/runtime").mkdir(parents=True,exist_ok=True); Path("results/runtime/training_metrics.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    return metrics


if __name__=="__main__":
    p=__import__("argparse").ArgumentParser(); p.add_argument("--epochs",type=int,default=30); p.add_argument("--samples",type=int,default=600); p.add_argument("--seed",type=int,default=42); p.add_argument("--out",default="ai_models/checkpoints/baseline_gcn.pt"); a=p.parse_args(); print(json.dumps(run_training(a.epochs,a.samples,a.seed,a.out),indent=2))
