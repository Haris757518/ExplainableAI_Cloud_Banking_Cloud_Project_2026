> Updated authorization: the user approved local Docker Desktop and single-node Kubernetes on this Windows PC, with large files on D:. Setup is in progress. The earlier proposal below is retained as historical context. WSL 2.7.10 is now verified; Docker is not yet installed. AWS budget remains zero. See [current local protocol](LOCAL_COMPLETION_PROTOCOL.md).

# Banking workload deployment proposal

Status on 22 October 2026: preparation only. Approved incremental AWS budget is ₹0 and approved runtime for new compute is zero hours. Nothing in this document authorizes deployment.

## Existing infrastructure checks

AWS credentials previously authenticated and existing public-bank S3 storage was verified. The new read-only checks returned AccessDeniedException for EKS ListClusters and UnauthorizedOperation for EC2 DescribeInstances in us-east-1. This prevents an inventory of reusable compute. It does not prove that no instances or clusters exist. An authorized administrator can provide read-only discovery or identify a specifically approved host. Even reusing a host needs confirmation that CPU credits, disk, network and monitoring will not incur incremental charges.

No Docker, kubectl, kind, minikube or Helm command was found locally. WSL discovery returned access denied. Bank of Anthos was downloaded from its official repository at commit db35fea9fd090150e2398106aadb475576f80d94. Its development guide targets GKE and requires a suitable Kubernetes environment. The checked manifests request approximately 1.06 CPU and 2176 MiB memory in aggregate, before Kubernetes and operating-system overhead. Therefore a 2 GiB host is not a justified size for the full upstream stack.

## Cheapest next experiment

Use the existing instrumented local banking application without Kubernetes, operating only on disposable test accounts and isolated research storage. It already measures executed HTTP and SQL spans. Add explicit request arrivals, active requests, queue depth, process CPU deltas, completed transactions, worker limits and transaction-integrity checks. Run normal traffic first, freeze its baseline, then bounded high request arrivals. Record measurements rather than inventing CPU, queue or request values.

Required local resources: existing Python runtime, SQLite test ledger, loopback-only service ports, a bounded load-generator process and local telemetry disk. Suggested execution duration after operator approval: 30 seconds warmup, 60 seconds baseline, 60 seconds higher demand and 30 seconds observation, approximately three minutes. Allow 30–60 minutes engineering time to instrument and validate. Incremental AWS compute cost: ₹0 because no AWS compute, publication or storage operation is required. This would be a local banking workload study, not Bank of Anthos and not cloud telemetry. Whether demand actually creates CPU saturation must be measured; if it does not, the system must abstain from that driver.

## Future paid alternative requiring separate approval

A reduced instrumented banking application could run on one Linux VM with a local test database and no EKS, managed database, NAT gateway or load balancer. As an illustrative us-east-1 planning reference, AWS documents t3.small at US$0.0208 per hour. Two hours would be US$0.0416 for instance time alone. This is not a complete bill: EBS, IPv4 if used, CPU-credit mode, logs, metrics, data transfer and taxes can add charges. This size is proposed only for the reduced application, not the full Anthos stack. A bounded total budget and a current regional quote must be approved before launch.

EKS currently lists US$0.10 per cluster-hour for standard support, excluding worker compute and other resources. Two hours of control plane alone would be US$0.20. It adds no scientific necessity for the first reduced experiment and is not proposed under the current budget.

References checked 22 October 2026:

- AWS instance reference: https://docs.aws.amazon.com/prescriptive-guidance/latest/optimize-costs-microsoft-workloads/right-size-selection.html
- AWS EKS pricing: https://aws.amazon.com/eks/pricing/
- Bank of Anthos: https://github.com/GoogleCloudPlatform/bank-of-anthos

## Complete cleanup procedure for any later approved deployment

Before launch, save the exact experiment identifier, account/region, resource IDs, tags and cleanup deadline in an execution manifest. Restrict all actions to newly created resources with that identifier. Do not reuse or delete the existing public-bank bucket, importer metrics or unrelated account resources as part of cleanup.

1. Stop the experiment load generator, record its actual end time and collect transaction-integrity results.
2. Export raw observations, traces, experiment annotations and checksums to approved local storage. Keep inference measurements and annotations separate.
3. Stop experiment services. For local execution, terminate only the processes whose PIDs and creation times were recorded, release their ports and preserve the isolated research database. Remove only explicitly disposable work files after retention review.
4. For a future single-VM experiment, terminate the exact recorded instance ID. Verify termination. Delete only experiment-created EBS volumes or snapshots whose retention was not approved; verify that delete-on-termination actually applied.
5. Release any experiment-created Elastic IP, and remove only experiment-created network interfaces, security groups, key material or IAM roles when no longer attached. No new IAM privilege is implied by this proposal.
6. If Kubernetes is later approved, first delete experiment ingress/load-balancer services and verify associated load balancers are gone, then delete experiment workloads and volumes, worker nodes and finally the cluster. Retain an inventory until every chargeable resource is accounted for.
7. Remove only experiment-created log groups, alarms and dashboards after the retention decision. Stopping compute alone does not stop storage or retained log charges.
8. Use authorized read-only inventory to confirm no experiment resources remain. Save cleanup receipts and inspect billing after its reporting delay. Budget alerts are not a hard spending cap.

No cleanup of existing resources was executed because no new deployment occurred.
