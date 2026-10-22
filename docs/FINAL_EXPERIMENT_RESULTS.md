Revised implementation and measured results

22 October 2026

# Research scope

The application combines published digital bank performance measurements with independent cloud telemetry experiments. Its default AWS Banking Analytics mode examines historical API latency, availability and errors from actual banks. AI Research and Validation retains Alibaba, RCAEval and Microsoft experiments for their separate scientific tasks.

The implementation imported and validated 53,126 normalized banking records. Some records explicitly represent unavailable values. The new data path preserves original source snapshots, reporting dates and checksums. It never converts public statistics into private infrastructure telemetry.

## Main findings

The Monzo Payment Initiation analysis flags three deviations in its final evaluation period. The selected newer Starling Payment Initiation series has no flagged deviations. These outcomes are model findings without incident labels. The fresh Alibaba experiment finds lower reconstruction error for the feature model without graph edges. A graph advantage is therefore not established.

The historical AWS storage path is implemented and covered by failure and readback tests. Both banks now have verified S3 uploads. All four downloaded objects match their source checksums. The private bucket uses encryption and blocks public access. CloudWatch importer-health metrics have been read back successfully.

# Banking datasets and provenance

| Source | Period | Rows | Null values |
| --- | --- | --- | --- |
| Monzo | 2019-09-14 to 2026-06-30 | 24820 | 4967 |
| Starling | 2019-07-01 to 2026-06-30 | 28306 | 0 |

A normalized record retains bank, source name, date, service, metric, value, unit, frequency, origin, official URL, retrieval timestamp, record status, raw value and source checksum. Starling records also preserve the quarterly report filename and original field identifier. Latency uses milliseconds and availability, downtime and errors use percent.

## Monzo table validation

The official HTML supplies explicit daily dates across multiple years. Some tables advertise a Confirmation of Funds column but omit its daily cells. The importer records those cells as null. Three unsupported source values remain null with their original strings and dates in the validation manifest. Missing values never become zero or an inferred infrastructure measurement.

## Starling quarter validation

The initial server-rendered daily table has 92 day indices under a Q2 2026 heading. That quarter has 91 calendar days. The importer excludes that ambiguous table and uses the 28 separately named reports embedded by the official quarter selector. Each report passes an exact day-index and calendar-length check before conversion to dates. Dedicated and newer Open Banking reporting fields remain separate series.

## Storage and preservation

Every successful import writes a new generation containing normalized CSV and JSON plus a manifest. A current pointer changes only after validation and writing complete. Original HTML snapshots are content-addressed by SHA-256. Failed parsing retains the source snapshot and the previous validated generation. The original V1 checkout and prior research results remain available.

# Banking analysis methodology

Each bank, service and metric defines a separate series. Analysis sorts actual observed dates and excludes null targets. Earlier 60 percent of measured observations establish the median and median absolute deviation reference. The next 20 percent calibrate a one-sided threshold using the greater of a 3.5 standardized score and the calibration 99th percentile. The final 20 percent form the untouched evaluation period.

Low availability is adverse. High latency, downtime and error rates are adverse. A flagged date includes its observed value, reference, difference, standardized score, persistence and original measurement. Consecutive flags count only adjacent calendar days. The explanation states that infrastructure cause is unknown.

| Series | Train | Calibration | Test | Flags |
| --- | --- | --- | --- | --- |
| Monzo Payment Initiation | 1488 | 496 | 497 | 3 |
| Starling Payment Initiation | 273 | 91 | 92 | 0 |

## Forecast evaluation

The same held-out dates compare a fixed training-median reference with a persistence forecast. Persistence uses only the preceding recorded observation, including earlier evaluation observations when available. It predicts the next recorded point, whose calendar timing may be unknown across gaps. Neither method implies confirmed incidents.

| Series | Median MAE in ms | Persistence MAE in ms |
| --- | --- | --- |
| Monzo | 10.8048 | 5.5654 |
| Starling | 2.3587 | 0.9348 |

Monzo analysis covers the published Open Banking Payment Initiation series. Starling analysis covers Payment Initiation in the newer Open Banking category, starting in Q2 2025. Bank categories and reporting intervals differ, so these error figures do not rank the banks against one another.

# Independent GNN and benchmark evaluation

The fresh Alibaba experiment uses the bounded production trace and identical width-16 masked autoencoders. Recorded service calls supply graph relationships. Node and edge selection uses only calls through 175000 milliseconds, within the training period. The identity variant removes graph edges while preserving architecture, seed, features and chronological splits. Both train for 100 epochs. Validation selects the checkpoint and the held-out targets determine the final error.

