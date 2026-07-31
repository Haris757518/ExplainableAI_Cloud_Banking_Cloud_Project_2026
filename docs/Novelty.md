# Novelty

This project introduces several novel contributions to the field of cloud performance analytics:

1. **GNN-Based Cloud Topology Modeling**: Unlike traditional time-series anomaly detection, this project models the entire cloud infrastructure as a dynamic graph. By leveraging Graph Neural Networks, the system can understand the complex interdependencies between resources, allowing for the detection of subtle, distributed performance anomalies that traditional methods miss.
2. **Integrated Explainable AI (XAI)**: We introduce a dedicated XAI module that interprets the GNN's predictions. When an anomaly is detected, the system provides a transparent breakdown of the contributing factors (e.g., identifying exactly which node or connection is responsible for the bottleneck), transforming black-box predictions into actionable insights.
3. **Banking-Specific Cloud Context**: The framework is specifically tailored to address the strict reliability and latency requirements of digital banking systems, focusing on maintaining the high availability of critical financial transaction processing environments.
4. **End-to-End AWS Native Integration**: The solution proposes a comprehensive, cloud-native architecture utilizing a suite of AWS services (SageMaker, Lambda, EC2, CloudWatch) to provide a scalable, real-time analytics pipeline.
