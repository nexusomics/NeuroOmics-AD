"""Drug repurposing schemas."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class DrugPipelineRequest(BaseModel):
    gene_list: list[str] = Field(..., min_length=1, description="Disease genes / prioritized targets")
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "network": 0.25, "pathway_reversal": 0.20, "target_overlap": 0.20,
            "bbb": 0.10, "admet": 0.10, "clinical": 0.15,
        },
        description="Criterion weights (must sum to 1)",
    )
    max_candidates: int = 50
    require_bbb_positive: bool = False
    min_clinical_phase: str = "preclinical"  # preclinical | phase1 | phase2 | phase3 | approved
    sources: list[str] = Field(default_factory=lambda: ["chembl", "dgidb", "open_targets", "drugbank", "lincs", "cmap"])


class DrugCandidateOut(BaseModel):
    drug_name: str
    drugbank_id: str = ""
    chebi_id: str = ""
    pubchem_cid: str = ""
    mechanism: str = ""
    targets: list[str]
    fda_status: str = ""
    indication: str = ""
    score_network: float
    score_pathway_reversal: float
    score_target_overlap: float
    score_bbb: float
    score_admet: float
    score_clinical: float
    composite_score: float
    rank: int
    details: dict[str, Any] = {}


class DrugTargetMapRequest(BaseModel):
    gene_list: list[str] = Field(..., min_length=1)


class DrugCombinationRequest(BaseModel):
    gene_list: list[str] = Field(..., min_length=1)
    top_n: int = 20
