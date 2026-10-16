# Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks

## Final review build acceptance

The final banking-first implementation is complete for the verified local scope. The authoritative setup, measured results, exact commands, limitations and faculty walkthrough are in [docs/FINAL_HANDOVER.md](docs/FINAL_HANDOVER.md). [README.md](README.md) is the single current startup guide.

- **Verified:** Balance Enquiry, atomic/idempotent Fund Transfer, Transaction History, real multi-process HTTP/SQL traces, frozen normal calibration, evidence-based localization and application-delay mechanism analysis, conditional recommendations, independent labels and measured follow-up.
- **Measured study:** 270 normal requests; 0 false-positive requests among 54 held-out normal requests. Three bounded application-delay repetitions were detected, correctly localized/classified, and followed by a measured return toward reference.
- **GNN:** Banking-only graph and identity next-request models trained/evaluated with identical budgets. Both localized the three controlled cases; graph normal prediction MSE was slightly worse. Compatible model inference runs, but does not control primary root ranking without established incremental benefit.
- **TC-CFAO:** 3 of 8 existing evidence fields examined across 2 of 3 resources. No AWS cost or total collection-savings claim.
- **Verified checks:** 113 backend tests, 16 browser tests, production build, and final visual checks at 1366×768 and 1920×1080.
- **Preserved:** all earlier benchmark datasets, results, checkpoints, forecasting and independent AWS/EC2/PostgreSQL monitoring code. Current AWS authentication/resource discovery passed; no live cloud fault accuracy was established.
- **Blocked / not implemented here:** the dedicated PostgreSQL contention experiment. SQLite is explicitly labelled; no PostgreSQL lock evidence is fabricated.
- **Unestablished:** GNN superiority, generalized mechanism accuracy, real-money banking, production causality, live AWS banking deployment and broad reliability guarantees.

Frozen local study: [results/banking/measured_20261016/report.json](results/banking/measured_20261016/report.json). Runtime databases and credentials are excluded from Git and the final source package. No workload/fault starts automatically. No new video was created for this completion pass.

Earlier handovers remain accessible under `docs/archive/` and in Git history. They are historical records, not the current setup instructions.
