from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

TransactionType = Literal[
    "UPI_PAYMENT", "FUND_TRANSFER", "CARD_PAYMENT", "BALANCE_INQUIRY", "BILL_PAYMENT", "ALIBABA_BENCHMARK", "OBSERVABILITY_PROBE"
]
NodeType = Literal["api_gateway", "microservice", "ec2", "rds", "cache", "queue", "database"]
Scenario = Literal[
    "NORMAL", "CPU_SPIKE", "DATABASE_LATENCY", "SERVICE_OVERLOAD",
    "NETWORK_DEGRADATION", "CASCADING_FAILURE", "UNLABELED"
]

class TransactionContext(BaseModel):
    id: str
    type: TransactionType
    path: list[str] = Field(default_factory=list)

class GraphNode(BaseModel):
    id: str
    type: NodeType
    label: str
    layer: str = "infrastructure"

class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str = "depends_on"

class TelemetryPoint(BaseModel):
    node_id: str
    timestamp: datetime | None = Field(default_factory=lambda: datetime.now(timezone.utc))
    cpu_percent: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    memory_percent: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    network_in_mbps: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    network_out_mbps: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    latency_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    error_rate: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    request_rate: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    db_latency_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    disk_io: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    source: str = "simulation"
    observed_metrics: list[str] = Field(default_factory=list)

class AnalysisSample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction: TransactionContext
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    telemetry: list[TelemetryPoint]
    scenario: Scenario
    node_labels: dict[str, int] = Field(default_factory=dict)
    root_cause_nodes: list[str] = Field(default_factory=list)
    sequence_index: int = 0
    source: str = "simulation"
    metadata: dict = Field(default_factory=dict)

class AffectedNode(BaseModel):
    node: str
    score: float
    node_type: str | None = None

class RootCause(BaseModel):
    node: str
    score: float
    reason: str
    evidence: list[str] = Field(default_factory=list)
    transaction_relevance: float = 0.0
    graph_propagation: float = 0.0
    path_classification: str = "UNKNOWN"

class FeatureImportance(BaseModel):
    feature: str
    importance: float

class Explanation(BaseModel):
    important_features: list[FeatureImportance]
    important_nodes: list[AffectedNode]
    dependency_path: list[str]
    narrative: str = ""

class TelemetryPolicy(BaseModel):
    resolution_seconds: dict[str, int]
    baseline_resolution_seconds: int = 60
    focused_resolution_seconds: int = 5
    estimated_high_resolution_reduction_percent: float = 0.0

class CFAOResult(BaseModel):
    causal_frontier: list[str]
    telemetry_policy: TelemetryPolicy
    trigger: str
    refinement: dict = Field(default_factory=dict)

class CounterfactualResult(BaseModel):
    node: str
    intervention: str
    original_anomaly_score: float
    counterfactual_anomaly_score: float
    score_reduction: float
    interpretation: str

class AnalysisResult(BaseModel):
    assessment: dict = Field(default_factory=dict)
    anomaly_score: float | None
    is_anomaly: bool | None
    affected_nodes: list[AffectedNode]
    root_causes: list[RootCause]
    explanation: Explanation
    cfao: CFAOResult
    counterfactual: CounterfactualResult | None = None
    source: str
    scenario: str
    transaction: TransactionContext
    graph: AnalysisSample
    model_version: str = "baseline-gcn-v2"
