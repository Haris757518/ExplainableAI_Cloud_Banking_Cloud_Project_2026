# Published banking data provenance

The banking dashboard reads public aggregated bank service measurements. It contains no customer transactions or private bank infrastructure telemetry.

## Official sources

- Monzo: https://monzo.com/service-information
- Starling: https://www.starlingbank.com/current-account/service-information/api-performance/
- Alibaba: https://github.com/alibaba/clusterdata/tree/master/cluster-trace-microservices-v2021
- RCAEval: https://huggingface.co/datasets/phamquiluan/RCAEval
- Microsoft: https://github.com/microsoft/cloud-monitoring-dataset

Raw HTML snapshots, normalized JSON/CSV and manifests are under `results/real_banking`. Current manifest pointers select complete validated import generations. Snapshots use SHA-256 filenames. Each row retains its original value, retrieval time, source URL and snapshot checksum. Starling rows additionally retain report and field identifiers. CSV is the supported normalized historical interchange format.

## Source discrepancies

Monzo advertises CBPII columns in some daily tables while omitting their cells. These become explicit nulls, never invented observations. Three malformed source values are quarantined as null with `unsupported_value_or_unit` status. The manifest lists their dates and original strings. Missing dates are checked separately from missing cell values.

Starling's initial server-rendered table has 92 day indices beneath a Q2 2026 heading, although that quarter has 91 days. The importer excludes that table. The official page embeds 28 separately named reports for the quarter selector. Their filenames specify the reporting period, and each report's day indices match its quarter calendar length. Dates derive from those validated identifiers. Dedicated and newer Open Banking reporting categories remain separate series.

The imports contain Monzo history from 2019-09-14 through 2026-06-30 and Starling history from 2019-07-01 through 2026-06-30. An import date is not a measurement date. These records must never be presented as current live telemetry.

## Reproduction

Run `python scripts/reproduce_real_banking.py` from the project directory to reproduce banking evaluations without network access. To refresh official snapshots, use the dashboard's explicit import action. Ordinary page loads read local data only. Historical source revisions are separate import generations.

Banking analysis uses the first 60% of measured dates for its reference, the next 20% for threshold calibration and the final 20% for evaluation. Nulls are excluded from model targets. Calibration and test data never alter the training reference. Graph reconstruction and fault localization belong to the independent research datasets.

## AWS path

Set `BANKING_DATASET_BUCKET` and an authorized AWS credential/region configuration before opting into writes. Use a dedicated bucket prefix `public-bank-history/`. Required storage actions are `s3:PutObject` and `s3:GetObject` on that prefix for upload and HEAD verification. Import health uses `cloudwatch:PutMetricData`, restricted to namespace `PublicBankDataset/ImportHealth` where IAM policy permits.

S3 status records HEAD metadata and length verification. CloudWatch status records API acknowledgement and explicitly discloses that readback was not verified. No historical bank measurements are republished as current CloudWatch measurements. Athena remains optional and is not provisioned. Live AWS execution is now verified. Four S3 objects passed downloaded SHA-256 checks. The private encrypted bucket and CloudWatch readback receipts are saved in results/real_banking/deployment.json.

## Archived work

The original V1 checkout is unchanged. The copied application retains BankingDashboard, BankingResults, AwsBankingPanel, AwsDemoPanel, legacy endpoints, research checkpoints and previous result folders. These are archived experiments, excluded from the new primary banking page and its evidence. Runtime SQLite databases and secrets were deliberately not copied; the redesigned application initializes its own runtime database.
