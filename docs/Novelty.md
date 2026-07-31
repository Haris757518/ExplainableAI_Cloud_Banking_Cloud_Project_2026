# Novelty

- **Unified multi-pillar design:** combines camouflage-resistant neighbor selection (CARE-GNN), balanced graph sampling (PC-GNN), dynamic weight evolution (EvolveGCN), and semi-supervised temporal attention (GTAN, AddGraph) into a single fraud-detection backbone, rather than adopting only one mechanism as most existing systems do.
- **Tiered latency-aware architecture:** separates an inline, sub-50ms GNN scoring path (informed by Albert & Finnegan) from an asynchronous deep-explainability and LLM-based compliance-auditing path (informed by Collins et al.), resolving the latency-vs-explainability-depth trade-off identified as an open gap in the literature.
- **Regulatory-first explainability:** treats explainability as a first-class design requirement from the outset (per SHERA's finding that removing XAI measurably collapses interpretability), rather than retrofitting an explainer after the fact.
- **Cloud-native, digital-banking-specific scope:** unlike cloud-generic anomaly detectors (GAL-MAD, TAGAE, O’Shea et al.) or banking-specific but non-cloud-architected fraud models, the proposed system is explicitly designed as a deployable AWS microservice pipeline for digital banking.
- **Dual robustness to both adversarial evasion and extreme imbalance simultaneously**, rather than addressing either camouflage or imbalance alone as in most single-paper approaches.
