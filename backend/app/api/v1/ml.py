"""Machine-learning endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.ml.train import SUPPORTED_ALGORITHMS, train_models
from app.schemas.ml import MLTrainingRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml", tags=["machine-learning"])


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


@router.post("/train")
def train_endpoint(payload: MLTrainingRequest, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)) -> dict:
    matrix, metadata = _load(db, payload.dataset_id)
    if metadata is None or payload.label_column not in metadata.columns:
        raise HTTPException(status_code=422, detail=f"label column '{payload.label_column}' not found in metadata")
    labels = metadata[payload.label_column]
    for algo in payload.algorithms:
        if algo not in SUPPORTED_ALGORITHMS and algo != "gnn":
            raise HTTPException(status_code=422, detail=f"unsupported algorithm '{algo}' (use {SUPPORTED_ALGORITHMS + ['gnn']})")
    result = train_models(
        matrix, labels,
        algorithms=payload.algorithms, test_size=payload.test_size, cv_folds=payload.cv_folds,
        feature_selection=payload.feature_selection, top_features=payload.top_features,
        gnn=payload.gnn, hyperparameters=payload.hyperparameters,
    )
    return result


@router.get("/algorithms")
def list_algorithms() -> dict:
    return {
        "classification": {
            "random_forest": "Ensemble of decision trees; robust feature interactions",
            "xgboost": "Gradient-boosted trees; state-of-the-art tabular performance",
            "svm": "Support vector machine with RBF kernel; strong on small samples",
            "dnn": "Deep neural network (MLP); captures non-linear biomarker patterns",
            "gnn": "Graph convolutional network over the gene-interaction graph",
        },
        "short_names": SUPPORTED_ALGORITHMS + ["gnn"],
    }


@router.get("/trained")
def list_trained(user: User = Depends(get_current_user)) -> dict:
    """List trained models stored in the ML cache directory."""
    from app.core.config import settings

    cache_dir = settings.storage_path / ".mlcache"
    models = []
    if cache_dir.exists():
        for d in sorted(cache_dir.iterdir()):
            meta_file = d / "metadata.json"
            if meta_file.exists():
                import json

                try:
                    meta = json.loads(meta_file.read_text())
                    models.append({"key": meta.get("key"), "algorithm": meta.get("algorithm"),
                                   "metrics": meta.get("metrics", {}), "artifact_path": str(d / "model.joblib")})
                except Exception:  # noqa: BLE001
                    continue
    return {"models": models, "n": len(models)}
