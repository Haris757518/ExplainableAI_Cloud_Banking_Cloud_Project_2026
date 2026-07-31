# Research Gap

Despite the advancements in cloud monitoring and machine learning, several critical gaps remain:

1. **Lack of Topological Awareness**: Most existing anomaly detection systems treat cloud metrics (CPU, RAM, network) as isolated time-series data. They fail to understand the structural and functional dependencies between different microservices and cloud resources, leading to false positives and an inability to detect complex, cascading failures.
2. **The Black-Box Problem**: While deep learning models offer high accuracy in detecting anomalies, they provide no explanation for their predictions. In the heavily regulated digital banking sector, an unexplainable alert is often unactionable, as administrators require a clear understanding of the root cause before intervening in production systems.
3. **Absence of Unified XAI-GNN Frameworks**: There is a significant lack of integrated frameworks that combine the topological modeling power of Graph Neural Networks (GNNs) with Explainable AI (XAI) specifically tailored for cloud performance analytics in digital banking.
