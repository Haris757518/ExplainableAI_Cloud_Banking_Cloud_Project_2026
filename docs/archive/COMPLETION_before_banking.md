# Current handover: Research V4

See [the full implementation report and faculty walkthrough](docs/ROOT_CAUSE_V4.md). The new version adds mechanism evidence, sequential visual investigation, real RE2 trace graphs and independent mechanism evaluation. Earlier handover notes are preserved below.

---

# Research platform implementation — 16 October 2026

Official title: **Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks**.

The integrated application is running at http://127.0.0.1:8000/ .

See [the full technical handover](docs/RESEARCH_PLATFORM_V3.md) for implemented features, exact commands, original data provenance, file inventory, numerical results, demonstration steps and limitations. Verified research references are in [RESEARCH_FOUNDATION.md](docs/RESEARCH_FOUNDATION.md). Baseline/checkpoint information is in [MASTER_RESEARCH_BASELINE.json](docs/MASTER_RESEARCH_BASELINE.json).

Current sources: existing Alibaba traces, all 60 official Microsoft labelled series, 150 official RCAEval RE1 recordings, and read-only AWS. Current checks: 63 backend tests passed, frontend build passed, seven browser tests passed in the final acceptance run. No cloud faults/configuration changes were executed.

Primary held-out RCA result: Top-1 60.0%, Top-3 86.7%, MRR 0.7445 on 30 grouped test cases. Microsoft median/MAD F1 is 0.3269 on the common 45,017 valid held-out points. These results are exploratory and source-specific. The graph model did not beat the feature-only reconstruction baseline. All held-out RCA recordings had pre-injection alerts in the separate any-resource timing evaluation, so zero conditional delay is not evidence of reliable operational alerting. Forecast intervals are not guaranteed and can under-cover.

Current implementation and artifacts remain local; no new GitHub push was performed.

**Current AWS blocker:** authentication succeeds, but final resource reads are denied: `ec2:DescribeInstances` (`UnauthorizedOperation`) and `rds:DescribeDBInstances` (`AccessDenied`). Earlier live validation passed; current collection cannot be verified until the active lab role/session regains read access. The application reports this error and does not substitute a healthy status.
