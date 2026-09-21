from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

TransactionType = Literal[
    "UPI_PAYMENT", "FUND_TRANSFER", "CARD_PAYMENT", "BALANCE_INQUIRY", "BILL_PAYMENT"
]
NodeType = Literal["api_gateway", "microservice", "ec2", "rds", "cache", "queue"]
Scenario = Literal[
    "NORMAL", "CPU_SPIKE", "DATABASE_LATENCY", "SERVICE_OVERLOAD",
    "NETWORK_DEGRADATION", "CASCADING_FAILURE"
]

class TransactionContext(BaseModel):
    id: str
    type: TransactionType

class GraphNode(BaseModel):
    id: str
    type: NodeType
    label: str

class GraphEdge(BaseModel):
    source: str
    target: str

class TelemetryPoint(BaseModel):
    node_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cpu_percent: float = Field(ge=0, le=100)
    memory_percent: float = Field(ge=0, le=100)
    network_in_mbps: float = Field(ge=0)
    network_out_mbps: float = Field(ge=0)
    latency_ms: float = Field(ge=0)
    error_rate: float = Field(ge=0, le=1)
    request_rate: float = Field(ge=0)
    db_latency_ms: float = Field(ge=0)
    disk_io: float = Field(ge=0)

class AnalysisSample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction: TransactionContext
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    telemetry: list[TelemetryPoint]
    scenario: Scenario
    node_labels: dict[str, int] = Field(default_factory=dict)
    root_cause_nodes: list[str] = Field(default_factory=list)

class AffectedNode(BaseModel):
    node: str
    score: float
    node_type: str | None = None

class RootCause(BaseModel):
    node: str
    score: float
    reason: str
    evidence: list[str] = []

class FeatureImportance(BaseModel):
    feature: str
    importance: float

class Explanation(BaseModel):
    important_features: list[FeatureImportance]
    important_nodes: list[AffectedNode]
    dependency_path: list[str]

class TelemetryPolicy(BaseModel):
    resolution_seconds: dict[str, int]

class CFAOResult(BaseModel):
    causal_frontier: list[str]
    telemetry_policy: TelemetryPolicy
    trigger: str

class AnalysisResult(BaseModel):
    anomaly_score: float
    is_anomaly: bool
    affected_nodes: list[AffectedNode]
    root_causes: list[RootCause]
    explanation: Explanation
    cfao: CFAOResult
    source: str
    scenario: str
    transaction: TransactionContext
    graph: AnalysisSample
