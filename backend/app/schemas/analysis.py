"""Analysis schemas for omics workflows."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class AnalysisCreate(BaseModel):
    name: str
    analysis_type: str
    dataset_ids: list[str] = []
    config: dict[str, Any] = {}


class AnalysisOut(BaseModel):
    id: str
    project_id: str
    name: str
    analysis_type: str
    config: dict[str, Any]
    status: str
    progress: int
    error_message: str = ""
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class ArtifactOut(BaseModel):
    id: str
    analysis_id: str
    name: str
    kind: str
    format: str
    file_path: str
    size_bytes: int
    metadata_json: dict[str, Any]
    created_at: Optional[datetime] = None


# ---- differential expression ----
class DifferentialExpressionRequest(BaseModel):
    dataset_id: str
    group_column: str = "group"
    case_group: str
    control_group: str
    covariates: list[str] = []
    method: Literal["auto", "deseq2", "limma", "python"] = "auto"
    fdr_threshold: float = 0.05
    log2fc_threshold: float = 1.0


# ---- meta-analysis ----
class MetaAnalysisRequest(BaseModel):
    dataset_ids: list[str] = Field(..., min_length=2)
    group_column: str = "group"
    case_group: str
    control_group: str
    effect_size_method: Literal["cohens_d", "hedges_g", "log2fc"] = "cohens_d"
    fixed_effects: bool = True


# ---- deconvolution ----
class DeconvolutionRequest(BaseModel):
    dataset_id: str
    signature_source: str = "lm22"  # lm22 (CIBERSORT-style) | custom
    method: Literal["cibersort", "bayesprism_style", "nnls"] = "cibersort"


# ---- enrichment ----
class EnrichmentRequest(BaseModel):
    gene_list: list[str] = Field(..., min_length=1)
    background: Optional[list[str]] = None
    databases: list[str] = ["GO_Biological_Process", "KEGG_2021_Human", "Reactome_2022"]
    min_size: int = 5
    max_size: int = 500
    fdr_threshold: float = 0.05


# ---- network ----
class NetworkRequest(BaseModel):
    gene_list: list[str] = Field(..., min_length=1)
    confidence_threshold: float = 0.4
    max_interactors: int = 50
    source: str = "string"  # string | biogrid | custom


# ---- integration ----
class IntegrationRequest(BaseModel):
    dataset_ids: list[str] = Field(..., min_length=2)
    method: Literal["weighted_fusion", "moa_like", "jive_like"] = "weighted_fusion"
    rank: int = 5
