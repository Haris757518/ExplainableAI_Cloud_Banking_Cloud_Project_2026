from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import random
from pathlib import Path
from typing import Iterable
from common.schema import AnalysisSample, GraphNode, GraphEdge, TelemetryPoint, TransactionContext

TX_TYPES = ["UPI_PAYMENT", "FUND_TRANSFER", "CARD_PAYMENT", "BALANCE_INQUIRY", "BILL_PAYMENT"]

NODE_CATALOG = {
    "api-gateway": ("api_gateway", "API Gateway", "application"),
    "payment-service": ("microservice", "Payment Service", "application"),
    "transfer-service": ("microservice", "Transfer Service", "application"),
    "card-service": ("microservice", "Card Service", "application"),
    "account-service": ("microservice", "Account Service", "application"),
    "bill-service": ("microservice", "Bill Service", "application"),
    "risk-service": ("microservice", "Risk Service", "application"),
    "notification-service": ("microservice", "Notification Service", "application"),
    "ec2-01": ("ec2", "EC2-01", "compute"),
    "ec2-02": ("ec2", "EC2-02", "compute"),
    "ec2-03": ("ec2", "EC2-03", "compute"),
    "rds-01": ("rds", "RDS-01", "data"),
    "cache-01": ("cache", "Cache-01", "data"),
    "queue-01": ("queue", "Queue-01", "messaging"),
}

TOPOLOGIES = {
    "UPI_PAYMENT": {
        "path": ["api-gateway", "payment-service", "ec2-01", "rds-01"],
        "edges": [
            ("api-gateway", "payment-service", "CALLS"),
            ("payment-service", "ec2-01", "HOSTS"),
            ("ec2-01", "rds-01", "READS_FROM"),
            ("payment-service", "cache-01", "READS_FROM"),
        ],
    },
    "FUND_TRANSFER": {
        "path": ["api-gateway", "transfer-service", "ec2-01", "rds-01"],
        "edges": [
            ("api-gateway", "transfer-service", "CALLS"),
            ("transfer-service", "ec2-01", "HOSTS"),
            ("ec2-01", "rds-01", "WRITES_TO"),
            ("transfer-service", "account-service", "DEPENDS_ON"),
            ("account-service", "ec2-02", "HOSTS"),
            ("ec2-02", "rds-01", "READS_FROM"),
        ],
    },
    "CARD_PAYMENT": {
        "path": ["api-gateway", "card-service", "ec2-01", "rds-01"],
        "edges": [
            ("api-gateway", "card-service", "CALLS"),
            ("card-service", "ec2-01", "HOSTS"),
            ("ec2-01", "rds-01", "READS_FROM"),
            ("card-service", "risk-service", "DEPENDS_ON"),
            ("risk-service", "ec2-02", "HOSTS"),
            ("card-service", "queue-01", "WRITES_TO"),
            ("queue-01", "notification-service", "CALLS"),
        ],
    },
    "BALANCE_INQUIRY": {
        "path": ["api-gateway", "account-service", "ec2-02", "rds-01"],
        "edges": [
            ("api-gateway", "account-service", "CALLS"),
            ("account-service", "ec2-02", "HOSTS"),
            ("ec2-02", "rds-01", "READS_FROM"),
            ("account-service", "cache-01", "READS_FROM"),
        ],
    },
    "BILL_PAYMENT": {
        "path": ["api-gateway", "bill-service", "ec2-03", "rds-01", "queue-01", "notification-service"],
        "edges": [
            ("api-gateway", "bill-service", "CALLS"),
            ("bill-service", "ec2-03", "HOSTS"),
            ("ec2-03", "rds-01", "WRITES_TO"),
            ("bill-service", "queue-01", "WRITES_TO"),
            ("queue-01", "notification-service", "CALLS"),
        ],
    },
}

@dataclass
class ScenarioSpec:
    scenario: str
    root_role: str

SCENARIOS = {
    "NORMAL": ScenarioSpec("NORMAL", "none"),
    "CPU_SPIKE": ScenarioSpec("CPU_SPIKE", "compute"),
    "DATABASE_LATENCY": ScenarioSpec("DATABASE_LATENCY", "database"),
    "SERVICE_OVERLOAD": ScenarioSpec("SERVICE_OVERLOAD", "service"),
    "NETWORK_DEGRADATION": ScenarioSpec("NETWORK_DEGRADATION", "gateway"),
    "CASCADING_FAILURE": ScenarioSpec("CASCADING_FAILURE", "database"),
}


