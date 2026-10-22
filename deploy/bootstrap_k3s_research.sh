#!/bin/bash
set -euo pipefail
install -d -m 700 /opt/banking-research
# Deadline is tied to launch time, not to when installation finishes.
cat > /etc/systemd/system/bank-research-deadline.service <<'UNIT'
[Unit]
Description=Approved disposable research deadline
[Service]
Type=oneshot
ExecStart=/sbin/poweroff
UNIT
cat > /etc/systemd/system/bank-research-deadline.timer <<'TIMER'
[Unit]
Description=Terminate research before approved maximum runtime
[Timer]
OnCalendar=2026-10-22 19:02:40 UTC
Persistent=true
AccuracySec=1s
Unit=bank-research-deadline.service
[Install]
WantedBy=timers.target
TIMER
systemctl daemon-reload
systemctl enable --now bank-research-deadline.timer
systemctl list-timers bank-research-deadline.timer --no-pager
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
