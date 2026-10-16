from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from database.db import Base

class AnalysisRun(Base):
    __tablename__="analysis_runs"
    __table_args__ = (Index("ix_runs_created", "created_at"), Index("ix_runs_anomaly_created", "is_anomaly", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(64))
    scenario: Mapped[str] = mapped_column(String(64))
    anomaly_score: Mapped[float | None] = mapped_column(Float)
    is_anomaly: Mapped[bool | None] = mapped_column(Boolean)
    root_cause: Mapped[str] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(String(64))
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DiagnosticSnapshot(Base):
    __tablename__ = 'diagnostic_snapshots'
    __table_args__ = (Index('ix_diagnostic_resource_created', 'resource_id', 'created_at'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[str] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(String(64))
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
