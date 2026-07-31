# Objectives

- Design a camouflage-resistant, multi-relation GNN fraud detection module capable of filtering adversarially disguised fraudulent connections in transaction graphs.
- Develop a class-imbalance-aware training pipeline using structured graph sampling to reliably detect rare fraudulent transactions without excessive false positives.
- Implement a dynamic graph adaptation mechanism that incorporates new accounts, cards, and relationships into the model without full retraining.
- Build a native explainability layer (attention-based and/or SHAP-based) that generates human-readable, regulator-facing justifications for each flagged transaction.
- Architect and deploy a tiered, low-latency AWS cloud infrastructure that separates real-time inline fraud scoring from asynchronous compliance auditing and reporting.
- Evaluate the proposed system against established public benchmarks (Yelp, Amazon, Elliptic, IEEE-CIS) using AUC-ROC, F1, G-Mean, and inference latency as comparison metrics against baseline GNN and non-GNN detectors.
