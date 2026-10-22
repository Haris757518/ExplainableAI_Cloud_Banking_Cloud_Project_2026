"""Published observations only; no infrastructure fields are inferred."""
from dataclasses import dataclass, asdict

SOURCES = {
    'monzo': 'https://monzo.com/service-information',
    'starling': 'https://www.starlingbank.com/current-account/service-information/api-performance/',
}

@dataclass(frozen=True)
class Observation:
    bank: str
    source_name: str
    date: str
    service: str
    metric: str
    value: float | None
    unit: str
    frequency: str
    data_origin: str
    source_url: str
    retrieved_at: str
    record_status: str
    raw_value: str
    snapshot_sha256: str

    def dict(self):
        return asdict(self)
