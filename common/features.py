from __future__ import annotations
import numpy as np
from .schema import AnalysisSample

FEATURE_NAMES = [
    "cpu_percent", "memory_percent", "network_in_mbps", "network_out_mbps",
    "latency_ms", "error_rate", "request_rate", "db_latency_ms", "disk_io",
    "transaction_upi", "transaction_transfer", "transaction_card",
    "transaction_balance", "transaction_bill", "is_ec2", "is_rds"
]

def node_feature_matrix(sample: AnalysisSample) -> tuple[np.ndarray, list[str]]:
    tx = sample.transaction.type
    tx_flags = {
        "UPI_PAYMENT": [1,0,0,0,0],
        "FUND_TRANSFER": [0,1,0,0,0],
        "CARD_PAYMENT": [0,0,1,0,0],
        "BALANCE_INQUIRY": [0,0,0,1,0],
        "BILL_PAYMENT": [0,0,0,0,1],
    }[tx]
    telemetry = {t.node_id: t for t in sample.telemetry}
    rows = []
    for node in sample.nodes:
        t = telemetry[node.id]
        row = [
            t.cpu_percent / 100.0,
            t.memory_percent / 100.0,
            t.network_in_mbps / 100.0,
            t.network_out_mbps / 100.0,
            min(t.latency_ms / 1000.0, 5.0),
            t.error_rate,
            min(t.request_rate / 500.0, 5.0),
            min(t.db_latency_ms / 1000.0, 5.0),
            min(t.disk_io / 1000.0, 5.0),
            *tx_flags,
            float(node.type == "ec2"),
            float(node.type == "rds"),
        ]
        rows.append(row)
    return np.asarray(rows, dtype=np.float32), FEATURE_NAMES
