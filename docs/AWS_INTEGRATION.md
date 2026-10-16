# AWS Integration

The project supports two explicit modes:

- **LOCAL SIMULATION** — deterministic synthetic banking/cloud telemetry. No AWS credentials required.
- **AWS LIVE** — read-only discovery of visible EC2/RDS resources plus CloudWatch `GetMetricData` collection. No AWS resources are created, changed, or deleted by the app.

## 1. AWS Academy access

Use the AWS Academy LMS account provided by your college. Open the course containing the **Learner Lab**, enter **Modules → Learner Lab**, accept the lab terms when prompted, then select **Start Lab**. When the lab becomes ready, use the **AWS** link to open the temporary AWS account. The lab exposes a temporary AWS account while the lab session is active.

## 2. Local credentials

Do not paste AWS secrets into source code or Git.

For AWS Academy temporary credentials, use the credential method shown by your Learner Lab for your course. The application uses the standard boto3 credential chain and also supports `AWS_PROFILE`.

Recommended environment variables when your lab gives temporary credentials:

```text
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
AWS_DEFAULT_REGION=ap-south-1
```

Or configure a profile and set:

```text
AWS_PROFILE=your-profile
AWS_REGION=ap-south-1
```

## 3. Project configuration

Copy `.env.example` to `.env` and set:

```text
AWS_MODE=true
AWS_REGION=ap-south-1
EC2_INSTANCE_IDS=
RDS_INSTANCE_IDS=
AWS_TRANSACTION_TYPE=UPI_PAYMENT
AWS_MAPPING_FILE=configs/aws_mapping.json
CLOUDWATCH_LOOKBACK_MINUTES=15
CLOUDWATCH_PERIOD_SECONDS=60
```

Leaving EC2/RDS ID filters blank allows read-only discovery of visible resources in the selected region. Populate them to narrow the analysis to specific resources.

## 4. Resource mapping

`configs/aws_mapping.json` can explicitly map the logical `payment-service` and `banking-db` nodes to EC2/RDS IDs. AWS tags are also used when present. A small example is provided in `configs/aws_mapping.example.json`.

The graph distinguishes logical application nodes from actual AWS resource nodes. It never marks an invented resource as discovered AWS infrastructure.

## 5. CloudWatch telemetry

The adapter queries CloudWatch with `GetMetricData` over the configured lookback window.

EC2 metrics:

- CPUUtilization
- NetworkIn
- NetworkOut
- DiskReadOps
- DiskWriteOps

RDS metrics:

- CPUUtilization
- DatabaseConnections
- ReadLatency
- WriteLatency
- ReadIOPS
- WriteIOPS
- FreeableMemory
- FreeStorageSpace
- NetworkReceiveThroughput
- NetworkTransmitThroughput

Each observation is marked with `source=aws_cloudwatch`, the period, and the actual metrics observed.

## 6. Graph construction

AWS mode builds a business-to-infrastructure graph from:

```text
Transaction
   ↓
Logical banking service
   ↓
EC2 compute resource
   ↓
RDS data resource
```

Relationships are explicit (`hosts`, `reads_writes`) rather than arbitrary percentages. The UI shows actual AWS resource IDs/names and anomaly scores separately.

## 7. Analysis pipeline

```text
AWS discovery
   ↓
CloudWatch telemetry
   ↓
Telemetry normalization
   ↓
Business-to-infrastructure graph
   ↓
GNN
   ↓
Anomaly
   ↓
Affected nodes
   ↓
Transaction-conditioned RCA
   ↓
XAI
   ↓
Causal frontier
   ↓
Adaptive observability
   ↓
Re-analysis
```

The existing `ai_engine.analyze(graph_data)` interface remains unchanged.

## 8. TC-CFAO and metric resolution

Native EC2/RDS CloudWatch metrics are queried at their configured real period (60 seconds by default). The project does **not** claim that native CloudWatch EC2/RDS metrics are magically available every 5 seconds.

The 5-second figure in TC-CFAO remains the proposed focused/high-resolution policy for application/custom telemetry or a later high-resolution collection channel. Any experiment using a simulated 5-second policy must be labeled as such.

## 9. Endpoints

- `GET /api/aws/status`
- `GET /api/aws/resources`
- `POST /api/aws/collect`
- `POST /api/aws/analyze?transaction_type=UPI_PAYMENT`

All AWS endpoints are read-only.

## 10. Troubleshooting

If `/api/aws/status` reports disconnected, verify the temporary Learner Lab session is active, the credentials/profile are available to the Python process, and the region is correct.

If resource discovery works but AWS analysis reports no CloudWatch datapoints, check that the selected resources are emitting the requested metrics and that the lookback window covers a period when the resources were running.
