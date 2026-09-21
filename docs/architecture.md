# System Architecture

1. AWS EC2/RDS and CloudWatch are the cloud-observation layer.
2. A normalization layer converts AWS observations to the internal telemetry schema.
3. The graph builder maps banking workflow dependencies to nodes and edges.
4. The baseline GCN performs node-level anomaly classification; the maximum node probability is used as the graph anomaly score.
5. RCA combines model node score, telemetry abnormality and graph dependency context.
6. The explainability layer uses feature perturbation to estimate which input dimensions most affect the anomaly score.
7. TC-CFAO creates a small causal frontier around ranked root-cause candidates and proposes high-resolution monitoring for those nodes.
