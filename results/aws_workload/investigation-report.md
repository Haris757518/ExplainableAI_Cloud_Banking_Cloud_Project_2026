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

Action: Rebuild the displayed balances from the ledger and compare both accounts with their recorded transfers. This temporary recovery action was completed in the isolated demo.

Prevention: Change the updater so it processes every completed transfer, even when transfers finish out of number order. Test reversed completion order, restarts and repeated delivery before releasing the fix.

Recovery: After resynchronization, both account balances matched the ledger, three new transfers each appeared once in the ledger and history, and three balance reads succeeded with no blocked database sessions. A permanent application fix has not been implemented.

Evidence status: Reproduced in an investigator-assisted controlled test

## Limits

- The reference is the first 60 seconds; alert threshold is three times its 95th-percentile response time. This is a demo rule, not a calibrated production SLO.
- One executed workload; no independent banking test-set accuracy or novel-method advantage is established.
- Payment acknowledgement flags were excluded because the original collector parsed them incorrectly. Ledger matching does not establish what each caller saw.
- Backend and SQL traces, admission queue depth and per-request processor attribution are missing.
- Diagnostic evidence is separated from intervention labels. Findings use only measurements available by each window end. Final recovery uses separately identified later evidence.

Transparent measured-signature rules. No banking-domain GNN is validated; separate RE2 model results remain in Research & Validation.