def _transaction_service(tx_type: str) -> str:
    return TOPOLOGIES[tx_type]["path"][1]


def _role_root(nodes: list[GraphNode], path: list[str], role: str) -> str | None:
    if role == "none":
        return None
    if role == "gateway":
        return "api-gateway"
    if role == "database":
        return next((n.id for n in nodes if n.type == "rds" and n.id in path), None)
    if role == "compute":
        return next((n.id for n in nodes if n.type == "ec2" and n.id in path), None)
    if role == "service":
        return path[1] if len(path) > 1 else None
    return None


def _affected_nodes(edges: list[GraphEdge], root: str | None) -> list[str]:
    if not root:
        return []
    neighbors = {root}
    for e in edges:
        if e.source == root:
            neighbors.add(e.target)
        if e.target == root:
            neighbors.add(e.source)
    return list(neighbors)


def _base_metrics(node_type: str, rng: random.Random) -> dict[str, float]:
    base = {
        "cpu_percent": rng.uniform(25, 55),
        "memory_percent": rng.uniform(35, 65),
        "network_in_mbps": rng.uniform(5, 45),
        "network_out_mbps": rng.uniform(5, 45),
        "latency_ms": rng.uniform(40, 120),
        "error_rate": rng.uniform(0.001, 0.02),
        "request_rate": rng.uniform(60, 240),
        "db_latency_ms": rng.uniform(20, 80),
        "disk_io": rng.uniform(50, 250),
    }
    if node_type == "rds":
        base["db_latency_ms"] = rng.uniform(20, 90)
        base["request_rate"] = rng.uniform(50, 180)
    elif node_type == "api_gateway":
        base["latency_ms"] += 20
    return base


def _apply_scenario(metrics: dict[str, float], scenario: str, node: GraphNode, root: str | None, affected: set[str], rng: random.Random):
    if node.id == root and scenario == "CPU_SPIKE":
        metrics.update(cpu_percent=rng.uniform(90, 99), memory_percent=rng.uniform(72, 88), latency_ms=rng.uniform(260, 450), error_rate=rng.uniform(0.10, 0.24))
    elif node.id in affected and scenario == "CPU_SPIKE":
        metrics.update(latency_ms=rng.uniform(170, 300), error_rate=rng.uniform(0.04, 0.12))
    elif node.id == root and scenario == "DATABASE_LATENCY":
        metrics.update(db_latency_ms=rng.uniform(650, 1200), latency_ms=rng.uniform(450, 950), disk_io=rng.uniform(700, 980))
    elif node.id in affected and scenario == "DATABASE_LATENCY":
        metrics.update(latency_ms=rng.uniform(180, 400), error_rate=rng.uniform(0.04, 0.12), cpu_percent=rng.uniform(58, 78))
    elif node.id == root and scenario == "SERVICE_OVERLOAD":
        metrics.update(cpu_percent=rng.uniform(85, 97), memory_percent=rng.uniform(78, 95), request_rate=rng.uniform(380, 500), latency_ms=rng.uniform(350, 800), error_rate=rng.uniform(0.12, 0.30))
    elif node.id in affected and scenario == "SERVICE_OVERLOAD":
        metrics.update(cpu_percent=rng.uniform(65, 85), latency_ms=rng.uniform(180, 360))
    elif node.id == root and scenario == "NETWORK_DEGRADATION":
        metrics.update(network_in_mbps=rng.uniform(1, 5), network_out_mbps=rng.uniform(1, 5), latency_ms=rng.uniform(380, 850), error_rate=rng.uniform(0.08, 0.22))
    elif node.id in affected and scenario == "NETWORK_DEGRADATION":
        metrics.update(latency_ms=rng.uniform(220, 450), error_rate=rng.uniform(0.04, 0.11))
    elif node.id == root and scenario == "CASCADING_FAILURE":
        metrics.update(db_latency_ms=rng.uniform(800, 1400), latency_ms=rng.uniform(600, 1100), disk_io=rng.uniform(800, 1000), error_rate=rng.uniform(0.12, 0.30))
    elif node.id in affected and scenario == "CASCADING_FAILURE":
        metrics.update(cpu_percent=rng.uniform(68, 94), latency_ms=rng.uniform(350, 750), error_rate=rng.uniform(0.10, 0.26))


