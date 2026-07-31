# Literature Survey

## Haris K (Papers 1-5)

1. **Enhancing Graph Neural Network-based Fraud Detectors against Camouflaged Fraudsters (CARE-GNN)**
   - *Ref:* Dou, Y., Liu, Z., Sun, L., Deng, Y., Peng, H., & Yu, P. S. (2020).
   - *Objective:* Improve GNN-based fraud detection by explicitly countering fraudster “camouflage” — the deliberate mimicking of benign behavior to evade detection.
   - *Findings:* Outperforms GCN, GraphSAGE, and prior GNN fraud detectors in ROC-AUC and Recall on both datasets. The RL neighbor selector adaptively filters out noisy, camouflaged connections during training.

2. **Pick and Choose: A GNN-based Imbalanced Learning Approach for Fraud Detection (PC-GNN)**
   - *Ref:* Liu, Y., Ao, X., Qin, Z., Chi, J., Feng, J., Yang, H., & He, Q. (2021).
   - *Objective:* Address the severe class imbalance inherent in transaction fraud graphs without simply oversampling or undersampling raw data.
   - *Findings:* Consistently improves AUC, F1, and G-Mean over CARE-GNN under high imbalance ratios. The label-balanced sampler mitigates majority-class bias more effectively than random resampling.

3. **EvolveGCN: Evolving Graph Convolutional Networks for Dynamic Graphs**
   - *Ref:* Pareja, A., Domeniconi, G., Chen, J., Ma, T., Suzumura, T., Kanezashi, H., Kaler, T., Schardl, T., & Leiserson, C. (2020).
   - *Objective:* Model graphs that change structure and node population over time without relying on fixed node embeddings that become stale.
   - *Findings:* Outperforms static GCN/GAT baselines on the Elliptic financial transaction dataset. Handles entirely new nodes at test time.

4. **Semi-Supervised Credit Card Fraud Detection via Attribute-Driven Graph Representation (GTAN)**
   - *Ref:* Xiang, S., Zhu, M., Cheng, D., Li, E., Zhao, R., Ouyang, Y., Chen, L., & Zheng, Y. (2023).
   - *Objective:* Improve credit card fraud detection when most transaction labels are unavailable, common in real banking pipelines.
   - *Findings:* Outperforms fully-supervised GNN fraud baselines despite using only a small fraction of labeled data. The gated temporal attention module captures short-term behavioral bursts.

5. **AddGraph: Anomaly Detection in Dynamic Graphs via Attention-based Temporal GCN**
   - *Ref:* Zheng, L., Li, Z., Li, J., Li, Z., & Gao, J. (2019).
   - *Objective:* Detect anomalous edges as they appear in a continuously evolving graph, rather than only classifying entire graph snapshots.
   - *Findings:* Outperforms static anomaly baselines and prior dynamic graph anomaly methods in AUC. Requires substantially fewer labeled anomalies than fully supervised alternatives.

## Keshav Gokaram (Papers 6-10)

6. **GAL-MAD: Towards Explainable Anomaly Detection in Microservice Applications Using Graph Attention Networks**
   - *Ref:* Akmeemana, L., Faiz, H., Attanayake, C., & Wickramanayake, S. (2025).
   - *Objective:* Detect anomalies in cloud-hosted microservice applications by jointly modeling structural dependencies and temporal behavior, then explain each anomaly at the service/metric level.
   - *Findings:* Outperforms GDN, MAD-GAN, Kitsune, and a Transformer baseline on recall (e.g., 98.8% at 95:5 ratio vs 80.9% for GDN).

7. **Graph Neural Networks for Anomaly Detection in Cloud Infrastructure (TAGAE)**
   - *Ref:* Jakkaraju, A. (2025).
   - *Objective:* Build a production-oriented GNN framework detecting node-, edge-, and distributed-level anomalies across large-scale cloud infrastructure under real-time latency constraints.
   - *Findings:* 94.2% F1 and 96.5% AUC-PR overall, with 68ms inference latency — a 63% reduction versus GraphSAGE.

8. **Explainable Graph Ensemble Learning for Multivariate Time Series Anomaly Detection in Cloud Microservice Architectures**
   - *Ref:* O’Shea, K., Yan, S., Yu, M., Chen, X., Mauceri, S., Dhariyal, B., Xu, L., O’Connor, N., & Liu, M. (2025).
   - *Objective:* Improve interpretability of multivariate time-series anomaly detection in cloud microservices by explaining anomalies through temporal and topological structure rather than flat feature importance.
   - *Findings:* Achieves an averaged event-wise F1 score of 0.94 across the two datasets. Attention-weight visualizations give operators combined topological-and-temporal explanations for each flagged event.

