# Build Status — Research V1 + AWS Ready

## Existing research pipeline

- Synthetic baseline GCN, temporal analysis, RCA, XAI, counterfactual evidence, TC-CFAO and adaptive re-analysis remain intact.
- The existing simulation dashboard remains available.

## New AWS integration

- Read-only AWS credential/status endpoint.
- Dynamic EC2 and RDS resource discovery.
- Batched CloudWatch `GetMetricData` adapter.
- EC2 metrics: CPUUtilization, NetworkIn, NetworkOut, DiskReadOps, DiskWriteOps.
- RDS metrics: CPUUtilization, DatabaseConnections, ReadLatency, WriteLatency, ReadIOPS, WriteIOPS, FreeableMemory, FreeStorageSpace, NetworkReceiveThroughput, NetworkTransmitThroughput.
- Explicit telemetry provenance (`aws_cloudwatch`).
- AWS graph constructed from discovered EC2/RDS resource IDs plus a logical Payment Service application node.
- Optional resource mapping by AWS tags and `configs/aws_mapping.json`.
- New endpoints: `/api/aws/status`, `/api/aws/resources`, `/api/aws/collect`, `/api/aws/analyze`.
- Frontend now has explicit `LOCAL SIMULATION` vs `AWS LIVE` modes and displays AWS resource counts/source.
- Graph no longer hardcodes the simulation node IDs in the visual layout; it lays out nodes by graph layer and labels relationships.

## Research integrity notes

- No fake AWS resources are marked as discovered.
- Native EC2/RDS CloudWatch resolution is not falsely described as 5-second telemetry.
- TC-CFAO's focused resolution remains a policy for high-resolution/custom/application telemetry or controlled simulation unless a real high-resolution data source is implemented.

## Live validation status

Actual AWS calls still need to be run from the user's AWS Academy environment because credentials/resources are not available in this build environment.
