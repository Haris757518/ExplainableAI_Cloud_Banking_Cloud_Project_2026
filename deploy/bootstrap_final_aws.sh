#!/bin/bash
set -euo pipefail
install -d -m 700 /opt/banking-research
curl -fsSL https://get.k3s.io -o /opt/banking-research/k3s-install.sh
sha256sum /opt/banking-research/k3s-install.sh > /opt/banking-research/k3s-installer.sha256
INSTALL_K3S_EXEC='server --disable traefik --disable servicelb --write-kubeconfig-mode 600' sh /opt/banking-research/k3s-install.sh
for attempt in $(seq 1 60); do
  if kubectl get nodes --no-headers 2>/dev/null | grep -q ' Ready '; then break; fi
  sleep 5
done
kubectl wait --for=condition=Ready node --all --timeout=120s
k3s --version
kubectl get nodes -o wide
free -m
df -h /var/lib/rancher/k3s
