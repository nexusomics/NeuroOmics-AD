"""Dataset schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

OMICS_TYPES = [
    "genomics", "transcriptomics", "proteomics", "metabolomics",
    "epigenomics", "single_cell", "gwas", "clinical",
]


class DatasetCreate(BaseModel):
    name: str
    omics_type: str = Field(..., description=f"one of {OMICS_TYPES}")
    platform: str = ""
    format: str = "csv"
    metadata_json: dict[str, Any] = {}


class DatasetOut(BaseModel):
    id: str
    project_id: str
    name: str
    omics_type: str
    platform: str
    format: str
    n_samples: int
    n_features: int
    metadata_json: dict[str, Any]
    status: str
    created_at: Optional[datetime] = None


class DatasetQCRequest(BaseModel):
    """Request to run QC/preprocessing on a dataset."""
    normalize: bool = True
    log_transform: bool = False
    batch_correct: bool = False
    batch_column: str = "batch"
    impute_missing: bool = True
    remove_outliers: bool = True
    method: str = "quantile"  # quantile | vst | tmm | none
