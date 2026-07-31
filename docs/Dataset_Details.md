# Dataset Details

| Dataset | Source / URL | Size / Records | Features | License | Purpose | Preprocessing |
|---------|--------------|----------------|----------|---------|---------|---------------|
| Yelp Fraud (Spam Review) | DGL / GitHub, used in Dou et al. 2020 | ~45,954 nodes, 3 relation types | Review text embeddings, rating, user/product relations | Research use | Camouflage-resistant fraud detector benchmarking | Graph construction (R-U-R, R-S-R, R-T-R relations), feature normalization |
| Amazon Fraud | DGL / GitHub, used in Dou et al. 2020, Liu et al. 2021 | ~11,944 nodes, 3 relation types | Review/rating features, user-product-time relations | Research use | Imbalance-aware sampling and camouflage robustness testing | Multi-relation graph construction, label-balanced subgraph sampling |
| Elliptic Bitcoin Dataset | Kaggle, used in Pareja et al. 2020, Dong et al. 2025 | 203,769 nodes, 234,355 edges | 166 anonymized transaction features, licit/illicit/unknown labels | Open | Dynamic graph adaptation and low-label anomaly detection benchmarking | Temporal snapshot splitting, unknown-label masking for semi-supervised evaluation |
| IEEE-CIS Fraud Detection | Kaggle | ~590,000 transactions, 3.5% fraud | Transaction amount, card, device, and identity features | Kaggle competition license | Low-latency inline scoring benchmark | Missing-value imputation, categorical encoding, graph construction from shared identifiers |
| Synthetic Digital Banking Transaction Graph | Generated in-house for this project | Target: 100K+ nodes | Account, card, merchant, device nodes; transaction edges with amount/time/location | Internal use | Prototype the tiered inline + asynchronous architecture | Synthetic anomaly injection, relation-type labeling, temporal snapshotting |
