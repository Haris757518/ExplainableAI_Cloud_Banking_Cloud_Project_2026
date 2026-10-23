# Banking investigation report

Read-only replay of retained measurements

3,025 submitted requests; 3,025 matching ledger records.

## Payments slowed; the deeper cause is unresolved

What happened: The 95th-percentile recorded request duration was 8.05 seconds, compared with 0.47 seconds in the reference window. Durations include timed-out requests; they are not all successful payment response times.

Where: Payment processing path

Why: Response times rose beyond the earlier reference.

Deeper explanation: The available measurements do not distinguish one cause. Slow payments alone do not prove a database, processor or network fault.

Action: Collect queue depth, backend request traces and per-request processing measurements before choosing a corrective action.

Prevention: Improve coverage of the missing measurements.

Recovery: Later windows returned close to the earlier payment speed. This does not by itself prove balance correctness or a permanent fix.

Evidence status: Supported by recorded measurements; not exclusive causal proof

## Payments slowed while processing capacity fell

What happened: The 95th-percentile recorded request duration was 8.06 seconds, compared with 0.47 seconds in the reference window. Durations include timed-out requests; they are not all successful payment response times.

Where: Payment-writing service

Why: The service was allowed to use much less processor time, so payments took longer to finish.

Deeper explanation: The recorded processor allowance fell from 0.5 to 0.02 CPU cores. This supports a capacity restriction. The measurements do not explain who changed it or why.

Action: Restore the previous processor allowance, then check payment speed and reconcile balances before declaring recovery.

Prevention: Keep minimum capacity settings under review and test configuration changes before applying them.

Recovery: Later windows returned close to the earlier payment speed. This does not by itself prove balance correctness or a permanent fix.

Evidence status: Supported by recorded measurements; not exclusive causal proof

## Payments waited for the database

What happened: The 95th-percentile recorded request duration was 8.07 seconds, compared with 0.47 seconds in the reference window. Durations include timed-out requests; they are not all successful payment response times.

Where: Transaction database

Why: Database sessions were blocked while payments were slow.

Deeper explanation: A database lock prevented other sessions from proceeding. The recording contains both waiting sessions and their lock waits. The transaction owner and business reason require further investigation.

Action: Identify the blocking transaction and its owner. Allow it to finish, or have an authorized operator cancel it safely; then check balances and payment speed.

Prevention: Keep transactions short and monitor long-running transactions and lock waits.

Recovery: Later windows returned close to the earlier payment speed. This does not by itself prove balance correctness or a permanent fix.

Evidence status: Supported by recorded measurements; not exclusive causal proof

## More payment requests arrived and responses slowed

What happened: The 95th-percentile recorded request duration was 3.34 seconds, compared with 0.47 seconds in the reference window. Durations include timed-out requests; they are not all successful payment response times.

Where: Payment processing path

Why: The recorded arrival rate increased while payment response times rose.

Deeper explanation: Higher demand is a supported contributor. The recording does not measure admission queues or enough per-request work to prove the exact internal bottleneck.

Action: Control the incoming rate or add verified capacity, then measure payment speed and check that transfers appear once in the ledger.

Prevention: Load-test expected peaks and define safe traffic limits using measured capacity.

Recovery: Later windows returned close to the earlier payment speed. This does not by itself prove balance correctness or a permanent fix.

Evidence status: Supported by recorded measurements; not exclusive causal proof

## The displayed balance missed a committed transfer

What happened: The controlled test produced a 17-cent difference between the displayed balance and the ledger.

Where: Balance-reading service

Why: A transfer with a higher number became visible before an earlier transfer finished.

Deeper explanation: The balance updater remembers the highest transaction number it has seen. If that transfer finishes first, an earlier-numbered transfer that finishes later can be skipped. The controlled test reproduced a missed transfer; it does not prove that every earlier balance difference had this cause.

Action: The corrected balance and history readers now read committed ledger records directly, so they do not depend on the order in which transaction numbers finish. The code was deployed and tested in the isolated AWS application.

Prevention: Keep the commit-order and restart regression tests. Monitor database load because authoritative reads perform more database work than cached reads.

Recovery: The original readers failed all three new commit-order trials. The corrected readers passed all three: both balances matched the ledger, and each tested transfer appeared once in both histories. The same checks passed after restarting the readers. This verifies the implemented correction within these tests.

Evidence status: Reproduced in an investigator-assisted controlled test

## Limits

- The reference is the first 60 seconds; alert threshold is three times its 95th-percentile response time. This is a demo rule, not a calibrated production SLO.
- One executed workload; no independent banking test-set accuracy or novel-method advantage is established.
- Payment acknowledgement flags were excluded because the original collector parsed them incorrectly. Ledger matching does not establish what each caller saw.
- Backend and SQL traces, admission queue depth and per-request processor attribution are missing.
- Diagnostic evidence is separated from intervention labels. Findings use only measurements available by each window end. Final recovery uses separately identified later evidence.

Banking GNNs have been trained and evaluated. Their symptom rankings are retained separately from evidence-guided localization. See Research and Validation for results and limits.

## Implemented correction verification

The original readers were incorrect in 3 of 3 controlled commit-order trials. The corrected readers passed 3 of 3. Both account balances matched the ledger after restart, and the tested transfers remained present once in both histories. Deployed build hashes matched the validated code.

Implemented code verified in these repeated AWS tests; production capacity and universal correctness are not certified.

## Separate later AWS validation

The later run submitted 8,475 requests, with 8,475 matching ledger records. Callers received 6,946 recorded success acknowledgements; 1,505 outcomes were uncertain. Ledger presence and caller acknowledgement are separate checks.

Another 24 responses were not classified as successful acknowledgements.

The table counts fixed CPU and database fault checkpoints in this later workload. It does not change the source of the incident explanations above.

| Model variant | Seed | GNN service ranking correct | Evidence-guided service localization correct | Fault checkpoints detected |
| --- | --- | --- | --- | --- |
| graph | 42 | 3 of 6 | 6 of 6 | 6 of 6 |
| graph | 43 | 3 of 6 | 6 of 6 | 6 of 6 |
| graph | 44 | 3 of 6 | 6 of 6 | 6 of 6 |
| identity | 42 | 0 of 6 | 6 of 6 | 2 of 6 |
| identity | 43 | 0 of 6 | 6 of 6 | 1 of 6 |
| identity | 44 | 0 of 6 | 6 of 6 | 6 of 6 |

- Six controlled CPU/database repetitions in one new workload on one AWS host; not six independent applications or infrastructures.
- The revision was frozen before this workload. GNNs are still trained independently on its normal prefix; cross-recording transfer is not claimed.
- Graph and identity variants share the same direct-evidence rules; any improvement from those rules does not establish graph superiority.
- Higher traffic is a load condition, not automatically a fault. Its two repetitions are retained but excluded from injected root-service accuracy.
- The corrective code uses authoritative reads and may increase database work. Demonstrated correctness under these tests is not universal production certification.