9. **SHERA: SHAP-Enhanced Resource Allocation for VM Scheduling and Efficient Cloud Computing**
   - *Ref:* Slathia, A. S., Sharma, A., Krishna, P. B., Anand, S., Rathi, A., Joseph, L., & Gao, X. Z. (2025).
   - *Objective:* Apply explainable AI to cloud resource-allocation and VM-scheduling decisions to improve transparency around energy efficiency and cost, rather than targeting anomaly detection directly.
   - *Findings:* Random Forest is the best predictor: 96.8% accuracy, RMSE 0.16. SHAP dependence plots reveal actionable scheduling insights.

10. **Detecting Anomalies in FinTech: A Graph Neural Network and Feature Selection Perspective**
    - *Ref:* Hoang, V. T., Dinh, N., Le, V.-T., Tran-Trung, K., Nguyen Van, B., & Meethongjan, K. (2026).
    - *Objective:* Provide a comprehensive survey of GNN-based anomaly detection specifically within FinTech and digital-banking systems, emphasizing feature selection for high-dimensional, noisy financial data.
    - *Findings:* Categorizes FinTech anomalies requiring different modeling granularities. Identifies interpretability as a principal open challenge — GNNs are frequently black boxes for regulators.

## Harish Kumar (Papers 11-15)

11. **Real-Time Financial Fraud Detection Using Adaptive Graph Neural Networks and Federated Learning**
    - *Ref:* Dağ, A., Sahin, S., & Karaköse, M. (2025).
    - *Objective:* Develop a real-time, privacy-preserving financial fraud detection framework that dynamically adapts to evolving fraud patterns across multiple banking institutions without exposing sensitive customer data.
    - *Findings:* 15–30% increase in fraud detection accuracy over baseline ML models and static GNNs. Reduces false-positive rates by 28.4% across federated banking nodes.

12. **Combining Graph Neural Networks and Anomaly Detection for Low-Latency Credit Card Fraud Prevention**
    - *Ref:* Albert, N., & Finnegan, A. (2025).
    - *Objective:* Design a hybrid dual-component architecture detecting multi-entity fraud schemes while operating within strict real-time payment gateway latency constraints (<50ms).
    - *Findings:* Outperforms Random Forest and XGBoost in ROC-AUC with significant false-positive reduction. Reaches sub-50ms inference latency required for live payment processing.

13. **Explainable Hybrid Graph Neural Networks and Large Language Models for Intelligent Financial Fraud Detection and Risk Analytics**
    - *Ref:* Collins, N., Gabriel, S., Mate, Z., Micheal, J., & Michael, G. (2026).
    - *Objective:* Bridge the explainability gap in automated banking compliance by unifying structural GNN transaction embeddings with LLM narrative reasoning.
    - *Findings:* Outperforms single-modality GNN and LLM models on complex, coordinated fraud rings. Substantially reduces manual compliance review time (45% reduction) by automating audit report generation.

14. **ECCFD-GNN: A Novel Risk-Sensitive Graph Neural Network Model for Fraudulent Transaction Detection**
    - *Ref:* Srivastava, S., Gupta, V., Mehndiratta, V., & Rani, S. (2026).
    - *Objective:* Address extreme class imbalance in credit card transaction graphs by introducing a multi-graph structural framework and explicit risk-score integration.
    - *Findings:* Radius and Feature-Correlation graphs effectively capture subtle interdependencies traditional models miss. Achieves high precision and recall on extreme minority-class fraud instances.

15. **SpaceGNN: Multi-Space Graph Neural Network for Node Anomaly Detection with Extremely Limited Labels**
    - *Ref:* Dong, Y., et al. (2025).
    - *Objective:* Detect anomalous nodes in complex transaction and cloud infrastructure networks when labeled fraud data is extremely scarce (<0.1% labeled nodes).
    - *Findings:* Outperforms GCN, GraphSAGE, and GAT baselines by 18.2% AUC-ROC under ultra-low label availability. Effectively captures hierarchical money-laundering trees and nested cloud infrastructure dependencies via hyperbolic embeddings.
