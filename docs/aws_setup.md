# AWS Setup

The project supports `AWS_MODE=false` for local simulation and `AWS_MODE=true` for CloudWatch-backed analysis.

## Primary services

- Amazon EC2
- Amazon RDS
- Amazon CloudWatch

## Configuration

Copy `.env.example` to `.env` and configure:

```text
AWS_MODE=true
AWS_REGION=ap-south-1
EC2_INSTANCE_IDS=i-xxxxxxxxxxxxxxxxx
RDS_INSTANCE_IDS=your-db-instance-id
```

Use the normal AWS credential chain. Do not put access keys in the repository.

## What is collected

The adapter requests CloudWatch metrics that are available from the selected AWS namespaces, including EC2 CPU/network counters and RDS CPU/latency/IOPS metrics.

Some telemetry fields used by the synthetic simulator are not standard CloudWatch metrics without additional agents/services. Those fields remain baseline-valued and are explicitly marked as not observed. The system must not represent them as real AWS measurements.

## Local development

Leave `AWS_MODE=false` until valid AWS resources and credentials are available.
