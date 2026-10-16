# Architecture

```text
Digital Banking Transaction
           |
           v
Transaction Context
           |
           v
Business-to-Infrastructure Graph
      /                  \
     v                    v
AWS CloudWatch        Simulation
EC2 / RDS              Telemetry
      \                    /
       +--------+---------+
                |
                v
         GNN / Temporal GNN
                |
                v
         Anomaly Detection
                |
                v
    Transaction-Conditioned RCA
                |
                v
          Causal Frontier
                |
                v
         Adaptive Telemetry
                |
                v
           Re-analysis
                |
                v
           XAI Evidence
                |
                v
             FastAPI
                |
                v
            Dashboard
```

The current baseline is deliberately lightweight. The architecture permits replacement of the baseline GCN with a temporal GNN without changing the telemetry schema, RCA contract, or API.
