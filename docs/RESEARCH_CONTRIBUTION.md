# Research contribution and related work

Reviewed against primary publications on 23 October 2026. This is a scoped comparison, not a systematic review or proof of worldwide novelty.

## Proposed contribution

PROBE-XAI integrates progressive inspection of measured evidence, a separation between model symptom scores and supported service attribution, explanations that stop when evidence runs out, and a banking recovery gate that checks committed ledger correctness. The project contributes an implemented workflow and a reproducible banking case study. It does not introduce a new GNN architecture or a formal causal-discovery algorithm.

The strongest demonstrated finding is concrete: fast balance reads passed the demonstrative speed policy while the displayed balance differed from the ledger. The integrity gate rejected that state, then accepted the reconciled state. The investigated commit-order defect was separately reproduced and corrected in executed AWS/PostgreSQL trials, including reader restarts. This is investigator-assisted mechanism validation; it was not autonomous GNN discovery.

## Comparison with existing work

| Primary work | Existing contribution relevant here | Consequence for this project |
|---|---|---|
| [Eadro, ICSE 2023](https://arxiv.org/abs/2302.05092) | Integrates anomaly detection and root-cause localization using multiple sources | Combining detection and localization is established prior work |
| [MicroRCA, NOMS 2020](https://doi.org/10.1109/NOMS47738.2020.9110353) | Uses application and resource observations for service localization | Resource evidence and a service graph are not themselves new |
| [GNNExplainer, NeurIPS 2019](https://arxiv.org/abs/1903.03894) | Explains model predictions through graph structure and features | A model explanation does not itself verify a physical cause or corrective action |
| [PDA, LISA 2007](https://www.usenix.org/legacy/events/lisa07/tech/full_papers/huang/huang_html/index.html) | Uses rules to dispatch scoped diagnostic probes after monitoring detects a problem | Progressive diagnostic inspection has a long history |
| [R2Act, July 2026 preprint](https://arxiv.org/abs/2607.04623) | Evaluates recovery-action validity separately from diagnosis correctness | Recovery-aware evaluation is established related work; the banking integrity test is this project's specific case |
| [DiagGuard trajectory study, August 2026 preprint, revised October 2026](https://arxiv.org/abs/2608.21310) | Studies diagnostic evidence trajectories and audits whether evidence supports diagnoses | Evidence grounding and verification are not unique to PROBE-XAI |
| [RCAEval, WWW Companion 2025](https://arxiv.org/abs/2412.17015) | Provides controlled benchmark recordings for RCA evaluation | Imported RE2 labels belong to the benchmark and are used only for scoring |

## Claims supported by this study

- The implemented dashboard explains recorded problems and the deepest supported mechanism in readable language.
- The integrity gate distinguishes the measured fast-but-incorrect account state from later reconciled recovery in one workload.
- The implemented reader correction passed the retained three-trial AWS before-and-after test and restart checks.
- The revised localizer uses actual processor and database measurements rather than equating the largest GNN residual with the initiating service. New repeat-test results must be taken from the checksum-verified final report, not assumed from the two development cases.

## Claims not established

Worldwide novelty, GNN superiority, production false-positive guarantees, autonomous discovery of the reader bug, universal software correctness and cross-application root-cause accuracy are not established. Inspection-effort units are not measured AWS query costs or formal information gain. Monzo and Starling aggregate statistics do not validate internal banking service diagnoses.

An appropriate project claim is: **We implemented and evaluated an evidence-limited banking investigation workflow that checks transaction integrity before declaring recovery, and demonstrated its value through an executed reader-defect case and corrective verification.**
