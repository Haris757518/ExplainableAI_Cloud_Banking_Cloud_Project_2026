from __future__ import annotations
import json
from pathlib import Path
from statistics import mean

from dataset.generator import generate_dataset, generate_sequence, TX_TYPES, SCENARIOS
from graph.structures import topology_signature
from graph.temporal import build_temporal_graph
from backend.services.pipeline import AnalysisPipeline
from analysis.evaluation import evaluate_anomaly_and_rca
from analysis.xai_evaluation import evaluate_xai_faithfulness
from analysis.evaluation import evaluate_counterfactuals
from analysis.cfao_experiment import evaluate_cfao_efficiency


def run_suite(samples: int = 180, sequences: int = 30, seed: int = 42) -> dict:
    pipeline=AnalysisPipeline()
    data=generate_dataset(samples,seed=seed)
    summary={
        "dataset":{"samples":samples,"scenarios":list(SCENARIOS.keys()),"transaction_types":TX_TYPES},
        "anomaly_and_rca":evaluate_anomaly_and_rca(pipeline.engine,data),
        "xai_faithfulness":evaluate_xai_faithfulness(pipeline.engine,data[:min(90,len(data))]),
        "counterfactual":evaluate_counterfactuals(pipeline.engine,data[:min(90,len(data))]),
    }
    graph_by_tx={}
    for tx in TX_TYPES:
        s=generate_dataset(1,seed=seed,tx_types=[tx])[0]
        graph_by_tx[tx]={"nodes":len(s.nodes),"edges":len(s.edges),"signature":topology_signature(s.nodes,s.edges),"path":s.transaction.path}
    summary["graph_diversity"]={"unique_transaction_topologies":len({v["signature"] for v in graph_by_tx.values()}),"by_transaction":graph_by_tx}

    temporal_examples=[]
    for i in range(sequences):
        tx=TX_TYPES[i%len(TX_TYPES)]; scenario=list(SCENARIOS.keys())[1+(i%5)]
        seq=generate_sequence(scenario,steps=8,seed=seed+i,anomaly_start=3,tx_type=tx,topology_change=True)
        tg=build_temporal_graph(seq)
        temporal_examples.append({"transaction_type":tx,"scenario":scenario,"steps":tg.length,"unique_topologies":len(set(tg.sequence.topology_signatures)),"topology_change_steps":tg.topology_change_steps})
    summary["temporal"]={"sequences":sequences,"examples":temporal_examples[:10],"sequences_with_topology_change":sum(bool(x["topology_change_steps"]) for x in temporal_examples)}
    summary["tc_cfao"]=evaluate_cfao_efficiency(pipeline,data)

    out=Path("results/runtime/research_suite.json"); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(summary,indent=2),encoding="utf-8")
    return summary
