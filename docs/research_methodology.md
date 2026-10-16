# Research Methodology

## Proposed System

**Transaction-Conditioned Causal-Frontier Adaptive Observability (TC-CFAO)** is the proposed research mechanism in this project.

The system conditions cloud-performance analysis on the digital-banking transaction path rather than monitoring infrastructure as isolated resources.

### Pipeline

Digital Banking Transaction
→ Transaction Context
→ Business-to-Infrastructure Graph
→ Temporal/Graph Telemetry
→ GNN Anomaly Detection
→ Transaction-Conditioned RCA
→ Causal Frontier
→ Adaptive Telemetry
→ High-Resolution Re-analysis
→ XAI + Refined RCA

## Graph Representation

The current baseline graph models:

- API Gateway
- Payment Service
- EC2
- RDS
- Cache
- Queue
- Notification Service

Edges capture calls, execution/hosting, data access, publication, and consumption relationships.

Transaction types are associated with transaction paths so graph analysis can emphasize infrastructure relevant to the current transaction.

## Baseline

The baseline model is a small GCN with node-level and graph-level outputs. It is intentionally lightweight so the system can run on CPU and later be replaced by a stronger temporal GNN.

## Explainability

The current baseline uses feature perturbation: one feature is suppressed across nodes and the change in graph anomaly score is observed. The system also exposes node scores and the dependency path. A graph-native explanation method can be added later without changing the API contract.

## Counterfactual Evidence

The project includes a simulated intervention that restores a suspected node's anomalous telemetry toward a normal baseline and re-runs the model. This is evidence from a controlled simulation, not a causal proof about production AWS behavior.

## TC-CFAO Experiment

The adaptive layer identifies a causal frontier and assigns a high-resolution sampling policy to that frontier while keeping unrelated nodes at coarse resolution. A second synthetic telemetry window is re-analyzed to compare evidence before and after focused observation.

## Research Evaluation

Compare:

1. Threshold/statistical baseline
2. Baseline GNN
3. GNN + transaction conditioning
4. GNN + RCA
5. GNN + XAI
6. GNN + TC-CFAO
7. Temporal GNN / counterfactual extensions

Measure actual:

- anomaly detection metrics
- node-level localization metrics
- root-cause localization
- telemetry volume / observation cost
- inference time
- RCA evidence change

Do not fabricate results. Label synthetic and AWS-derived observations separately.
