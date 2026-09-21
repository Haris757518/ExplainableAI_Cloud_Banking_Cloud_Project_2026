# Demo Script

Use `python scripts/demo.py --scenario DATABASE_LATENCY` after training.

Live story:
1. A banking transaction reaches the payment service.
2. RDS database latency becomes abnormal.
3. The GNN detects an anomalous graph state.
4. The RCA layer ranks RDS-01 highly.
5. The explanation layer highlights latency/database-latency signals.
6. TC-CFAO proposes 5-second monitoring for the causal frontier and 60-second monitoring elsewhere.
