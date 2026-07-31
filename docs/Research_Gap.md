# Research Gap Analysis

### Member 1 (Haris K)
- Adversarial robustness is rarely addressed: most GNN fraud detectors assume benign neighborhoods and do not explicitly counter camouflaged fraudsters.
- Class imbalance is handled ad hoc: structured, graph-aware balanced sampling outperforms naive oversampling yet remains underused in production pipelines.
- Static graph assumptions limit real-world deployment where new accounts and relationships are created continuously.
- Label scarcity in production is underexplored: fully supervised approaches assume large labeled datasets that rarely reflect real banking pipelines.

### Member 2 (Keshav Gokaram)
- No reviewed system combines GNN-based cloud performance/anomaly detection with native explainability in a digital-banking-specific deployment context; cloud-generic systems (GAL-MAD, TAGAE, O’Shea et al.) are not banking-specific, while the FinTech survey is domain-specific but not cloud-performance-specific.
- Explainability quality is domain-dependent and uneven: SHAP and attention methods reliably explain node/resource-level anomalies but struggle with fine-grained network-level anomalies.
- Reproducibility is inconsistent: several reviewed systems rely on proprietary or partially disclosed datasets, complicating benchmark comparison.
- Regulatory-grade, auditable explainability is explicitly called out as an open need in FinTech but not yet demonstrated end-to-end in any single reviewed cloud-performance system.

### Member 3 (Harish Kumar)
- No single system integrates real-time sub-50ms inference, privacy-preserving multi-tenant federation, deep XAI regulatory auditing, and class-imbalance resilience into one cloud-native microservice framework.
- A trade-off exists between latency and explainability depth: sub-50ms systems use lightweight attributions while deep narrative XAI engines introduce overhead unsuitable for live payment gateways; a tiered pipeline remains underexplored.
- Cold-start and imbalance bottlenecks persist in production — novel accounts (label scarcity) and extreme class imbalance (~0.1% fraud) cause message passing to over-smooth minority fraud signals.

### Combined Gap
Across all fifteen papers, no existing system unifies adversarial-camouflage robustness, structured class-imbalance handling, dynamic/temporal graph adaptation, native regulatory-grade explainability, and low-latency cloud-native deployment within a single digital banking platform. Individual papers solve one or two of these dimensions well (e.g., CARE-GNN for camouflage, PC-GNN for imbalance, EvolveGCN for dynamic graphs, TAGAE for latency, Collins et al. for LLM-based auditing) but none combine all of them into one deployable, tiered cloud architecture. This combined gap is the precise problem space the proposed project addresses.