| Alibaba model | Held out masked MSE |
| --- | --- |
| Recorded topology | 0.517233 |
| Identity adjacency | 0.000947 |
| Training mean reference | 1.050895 |

The identity model reconstructs the selected measured slice better. Reconstruction includes the current input features, so low reconstruction error is not a forecasting or root-cause accuracy score. Recorded directed calls are symmetrized by this model. Epoch loss histories and selected checkpoints are saved for both variants. Residual contributions and removal sensitivities explain model behavior without proving source-system causes.

## Microsoft anomaly detection

| Method | Precision | Recall | F1 | FP | FN |
| --- | --- | --- | --- | --- | --- |
| median_mad | 0.259 | 0.444 | 0.327 | 728 | 318 |
| forecast_residual | 0.068 | 0.572 | 0.122 | 4478 | 245 |

Microsoft figures above are preserved evaluations from the final 16 October research run. Threshold selection uses chronological validation labels and held-out scoring uses the dataset labels. The dashboard keeps these source-specific detection scores separate from bank deviations and Alibaba reconstruction.

# Root service evaluation and scientific limits

| RCAEval RE1 method | Cases | Top 1 | Top 3 | Coverage |
| --- | --- | --- | --- | --- |
| temporal | 30 | 0.233 | 0.600 | 1.000 |
| without_gate | 30 | 0.267 | 0.633 | 1.000 |
| evidence_gated | 30 | 0.600 | 0.867 | 1.000 |

The preserved RE1 study uses 150 recordings with a grouped 90 training, 30 validation and 30 test split. It reports service ranking separately from mechanism agreement. RE1 lacks recorded service-call topology. Per-fault results, mechanism confusion matrices and abstention coverage remain in the saved evidence and dashboard.

All 30 held-out RE1 cases showed pre-injection alerts in the preserved timing study. A zero conditional post-injection delay therefore cannot establish successful onset detection. Coverage and ranking scores do not resolve this false-positive limitation.

The existing five-case RE2 recorded-graph experiment reports Top-1 of 0.60 and Top-3 of 0.80 for both the identity and recorded graph variants. This small illustrative sample establishes no graph advantage or broad generalization. Broader RE2 evaluation remains future work.

## Claims supported by the implementation

The project uses genuine published digital bank measurements, recorded production microservice calls and controlled benchmark fault measurements. It implements a real GNN and reproducible comparisons. Its banking explanations identify measurable deviations and preserve supporting observations.

Public bank statistics provide no internal CPU, memory, SQL trace or service-call graph. They cannot identify a confirmed private bank AWS root cause. Bank anomaly precision and recall are unavailable because the imported bank series contain no verified incident labels. Neither GNN superiority nor complete banking fault coverage is established.

# Application architecture and verification

The application opens AWS Banking Analytics by default and has exactly two primary modes. The real bank page supports bank, metric, service and date selection, calendar-based history plots, CSV export, evidence-backed findings and provenance. AI Research and Validation retains Alibaba analysis and recorded Microsoft and RCAEval replay. Archived banking and AWS demos remain in source files without appearing as primary navigation.

## AWS historical storage path

An explicit import action can optionally upload the original HTML and normalized CSV to a configured S3 bucket. A separate current-time importer-health action can publish success and failure counts to CloudWatch. Historical bank values are never retimestamped as live CloudWatch data. S3 receipts require matching HEAD metadata and content length. CloudWatch records its write acknowledgement and the verified readback of ImportSuccess and ImportFailure metrics.

Set BANKING_DATASET_BUCKET and authorized AWS credentials before choosing writes. Without cloud access, import and analysis continue locally. The status API reads saved receipts and performs no cloud actions during a page load. Athena is optional and has not been provisioned. The executed deployment is in us-east-1 and its receipts are saved in results/real_banking/deployment.json.

## Verification

The complete Python regression suite passed 157 tests after the redesign. New tests cover official source parsing, known Monzo values, quarter validation, duplicate rejection, null handling, chronological leakage, forecast inputs, read-only API loads, partial cloud failure and storage verification. The production frontend build passed. Tests that need local client execution ran outside the restricted sandbox.

## Reproduction and source references

Start the application from this project directory with START_REDESIGN.ps1. Reproduce banking evaluations with python scripts/reproduce_real_banking.py. Reproduce the graph comparison with python scripts/run_graph_ablation.py --out results/new_graph_run --training-topology --epochs 100. Always choose a new research output directory.

https://monzo.com/service-information

https://www.starlingbank.com/current-account/service-information/api-performance/

https://github.com/alibaba/clusterdata/tree/master/cluster-trace-microservices-v2021

https://huggingface.co/datasets/phamquiluan/RCAEval

https://github.com/microsoft/cloud-monitoring-dataset
