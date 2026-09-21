from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import random
from pathlib import Path
from typing import Iterable
from common.schema import AnalysisSample, GraphNode, GraphEdge, TelemetryPoint, TransactionContext

NODE_DEFS = [
    ("api-gateway", "api_gateway", "API Gateway"),
    ("payment-service", "microservice", "Payment Service"),
    ("notification-service", "microservice", "Notification Service"),
    ("ec2-01", "ec2", "EC2-01"),
    ("rds-01", "rds", "RDS-01"),
    ("cache-01", "cache", "Cache-01"),
    ("queue-01", "queue", "Queue-01"),
]
EDGES = [
    ("api-gateway", "payment-service"),
    ("payment-service", "ec2-01"),
    ("ec2-01", "rds-01"),
    ("payment-service", "cache-01"),
    ("payment-service", "queue-01"),
    ("queue-01", "notification-service"),
]
TX_TYPES = ["UPI_PAYMENT", "FUND_TRANSFER", "CARD_PAYMENT", "BALANCE_INQUIRY", "BILL_PAYMENT"]

@dataclass
class ScenarioSpec:
    scenario: str
    root: list[str]
    affected: list[str]

SCENARIOS = {
    "NORMAL": ScenarioSpec("NORMAL", [], []),
    "CPU_SPIKE": ScenarioSpec("CPU_SPIKE", ["ec2-01"], ["ec2-01", "payment-service"]),
    "DATABASE_LATENCY": ScenarioSpec("DATABASE_LATENCY", ["rds-01"], ["rds-01", "ec2-01", "payment-service"]),
    "SERVICE_OVERLOAD": ScenarioSpec("SERVICE_OVERLOAD", ["payment-service"], ["payment-service", "ec2-01"]),
    "NETWORK_DEGRADATION": ScenarioSpec("NETWORK_DEGRADATION", ["api-gateway"], ["api-gateway", "payment-service"]),
    "CASCADING_FAILURE": ScenarioSpec("CASCADING_FAILURE", ["rds-01"], ["rds-01", "ec2-01", "payment-service", "api-gateway"]),
}


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


def _apply_scenario(metrics: dict[str, float], scenario: str, node_id: str, rng: random.Random):
    root = SCENARIOS[scenario].root
    affected = SCENARIOS[scenario].affected
    if scenario == "CPU_SPIKE" and node_id == "ec2-01":
        metrics.update(cpu_percent=rng.uniform(90, 99), memory_percent=rng.uniform(72, 88), latency_ms=rng.uniform(260, 450), error_rate=rng.uniform(0.10, 0.24))
    elif scenario == "CPU_SPIKE" and node_id == "payment-service":
        metrics.update(latency_ms=rng.uniform(170, 300), error_rate=rng.uniform(0.04, 0.12))
    elif scenario == "DATABASE_LATENCY" and node_id == "rds-01":
        metrics.update(db_latency_ms=rng.uniform(650, 1200), latency_ms=rng.uniform(450, 950), disk_io=rng.uniform(700, 980))
    elif scenario == "DATABASE_LATENCY" and node_id == "ec2-01":
        metrics.update(latency_ms=rng.uniform(180, 400), error_rate=rng.uniform(0.04, 0.12), cpu_percent=rng.uniform(58, 78))
    elif scenario == "DATABASE_LATENCY" and node_id == "payment-service":
        metrics.update(latency_ms=rng.uniform(220, 500), error_rate=rng.uniform(0.05, 0.14))
    elif scenario == "SERVICE_OVERLOAD" and node_id == "payment-service":
        metrics.update(cpu_percent=rng.uniform(85, 97), memory_percent=rng.uniform(78, 95), request_rate=rng.uniform(380, 500), latency_ms=rng.uniform(350, 800), error_rate=rng.uniform(0.12, 0.3))
    elif scenario == "SERVICE_OVERLOAD" and node_id == "ec2-01":
        metrics.update(cpu_percent=rng.uniform(65, 85), latency_ms=rng.uniform(180, 360))
    elif scenario == "NETWORK_DEGRADATION" and node_id == "api-gateway":
        metrics.update(network_in_mbps=rng.uniform(1, 5), network_out_mbps=rng.uniform(1, 5), latency_ms=rng.uniform(380, 850), error_rate=rng.uniform(0.08, 0.22))
    elif scenario == "NETWORK_DEGRADATION" and node_id == "payment-service":
        metrics.update(latency_ms=rng.uniform(220, 450), error_rate=rng.uniform(0.04, 0.11))
    elif scenario == "CASCADING_FAILURE" and node_id == "rds-01":
        metrics.update(db_latency_ms=rng.uniform(800, 1400), latency_ms=rng.uniform(600, 1100), disk_io=rng.uniform(800, 1000), error_rate=rng.uniform(0.12, 0.3))
    elif scenario == "CASCADING_FAILURE" and node_id == "ec2-01":
        metrics.update(cpu_percent=rng.uniform(78, 94), latency_ms=rng.uniform(400, 750), error_rate=rng.uniform(0.10, 0.24))
    elif scenario == "CASCADING_FAILURE" and node_id == "payment-service":
        metrics.update(latency_ms=rng.uniform(500, 1000), error_rate=rng.uniform(0.16, 0.35))
    elif scenario == "CASCADING_FAILURE" and node_id == "api-gateway":
        metrics.update(latency_ms=rng.uniform(400, 850), error_rate=rng.uniform(0.12, 0.28))


def generate_sample(scenario: str, seed: int = 42, index: int = 0) -> AnalysisSample:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    rng = random.Random(seed + index * 7919)
    tx = TX_TYPES[index % len(TX_TYPES)]
    timestamp = datetime(2026, 9, 21, 8, 0, tzinfo=timezone.utc) + timedelta(seconds=index * 60)
    nodes = [GraphNode(id=i, type=t, label=l) for i, t, l in NODE_DEFS]
    edges = [GraphEdge(source=s, target=t) for s, t in EDGES]
    telemetry = []
    labels = {}
    for node in nodes:
        m = _base_metrics(node.type, rng)
        _apply_scenario(m, scenario, node.id, rng)
        telemetry.append(TelemetryPoint(node_id=node.id, timestamp=timestamp, **m))
        labels[node.id] = 1 if node.id in SCENARIOS[scenario].affected else 0
    roots = list(SCENARIOS[scenario].root)
    return AnalysisSample(
        transaction=TransactionContext(id=f"TX-{index:06d}", type=tx),
        nodes=nodes, edges=edges, telemetry=telemetry,
        scenario=scenario, node_labels=labels, root_cause_nodes=roots
    )


def generate_dataset(samples: int, seed: int = 42, scenarios: Iterable[str] | None = None) -> list[AnalysisSample]:
    scenarios = list(scenarios or SCENARIOS.keys())
    return [generate_sample(scenarios[i % len(scenarios)], seed=seed, index=i) for i in range(samples)]


def write_jsonl(samples: list[AnalysisSample], path: str | Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample.model_dump(mode="json")) + "\n")


def read_jsonl(path: str | Path) -> list[AnalysisSample]:
    path = Path(path)
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip(): out.append(AnalysisSample.model_validate(json.loads(line)))
    return out
