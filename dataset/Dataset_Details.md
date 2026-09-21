# Dataset Details

The primary development dataset is synthetic digital-banking cloud telemetry generated with a fixed graph and controlled anomaly scenarios. This makes the graph labels reproducible and avoids presenting public cluster traces as if they were banking telemetry.

Scenarios: NORMAL, CPU_SPIKE, DATABASE_LATENCY, SERVICE_OVERLOAD, NETWORK_DEGRADATION, CASCADING_FAILURE.

AWS CloudWatch telemetry can later be collected with the same canonical schema.
