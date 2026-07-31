# Literature Survey

*This section provides a summary of the literature reviewed for this project.*

## 1. Cloud Performance Monitoring in Banking
Traditional approaches to cloud monitoring have heavily relied on threshold-based alerts. While effective for basic resource tracking, these methods struggle with the dynamic scaling and microservice interdependencies typical in modern digital banking platforms.

## 2. Machine Learning for Anomaly Detection
Recent research has increasingly adopted machine learning techniques, such as Random Forests, Support Vector Machines (SVMs), and standard neural networks, for anomaly detection in cloud logs. However, these models often fail to capture the topological relationships between different cloud nodes (e.g., how a database instance affects a specific API gateway).

## 3. Graph Neural Networks (GNNs) in Cloud Systems
GNNs have emerged as a powerful tool for modeling complex network topologies. Studies show that representing cloud infrastructure as a graph—where nodes are resources (VMs, databases) and edges are communication links—allows GNNs to significantly outperform traditional ML models in detecting cascading failures and distributed bottlenecks.

## 4. Explainable AI (XAI)
The 'black-box' nature of advanced deep learning models is a major barrier to adoption in mission-critical banking systems. Research into XAI techniques like SHAP (SHapley Additive exPlanations) and LIME has demonstrated how model predictions can be translated into human-readable insights, allowing administrators to trust and act upon AI-generated alerts.
