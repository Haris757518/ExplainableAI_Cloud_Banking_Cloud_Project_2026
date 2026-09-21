import sys
from pathlib import Path as _Path
ROOT=_Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse, random, json
from pathlib import Path
import numpy as np
import torch
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from dataset.generator import generate_dataset
from graph.builder import build_graph
from ai_models.gcn import BaselineGCN


def set_seed(seed: int):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)


def run_training(epochs: int = 35, samples: int = 600, seed: int = 42, out_path: str = "ai_models/checkpoints/baseline_gcn.pt"):
    set_seed(seed)
    data = generate_dataset(samples, seed=seed)
    split = int(samples * 0.8)
    train, test = data[:split], data[split:]
    model = BaselineGCN(in_features=16, hidden=32)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)
    losses=[]
    model.train()
    for epoch in range(epochs):
        random.shuffle(train)
        total=0.0
        for sample in train:
            graph = build_graph(sample)
            optimizer.zero_grad()
            _, logits = model(graph.x, graph.edge_index)
            loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, graph.node_labels)
            loss.backward(); optimizer.step(); total += float(loss.item())
        losses.append(total/len(train))
    model.eval()
    graph_true=[]; graph_pred=[]; node_true=[]; node_pred=[]
    with torch.no_grad():
        for sample in test:
            graph=build_graph(sample)
            glogit, nlogits=model(graph.x, graph.edge_index)
            graph_true.append(int(sample.scenario != "NORMAL"))
            graph_pred.append(int(torch.sigmoid(glogit).item() >= 0.5))
            node_true.extend(graph.node_labels.int().tolist())
            node_pred.extend((torch.sigmoid(nlogits)>=0.5).int().tolist())
    metrics={
        "graph_accuracy": accuracy_score(graph_true, graph_pred),
        "graph_precision": precision_score(graph_true, graph_pred, zero_division=0),
        "graph_recall": recall_score(graph_true, graph_pred, zero_division=0),
        "graph_f1": f1_score(graph_true, graph_pred, zero_division=0),
        "node_accuracy": accuracy_score(node_true, node_pred),
        "node_precision": precision_score(node_true, node_pred, zero_division=0),
        "node_recall": recall_score(node_true, node_pred, zero_division=0),
        "node_f1": f1_score(node_true, node_pred, zero_division=0),
        "graph_confusion_matrix": confusion_matrix(graph_true, graph_pred).tolist(),
        "epochs": epochs,
        "samples": samples,
        "seed": seed,
        "final_loss": losses[-1],
    }
    out=Path(out_path); out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state": model.state_dict(), "threshold": 0.5, "metrics": metrics}, out)
    Path("results/runtime").mkdir(parents=True, exist_ok=True)
    Path("results/runtime/training_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--epochs", type=int, default=35); p.add_argument("--samples", type=int, default=600); p.add_argument("--seed", type=int, default=42); p.add_argument("--out", default="ai_models/checkpoints/baseline_gcn.pt")
    args=p.parse_args(); print(json.dumps(run_training(args.epochs,args.samples,args.seed,args.out),indent=2))
