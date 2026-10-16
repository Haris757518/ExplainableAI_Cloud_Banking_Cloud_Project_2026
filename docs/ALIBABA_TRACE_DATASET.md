# Alibaba Microservices Trace v2021

## Why this dataset is being added

The project currently includes a synthetic digital-banking telemetry generator for controlled anomaly experiments. For research review and external validity, this project now also supports the **Alibaba Cluster Trace — Microservices v2021** dataset.

Alibaba's official clusterdata repository describes this trace as production-cluster data containing 20,000+ microservices over 12 hours, including call dependencies, response time, and call-rate/runtime metrics. The associated SoCC 2021 paper is *Characterizing Microservice Dependency and Performance: Alibaba Trace Analysis* by Luo et al. ([official dataset](https://github.com/alibaba/clusterdata), [paper](https://acmsocc.org/2021/acm-dl.html)).

The dataset is **not banking data**. Do not describe it as banking telemetry. In this project it is used for cloud/microservice performance and graph benchmarking; a banking transaction context may be added as a clearly labeled research overlay or synthetic experiment.

## Dataset structure

The released trace has four main parts:

- `Node`: bare-metal node CPU/memory utilization.
- `MSResource`: microservice/container CPU/memory utilization.
- `MSRTQps`: microservice call rates and response times.
- `MSCallGraph`: sampled microservice call graphs with upstream/downstream services and response time.

The official distribution is very large, so **do not download the entire dataset for tomorrow's review**. The provided fetch script downloads a selected call-graph archive and optionally selected metric archives.

## Download a manageable subset

The upstream repository provides `fetchData.sh`, which enumerates the released archives. This project contains a Python subset downloader that defaults to one call-graph archive:

```powershell
python scripts/fetch_alibaba_subset.py --out dataset/raw/alibaba_microservices_v2021
```

For performance metrics, add:

```powershell
python scripts/fetch_alibaba_subset.py --out dataset/raw/alibaba_microservices_v2021 --include-resource --include-rtqps
```

Only enable `--include-node` when you specifically need bare-metal node metrics.

Because the upstream download may require an access/survey step and the archives can be large, confirm access and available disk space before downloading. The official repository states that the full release contains multi-gigabyte archives across the four parts.

## Import a slice

After obtaining/extracting the selected archives:

```powershell
python scripts/import_alibaba_trace.py `
  --root dataset/raw/alibaba_microservices_v2021 `
  --max-services 40 `
  --max-edges 80 `
  --out dataset/processed/alibaba_snapshot.json
```

You can target a specific trace ID if known:

```powershell
python scripts/import_alibaba_trace.py --root dataset/raw/alibaba_microservices_v2021 --trace-id TRACE_ID
```

The adapter produces a compact research snapshot with:

- microservice graph nodes
- `CALLS` edges
- aggregated edge weights
- CPU/memory metrics when `MSResource` is present
- response-time/call-rate metrics when `MSRTQps` is present
- explicit `source="alibaba_microservices_v2021"`

## How this fits our research

Use the Alibaba trace for:

1. real production microservice graph topology
2. graph structure statistics
3. real runtime performance distributions
4. benchmark evaluation of graph encoders and temporal aggregation

Do **not** use its raw data as supervised banking-anomaly labels because the dataset is not labeled as digital-banking failures.

For controlled anomaly/RCA evaluation, use a separate experiment in which anomalies are injected into an untouched Alibaba trace slice and the injected intervention is recorded as the ground truth. Report that as **synthetic intervention on a real production trace**, not as an observed failure label from Alibaba.

## Tomorrow's review wording

A safe statement is:

> "We use the Alibaba Microservices Trace v2021, a production-cluster trace released with the SoCC 2021 Alibaba Trace Analysis paper, as an external cloud/microservice benchmark. We retain our synthetic banking workload separately for controlled transaction-conditioned anomaly experiments."

## Citation

```bibtex
@inproceedings{luo2021characterizing,
  title={Characterizing Microservice Dependency and Performance: Alibaba Trace Analysis},
  author={Luo, Shutian and Xu, Huanle and Lu, Chengzhi and Ye, Kejiang and Xu, Guoyao and Zhang, Liping and Ding, Yu and He, Jian and Xu, Chengzhong},
  booktitle={Proceedings of the ACM Symposium on Cloud Computing},
  pages={412--426},
  year={2021},
  doi={10.1145/3472883.3487003}
}
```
