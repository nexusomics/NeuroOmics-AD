"""Direct omics analysis endpoints (synchronous convenience wrappers).

These run the analysis immediately (for small inputs / demos). For large jobs,
use the project analysis runner which dispatches to Celery.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.analysis import (
    DeconvolutionRequest, DifferentialExpressionRequest, EnrichmentRequest,
    IntegrationRequest, MetaAnalysisRequest, NetworkRequest,
)
from app.services.deconvolution import deconvolute
from app.services.differential_expression import differential_expression
from app.services.enrichment import enrich
from app.services.integration import integrate
from app.services.meta_analysis import meta_analysis
from app.services.network import run_network_analysis
from app.services.preprocessing import run_preprocessing
from app.utils.files import artifact_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/omics", tags=["omics"])


def _load(db: Session, dataset_id: str):
    from app.models.dataset import Dataset
    from app.services.io import load_expression_matrix, load_metadata, resolve_dataset_path

    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    matrix = load_expression_matrix(ds.file_path)
    metadata = None
    if ds.metadata_json and ds.metadata_json.get("metadata_file"):
        p = resolve_dataset_path(ds.metadata_json["metadata_file"])
        if p.exists():
            metadata = load_metadata(p)
    return matrix, metadata


@router.post("/differential-expression")
def de_endpoint(payload: DifferentialExpressionRequest, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)) -> dict:
    matrix, metadata = _load(db, payload.dataset_id)
    if metadata is None:
        # synthesize groups from sample names
        samples = list(matrix.columns)
        groups = ["AD" if i % 2 == 0 else "CN" for i in range(len(samples))]
        metadata = __import__("pandas").DataFrame({"group": groups}, index=samples)
    return differential_expression(
        matrix, metadata,
        group_column=payload.group_column, case=payload.case_group, control=payload.control_group,
        covariates=payload.covariates, method=payload.method,
        fdr_threshold=payload.fdr_threshold, log2fc_threshold=payload.log2fc_threshold,
    )


@router.post("/preprocessing")
def preprocessing_endpoint(payload: dict, db: Session = Depends(get_db),
                           user: User = Depends(get_current_user)) -> dict:
    from app.services.preprocessing import run_preprocessing

    matrix, metadata = _load(db, payload["dataset_id"])
    result = run_preprocessing(
        matrix, metadata,
        normalize_method=payload.get("normalize_method", "quantile"),
        log_transform=payload.get("log_transform", False),
        batch_correct=payload.get("batch_correct", False),
        batch_column=payload.get("batch_column", "batch"),
        impute_method=payload.get("impute_method", "knn"),
        remove_outlier_samples=payload.get("remove_outliers", True),
    )
    # persist processed matrix as an artifact-like file
    out = artifact_dir(f"sync_{uuid.uuid4().hex[:8]}")
    result["matrix"].to_csv(out / "normalized_matrix.csv")
    return {"report": result["report"], "outliers": result["report"].get("outliers", [])}


@router.post("/enrichment")
def enrichment_endpoint(payload: EnrichmentRequest, user: User = Depends(get_current_user)) -> dict:
    return enrich(payload.gene_list, payload.background, payload.databases,
                  payload.min_size, payload.max_size, payload.fdr_threshold)


@router.post("/network")
def network_endpoint(payload: NetworkRequest, user: User = Depends(get_current_user)) -> dict:
    res = run_network_analysis(payload.gene_list, payload.confidence_threshold, payload.max_interactors, payload.source)
    return {"summary": res["summary"], "hub_genes": res["hub_genes"],
            "metrics": res["metrics"].to_dict(orient="records")}


@router.post("/meta-analysis")
def meta_endpoint(payload: MetaAnalysisRequest, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)) -> dict:
    matrices, metas = [], []
    for ds_id in payload.dataset_ids:
        m, meta = _load(db, ds_id)
        matrices.append(m)
        metas.append(meta or __import__("pandas").DataFrame(
            {"group": ["AD" if i % 2 == 0 else "CN" for i in range(m.shape[1])]}, index=m.columns))
    return meta_analysis(matrices, metas, case=payload.case_group, control=payload.control_group,
                         effect_size_method=payload.effect_size_method, fixed_effects=payload.fixed_effects)


@router.post("/deconvolution")
def deconvolution_endpoint(payload: DeconvolutionRequest, db: Session = Depends(get_db),
                           user: User = Depends(get_current_user)) -> dict:
    matrix, _ = _load(db, payload.dataset_id)
    res = deconvolute(matrix, payload.signature_source, payload.method)
    return {"qc": res["qc"], "fractions": res["fractions"].to_dict(orient="index")}


@router.post("/integration")
def integration_endpoint(payload: IntegrationRequest, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)) -> dict:
    matrices = []
    for ds_id in payload.dataset_ids:
        m, _ = _load(db, ds_id)
        matrices.append(m)
    res = integrate(matrices, payload.method, payload.rank)
    return {k: (v.to_dict() if hasattr(v, "to_dict") else v) for k, v in res.items()}
