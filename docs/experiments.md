# Experiments

## 1. Baseline GCN

`training/train.py` trains the transaction-conditioned two-layer GCN on variable transaction-specific graphs and writes measured metrics to `results/runtime/training_metrics.json`.

## 2. Statistical and graph baselines

`experiments/research_suite.py` compares the GNN with telemetry-only anomaly detection and telemetry-only / graph-centrality RCA baselines. These baselines are included for transparent evaluation rather than to assume a winner in advance.

## 3. Temporal graph experiment

`training/train_temporal.py` trains the temporal GCN + GRU on graph sequences. Each sequence can contain a controlled anomaly interval, recovery, and temporary topology drift. `analysis.temporal` reports onset, peak, recovery, unique topology count, and topology-change steps.

## 4. XAI evaluation

`analysis.xai_evaluation.evaluate_xai_faithfulness` measures the anomaly-score fraction removed when the model's top-ranked features are ablated.

## 5. Counterfactual evaluation

`analysis.evaluation.evaluate_counterfactuals` applies simulated node-level normalization interventions and records anomaly-score reductions. This is evidence of model sensitivity, not proof of real-world causality.

## 6. TC-CFAO evaluation

`analysis.cfao_experiment.evaluate_cfao_efficiency` compares an all-node 5-second investigation baseline with the causal-frontier policy. It records frontier size, observation reduction, and whether the leading diagnosis remains consistent after focused re-analysis.

## 7. Alibaba benchmark

The Alibaba Cluster Trace v2021 adapter can build real microservice graph snapshots. The benchmark is external cloud/microservice data and is not converted into banking labels.

## 8. Run everything

```powershell
python training/train.py --epochs 20 --samples 600 --seed 42
python training/train_temporal.py
python scripts/run_research_suite.py
python scripts/run_research_plots.py
```

Do not describe synthetic or compatibility measurements as production AWS measurements.
