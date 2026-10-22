"""Measurements and experiment labels are separate contracts."""
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict,model_validator

class MeasuredPoint(BaseModel):
    model_config=ConfigDict(extra='forbid')
    timestamp:float
    service:str
    metric:str
    value:float|None=Field(default=None,allow_inf_nan=False)
    unit:str
    observation_id:str
    origin:Literal['executed_workload']
    collector:str
    trace_id:str|None=None

class RecordedSpan(BaseModel):
    model_config=ConfigDict(extra='forbid')
    trace_id:str
    span_id:str
    parent_span_id:str|None=None
    service:str
    start:float
    end:float
    @model_validator(mode='after')
    def valid(self):
        if self.end<self.start:raise ValueError('Span ends before it starts')
        return self

class BankingCloudRecording(BaseModel):
    model_config=ConfigDict(extra='forbid')
    recording_id:str
    application:Literal['bank_of_anthos','instrumented_banking_application']
    environment:Literal['local','aws']
    infrastructure_id:str
    execution_id:str
    baseline_end:float
    measurements:list[MeasuredPoint]
    spans:list[RecordedSpan]=[]
    collector_version:str
    source_artifact_sha256:str
    # This is a provenance assertion checked against retained source artifacts,
    # not a proof obtainable by checking JSON field names.

class ExperimentLabel(BaseModel):
    model_config=ConfigDict(extra='forbid')
    execution_id:str
    affected_service:str
    injected_fault:str
    underlying_driver:str|None=None
    injection_start:float
    injection_end:float
    label_origin:str
