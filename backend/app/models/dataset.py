"""Dataset models: uploaded multi-omics datasets and their sample metadata."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    omics_type = Column(String(32), nullable=False)  # genomics|transcriptomics|proteomics|metabolomics|epigenomics|single_cell|gwas|clinical
    platform = Column(String(64), default="")
    file_path = Column(String(512), default="")
    format = Column(String(32), default="csv")  # csv|tsv|txt|mtx|vcf|bed
    n_samples = Column(Integer, default=0)
    n_features = Column(Integer, default=0)
    metadata_json = Column(JSON, default=dict)
    status = Column(String(32), default="uploaded")  # uploaded|processing|qc_passed|qc_failed|ready
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=dt.datetime.now(dt.timezone.utc))

    project = relationship("Project", back_populates="datasets")
    samples = relationship("DatasetSample", back_populates="dataset", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "omics_type": self.omics_type,
            "platform": self.platform,
            "format": self.format,
            "n_samples": self.n_samples,
            "n_features": self.n_features,
            "metadata_json": self.metadata_json or {},
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DatasetSample(Base):
    __tablename__ = "dataset_samples"

    id = Column(String(36), primary_key=True, default=_uuid)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    sample_id = Column(String(128), nullable=False)
    group = Column(String(64), default="")  # e.g. AD / CN / MCI
    covariates = Column(JSON, default=dict)

    dataset = relationship("Dataset", back_populates="samples")
