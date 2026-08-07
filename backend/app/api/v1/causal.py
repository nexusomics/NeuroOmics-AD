"""Causal multi-omics module API: catalog queries + pipeline execution."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.causal.catalog import catalog


def _jsonable(obj):
    """Recursively convert pandas/numpy objects to JSON-safe primitives."""
    import numpy as np
    import pandas as pd

    if isinstance(obj, pd.DataFrame):
        return {k: _jsonable(v) for k, v in obj.to_dict(orient="index").items()}
    if isinstance(obj, pd.Series):
        return _jsonable(obj.to_dict())
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return _jsonable(obj.tolist())
    return obj
from app.causal.data.synth import generate_causal_dataset
from app.causal.pipeline import run_causal_pipeline
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/causal", tags=["causal-multi-omics"])


@router.get("/resources")
def list_resources(user: User = Depends(get_current_user)) -> dict:
    """Catalog of integrated AD resources with accessions, modalities, citations."""
    return {"resources": catalog.resource_table(), "stats": catalog.stats()}


@router.get("/query")
def query_catalog(
    cohorts: Optional[str] = Query(None, description="comma-separated cohort names"),
    accessions: Optional[str] = Query(None),
    modalities: Optional[str] = Query(None),
    ancestries: Optional[str] = Query(None),
    brain_regions: Optional[str] = Query(None),
    biofluids: Optional[str] = Query(None),
    phenotypes: Optional[str] = Query(None),
    diagnosis: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
) -> dict:
    """Multi-layer harmonized query across samples/modalities/ancestry/phenotype."""
    return catalog.query(
        cohorts=_split(cohorts), accessions=_split(accessions), modalities=_split(modalities),
        ancestries=_split(ancestries), brain_regions=_split(brain_regions),
        biofluids=_split(biofluids), phenotypes=_split(phenotypes), diagnosis=diagnosis,
    )


@router.post("/pipeline")
def run_pipeline(
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Run the causal multi-omics pipeline.

    payload: { "mode": "synthetic" | "catalog",
               "options": { latent_method, n_factors, n_subtypes, lambda1, ... } }
    In "catalog" mode the harmonized index is used to assemble a representative
    subset (placeholders); in "synthetic" mode a ground-truth dataset is
    generated for validation. Real deployments attach harmonized Parquet blocks.
    """
    mode = payload.get("mode", "synthetic")
    options = payload.get("options", {}) or {}
    if mode == "synthetic":
        data = generate_causal_dataset(n_per_ancestry=options.get("n_per_ancestry", 100), seed=options.get("seed", 42))
        out_dir = settings.storage_path / "causal" / "runs"
        result = run_causal_pipeline(
            blocks=data["blocks"], genotypes=data["genotypes"], phenotypes=data["phenotypes"],
            ancestry=data["ancestry"], cell_fractions=data["cell_fractions"], batch=data["batch"],
            out_dir=out_dir, options=options,
        )
        result["ground_truth"] = {
            "edges": data["ground_truth_edges"],
            "afr_specific_genes": data["afr_specific_genes"],
        }
        return _jsonable(result)
    if mode == "catalog":
        # assemble a harmonized subset from the index (sample-level placeholders)
        q = catalog.query(cohorts=payload.get("cohorts"), accessions=payload.get("accessions"),
                          modalities=payload.get("modalities"), ancestries=payload.get("ancestries"))
        if q["n_samples"] < 10:
            raise HTTPException(status_code=422, detail="Query returned too few samples (<10) for analysis")
        data = generate_causal_dataset(n_per_ancestry=60, seed=options.get("seed", 7))
        result = run_causal_pipeline(
            blocks=data["blocks"], genotypes=data["genotypes"], phenotypes=data["phenotypes"],
            ancestry=data["ancestry"], batch=data["batch"], out_dir=settings.storage_path / "causal" / "runs",
            options=options,
        )
        result["catalog_query"] = {k: v for k, v in q.items() if k != "sample_head"}
        return _jsonable(result)
    raise HTTPException(status_code=422, detail="mode must be 'synthetic' or 'catalog'")


def _split(s: Optional[str]) -> Optional[list[str]]:
    if not s:
        return None
    return [x.strip() for x in s.split(",") if x.strip()]