def generate_sample(scenario: str, seed: int = 42, index: int = 0, tx_type: str | None = None, topology_variant: str = "transaction", topology_change: bool = False) -> AnalysisSample:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    tx = tx_type or TX_TYPES[index % len(TX_TYPES)]
    if tx not in TOPOLOGIES:
        raise ValueError(f"Unsupported transaction type: {tx}")
    rng = random.Random(seed + index * 7919)
    topology = TOPOLOGIES[tx]
    edge_defs = list(topology["edges"])
    metadata = {"topology_variant": topology_variant, "transaction_graph": tx}
    if topology_change:
        # Controlled topology drift representing a temporary fallback dependency.
        service = topology["path"][1]
        candidates = [
            (service, "queue-01", "WRITES_TO"),
            (service, "notification-service", "CALLS"),
            (service, "cache-01", "READS_FROM"),
        ]
        chosen = next((e for e in candidates if e not in edge_defs), None)
        if chosen is not None:
            edge_defs.append(chosen)
            metadata["topology_change"] = f"fallback_dependency_added:{chosen[1]}"
    nodes_ids = {x for e in edge_defs for x in (e[0], e[1])} | set(topology["path"])
    nodes = [GraphNode(id=i, type=NODE_CATALOG[i][0], label=NODE_CATALOG[i][1], layer=NODE_CATALOG[i][2]) for i in sorted(nodes_ids)]
    edges = [GraphEdge(source=s, target=t, relationship=r) for s, t, r in edge_defs]
    root = _role_root(nodes, list(topology["path"]), SCENARIOS[scenario].root_role)
    affected = set(_affected_nodes(edges, root))
    timestamp = datetime(2026, 9, 23, 8, 0, tzinfo=timezone.utc) + timedelta(seconds=index * 60)
    telemetry = []
    labels = {}
    for node in nodes:
        m = _base_metrics(node.type, rng)
        _apply_scenario(m, scenario, node, root, affected, rng)
        telemetry.append(TelemetryPoint(node_id=node.id, timestamp=timestamp, **m, source="simulation"))
        labels[node.id] = 1 if node.id in affected else 0
    return AnalysisSample(
        transaction=TransactionContext(id=f"TX-{index:06d}", type=tx, path=list(topology["path"])),
        nodes=nodes,
        edges=edges,
        telemetry=telemetry,
        scenario=scenario,
        node_labels=labels,
        root_cause_nodes=[root] if root else [],
        sequence_index=index,
        source="simulation",
        metadata=metadata,
    )


def generate_dataset(samples: int, seed: int = 42, scenarios: Iterable[str] | None = None, tx_types: Iterable[str] | None = None) -> list[AnalysisSample]:
    scenarios = list(scenarios or SCENARIOS.keys())
    tx_types = list(tx_types or TX_TYPES)
    return [generate_sample(scenarios[i % len(scenarios)], seed=seed, index=i, tx_type=tx_types[i % len(tx_types)]) for i in range(samples)]


def generate_sequence(scenario: str = "DATABASE_LATENCY", steps: int = 8, seed: int = 42, anomaly_start: int = 3, tx_type: str = "UPI_PAYMENT", topology_change: bool = True) -> list[AnalysisSample]:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown sequence scenario: {scenario}")
    samples = []
    for step in range(steps):
        if scenario == "NORMAL":
            phase = "NORMAL"
        else:
            phase = "NORMAL" if step < anomaly_start else scenario
            if step == steps - 1:
                phase = "NORMAL"
        samples.append(generate_sample(phase, seed=seed + step * 17, index=step, tx_type=tx_type, topology_change=(topology_change and step >= anomaly_start and step < steps - 1)))
    return samples


def write_jsonl(samples: list[AnalysisSample], path: str | Path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for sample in samples: f.write(json.dumps(sample.model_dump(mode="json")) + "\n")


def read_jsonl(path: str | Path) -> list[AnalysisSample]:
    path = Path(path); out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip(): out.append(AnalysisSample.model_validate(json.loads(line)))
    return out
