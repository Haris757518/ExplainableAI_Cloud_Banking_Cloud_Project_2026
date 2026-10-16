# Verified research foundation and actual design choices

The implementation is an integration hypothesis, not a reproduction or superiority claim over these systems.

| Verified work | Primary reference | Methodological relevance and implementation boundary |
|---|---|---|
| Deng and Hooi, Graph Neural Network-Based Anomaly Detection in Multivariate Time Series, AAAI 2021 | https://ojs.aaai.org/index.php/AAAI/article/view/16523 | Learns variable relationships and graph prediction evidence. This project evaluates a smaller recorded-topology autoencoder; it does not call that model GDN. |
| MicroRCA, NOMS 2020 | https://ieeexplore.ieee.org/document/9110353/ | Combines application/resource symptoms on an attributed graph. Here, missing graph/resource evidence causes abstention rather than invented dependencies. |
| MicroRank, WWW 2021 | https://github.com/IntelligentDDS/MicroRank | Author artifact verifies trace latency, PageRank and spectrum-based localization. Metric-only RE1 cannot supply those execution-path inputs, so a MicroRank reproduction is not claimed. |
| Eadro, ICSE 2023 | https://www.cse.cuhk.edu.hk/lyu/_media/conference/clee_icse2023_eadro.pdf | Multi-source detection/localization and intra/inter-service dependencies. Verified DOI is 10.1109/ICSE48619.2023.00150. This project does not manufacture logs/traces to imitate its modalities. |
| CHASE, arXiv 2406.19711 (2024 preprint) | https://arxiv.org/abs/2406.19711 | Causal-hypergraph multimodal RCA motivates explicit evidence availability. No causal hypergraph learner or causal identification is claimed here. |
| Ying et al., GNNExplainer, NeurIPS 2019 | https://proceedings.neurips.cc/paper_files/paper/2019/hash/d80b7040b773199015de6d3b4293c8ff-Abstract.html | Optimizes explanatory subgraph/features. This implementation computes feature/edge-removal sensitivity; it is not presented as the same optimized-mask method. |
| RCAEval, WWW 2025 benchmark | https://github.com/phamquiluan/RCAEval | Standard independently annotated recorded faults support localization scoring. Original case labels are outside inference inputs and repeated settings are grouped across splits. |

IEEE/ACM pages were partly access-restricted; Eadro metadata/method was verified through the author-hosted paper, and MicroRank through its author repository. Papers do not supply performance numbers for this project's experiments; all reported project results come from the saved local runs.

Testable gap: how much reliability and marginal follow-up scope an explicit evidence gate provides when available telemetry/topology differs by source. The RE1 ablation supports a subset-specific ranking improvement and the follow-up experiment measures resource/column scope. The graph ablation is negative. These observations do not establish causal diagnosis, learned information gain, broad superiority, or novelty against the cited systems. Independent multi-source and cross-system comparisons remain required.
