# Dataset Details

For this project, we will utilize cloud performance datasets and simulated cloud monitoring metrics suitable for Graph Neural Network-based anomaly detection. 

## Primary Data Sources

1. **Google Cluster Dataset / Alibaba Cluster Trace**: 
   These publicly available datasets contain highly detailed logs of job scheduling, resource usage, and machine constraints within large-scale distributed systems, serving as excellent foundational data for topological modeling.

2. **Azure VM Performance Dataset**:
   Provides extensive metrics regarding virtual machine performance, network latency, and throughput, useful for training time-series components of our models.

3. **Synthetic Digital Banking Cloud Logs**:
   To specifically model digital banking scenarios, we will generate synthetic datasets that simulate financial transaction loads, API Gateway request rates, and specific banking microservice behaviors (e.g., payment processing, account verification).

## Data Features

The dataset will include the following key metrics:
- **Compute Metrics**: CPU Utilization, Memory Usage, Disk I/O.
- **Network Metrics**: Network In/Out, Latency, Packet Loss, Request Rates.
- **Topology Information**: Source/Destination IP mappings, Service Dependency Graphs, API Call Traces.
- **Application Logs**: Error rates, Transaction processing times, Database Query Execution times.

## Preprocessing
Data will be aggregated, normalized, and transformed into graph structures, where nodes represent cloud instances/services and edges represent data flow or dependency links, annotated with their respective performance metrics.
