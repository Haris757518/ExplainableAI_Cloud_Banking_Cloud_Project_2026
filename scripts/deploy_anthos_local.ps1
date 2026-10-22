param([switch]$StorageVerified)
$ErrorActionPreference = 'Stop'
# Image pulls are forbidden until Docker's actual disk location is verified.
if (-not $StorageVerified) { throw 'Verify Docker disk image location is on D: before supplying -StorageVerified.' }
$context = (& kubectl config current-context).Trim()
if ($LASTEXITCODE -ne 0 -or $context -ne 'docker-desktop') { throw 'Only the local docker-desktop context is allowed.' }
$server = (& kubectl config view --minify -o 'jsonpath={.clusters[0].cluster.server}').Trim()
if ($server -notmatch '^https://(kubernetes\.docker\.internal|127\.0\.0\.1|localhost)(:\d+)?$') { throw "Unexpected Kubernetes API endpoint: $server" }
& docker info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker engine is not ready.' }
& kubectl --context docker-desktop get nodes
if ($LASTEXITCODE -ne 0) { throw 'Local Kubernetes is not ready.' }
$bundle = Join-Path $PSScriptRoot '..\deploy\anthos-prepared'
& kubectl --context docker-desktop apply -k $bundle
if ($LASTEXITCODE -ne 0) { throw 'Deployment failed.' }
& kubectl --context docker-desktop -n banking-probe-research wait --for=condition=Ready pod --all --timeout=600s
if ($LASTEXITCODE -ne 0) { throw 'Banking pods did not become ready. Inspect events before continuing.' }
Write-Output 'Ready for localhost access. Run: kubectl --context docker-desktop -n banking-probe-research port-forward --address 127.0.0.1 service/frontend 8080:80'
Write-Output 'No fault or load experiment has been started. Verify a transfer and its ledger record before research.'
