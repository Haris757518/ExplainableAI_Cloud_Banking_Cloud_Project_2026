# Banking investigation demo

Open the dashboard and select **Run banking investigation**. The current server is at http://127.0.0.1:8012/.

The application checks the saved evidence, compares later request durations with the first 60 seconds, and displays findings from the measured processor allowance, database lock waits and incoming request rate. Choose a finding to read what happened, where, why, the deeper explanation, the action and the recovery result. Download the readable report from the same screen.

## Findings from the executed AWS workload

- Processing allowance fell from 0.5 to 0.02 CPU cores while payments slowed. The recording supports a capacity restriction; the reason for the configuration change is not inferred from measurements.
- Database sessions waited behind a lock. The measurements establish blocking, but do not identify its business justification.
- Incoming requests increased and response times rose. Missing queue and per-request work measurements prevent an exclusive internal bottleneck claim.
- A separate investigator-assisted commit-order test reproduced a 17-cent displayed-balance discrepancy. A later-numbered transfer committed first; the transaction-number cursor could move past an earlier transfer that committed later.

The last finding has a stronger controlled mechanism test. It was not discovered autonomously by a GNN. It does not prove that every earlier discrepancy had the same cause.

## Recovery

The affected readers were resynchronized in the isolated demo. Later evidence records two matching account balances, three distinct newly verified transfers, three successful balance reads and no blocked database sessions. This establishes the recorded temporary recovery, not a permanent software fix. The proposed permanent change needs its own implementation and concurrency validation before deployment.

The 3,025 requests match 3,025 ledger records in this isolated run. The original acknowledgement parser had a defect; its success/failure flags are excluded. Timeouts are included in recorded request durations and are not treated as successful response times.

## Reproduce without AWS

From the project directory, run `python scripts/replay_banking_investigation.py`. It verifies every bundled evidence file against its retained checksum, writes the readable Markdown report and a machine-readable companion, and makes no network calls. `results/aws_workload/replay/manifest.json` records the source archive checksum. The original archive and final database backup remain on D:.

To start the application after closing it, run `START_REDESIGN.ps1`; its default port is 8000. Use `START_REDESIGN.ps1 -Port 8012` to match the current demo address. Only one server should own the chosen port.

## Research status

Banking replay uses transparent measured-signature rules. It does not apply RE2 models to banking data or claim validated banking GNN accuracy. The existing GNN and PROBE-XAI comparison remains in **Research & Validation**, with its independent benchmark provenance and limitations. Existing results do not establish a GNN advantage or a novel-method advantage. These research claims remain unfinished and must not be presented as proven by the demo.

The AWS research instance was terminated and its root volume deleted. The dashboard uses retained measurements and does not provide live cloud health or start new AWS resources.

## Verification

The project regression suite passed 188 tests, and four browser acceptance tests passed for the new banking replay and existing research screens. Checks cover altered evidence, unavailable measurements, overlapping explanations, completed-observation timing, inconsistent balances, earlier recovery evidence and duplicate recovery receipts.
