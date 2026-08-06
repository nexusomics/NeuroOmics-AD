"""Analysis run models: analyses, steps, and result artifacts."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True, default=_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    analysis_type = Column(String(64), nullable=False)  # differential_expression|meta_analysis|enrichment|network|deconvolution|integration|ml|drug_repurposing|preprocessing|single_cell|epigenomics|genomics
    config = Column(JSON, default=dict)
    status = Column(String(32), default="queued")  # queued|running|completed|failed|cancelled
    progress = Column(Integer, default=0)  # 0-100
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    error_message = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=dt.datetime.now(dt.timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="analyses")
    steps = relationship("AnalysisStep", back_populates="analysis", cascade="all, delete-orphan")
    artifacts = relationship("ResultArtifact", back_populates="analysis", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "analysis_type": self.analysis_type,
            "config": self.config or {},
            "status": self.status,
            "progress": self.progress,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


class AnalysisStep(Base):
    __tablename__ = "analysis_steps"

    id = Column(String(36), primary_key=True, default=_uuid)
    analysis_id = Column(String(36), ForeignKey("analyses.id"), nullable=False)
    step_name = Column(String(128), nullable=False)
    status = Column(String(32), default="pending")
    message = Column(Text, default="")
    duration_seconds = Column(Float, default=0.0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    analysis = relationship("Analysis", back_populates="steps")


class ResultArtifact(Base):
    __tablename__ = "result_artifacts"

    id = Column(String(36), primary_key=True, default=_uuid)
    analysis_id = Column(String(36), ForeignKey("analyses.id"), nullable=False)
    name = Column(String(255), nullable=False)
    kind = Column(String(32), default="table")  # table|figure|json|text|report
    format = Column(String(16), default="csv")  # csv|json|png|svg|html|pdf|docx|pptx|xlsx
    file_path = Column(String(512), default="")
    size_bytes = Column(Integer, default=0)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=dt.datetime.now(dt.timezone.utc))

    analysis = relationship("Analysis", back_populates="artifacts")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "name": self.name,
            "kind": self.kind,
            "format": self.format,
            "file_path": self.file_path,
            "size_bytes": self.size_bytes,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
