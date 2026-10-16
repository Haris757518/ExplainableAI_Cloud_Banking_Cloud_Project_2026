# AWS Integration

This directory contains the read-only AWS integration layer.

- `discovery.py` ?" EC2/RDS discovery and credential status checks.
- `cloudwatch_adapter.py` ?" batched CloudWatch `GetMetricData` collection.
- `normalizer.py` ?" converts AWS observations into the project's canonical graph/telemetry schema.
- `mapping.py` ?" optional JSON/tag mapping from logical banking services to AWS resources.

No module creates, modifies, or deletes AWS resources.
