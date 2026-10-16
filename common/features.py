from __future__ import annotations
import numpy as np
from .schema import AnalysisSample

TELEMETRY_FEATURES = [
    "cpu_percent", "memory_percent", "network_in_mbps", "network_out_mbps",
    "latency_ms", "error_rate", "request_rate", "db_latency_ms", "disk_io"
]
TRANSACTION_FEATURES = [
    "transaction_upi", "transaction_transfer", "transaction_card",
    "transaction_balance", "transaction_bill"
]
FEATURE_NAMES = TELEMETRY_FEATURES + TRANSACTION_FEATURES + [
    "is_ec2", "is_rds", "transaction_relevance", "path_depth", "time_sin", "time_cos"
]

TX_FLAGS = {
    "UPI_PAYMENT": [1, 0, 0, 0, 0],
    "FUND_TRANSFER": [0, 1, 0, 0, 0],
    "CARD_PAYMENT": [0, 0, 1, 0, 0],
    "BALANCE_INQUIRY": [0, 0, 0, 1, 0],
    "BILL_PAYMENT": [0, 0, 0, 0, 1],
    "ALIBABA_BENCHMARK": [0, 0, 0, 0, 0],
}

def node_feature_matrix(sample: AnalysisSample) -> tuple[np.ndarray, list[str]]:
    tx_flags = TX_FLAGS[sample.transaction.type]
    telemetry = {t.node_id: t for t in sample.telemetry}
    path = sample.transaction.path or [e.source for e in sample.edges]
    path_index = {node_id: idx for idx, node_id in enumerate(path)}
    rows = []
    for node in sample.nodes:
        t = telemetry[node.id]
        if any(getattr(t, key) is None for key in TELEMETRY_FEATURES):
            raise ValueError("GNN requires complete measured features; missing observations cannot be imputed as normal.")
        relevance = 1.0 if node.id in path else 0.15
        depth = path_index.get(node.id, len(path)) / max(1, len(path))
        angle = (sample.sequence_index % 8) / 8.0 * 2.0 * np.pi
        row = [
            t.cpu_percent / 100.0,
            t.memory_percent / 100.0,
            min(t.network_in_mbps / 100.0, 5.0),
            min(t.network_out_mbps / 100.0, 5.0),
            min(t.latency_ms / 1000.0, 5.0),
            t.error_rate,
            min(t.request_rate / 500.0, 5.0),
            min(t.db_latency_ms / 1000.0, 5.0),
            min(t.disk_io / 1000.0, 5.0),
            *tx_flags,
            float(node.type == "ec2"),
            float(node.type == "rds"),
            relevance,
            depth,
            float(np.sin(angle)),
            float(np.cos(angle)),
        ]
        rows.append(row)
    return np.asarray(rows, dtype=np.float32), FEATURE_NAMES
