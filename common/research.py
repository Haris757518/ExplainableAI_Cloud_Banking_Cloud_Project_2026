"""Shared contracts. Benchmark labels are deliberately outside inference inputs."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class DataSource(BaseModel):
    id: str
    kind: Literal['production_trace','expert_labelled_series','recorded_controlled_benchmark','live_cloud']
    reference: str
    revision: str | None = None
    topology_status: str = 'unavailable'

class TelemetryObservation(BaseModel):
    timestamp: float
    value: float | None = Field(default=None, allow_inf_nan=False)
    quality: str = 'observed'
    source_rows: list[int] = Field(default_factory=list)
    original_timestamp: float | None = None
    timestamp_semantics: str | None = None

class TelemetrySeries(BaseModel):
    id: str
    resource: str
    metric: str
    original_metric: str
    unit: str = 'source unit unspecified'
    period_seconds: float | None = None
    timestamp_kind: str = 'unix_seconds'
    observations: list[TelemetryObservation]

class DependencyEdge(BaseModel):
    observed_at: float | None = None
    source: str
    target: str
    relationship: str = 'recorded_call'
    provenance: str

class TelemetryCase(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    source: DataSource
    collection: str
    series: list[TelemetrySeries]
    edges: list[DependencyEdge] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)

class PerformanceForecast(BaseModel):
    status: str
    model: str
    series_id: str
    horizon_steps: int = 1
    timestamp: float | None = None
    value: float | None = None
    lower: float | None = None
    upper: float | None = None
    interval_interpretation: str | None = None
    reliability: str
    threshold_reference: float | None = None
    expected_threshold_exceedance: bool | None = None

class EvidenceRecord(BaseModel):
    resource: str
    metric: str
    timestamp: float
    value: float
    reference: float
    scale: float
    score: float
    direction: str
    persistence: int
    onset: float | None = None
    kind: str = 'measured_statistical_deviation'

class RootCauseCandidate(BaseModel):
    resource: str
    score: float
    temporal_score: float
    graph_support: float = 0
    score_definition: str
    supporting_evidence: list[EvidenceRecord]
    competing_hypotheses: list[str]
    missing_evidence: list[str]
    evidence_status: str = 'suspected; no causal confirmation'

class RecommendedAction(BaseModel):
    category: str
    evidence: list[str]
    mechanism_status: str
    diagnostic_action: str
    proposed_mitigation: str
    purpose: str
    verification_metric: str
    prerequisites: str = 'Operator verification and separate authorization before changes.'

class Incident(BaseModel):
    id: str
    source: DataSource
    observation_time: float | None
    status: str
    score_interpretation: str
    model_version: str
    affected_services: list[str]
    candidates: list[RootCauseCandidate]
    evidence: list[EvidenceRecord]
    missing_evidence: list[str]
    recommendations: list[RecommendedAction]
    forecasts: list[PerformanceForecast]
    investigation: dict
    explanation: dict
    recovery: dict
    graph: dict
    ground_truth_available: bool = False
    cause_verified: bool = False
    provenance: dict

class EvaluationResult(BaseModel):
    dataset: str
    split: dict
    methods: dict
    limitations: list[str]
    provenance: dict
