"""Dataset upload & management endpoints."""
from __future__ import annotations

import logging
import pandas as pd

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_project_for_user
from app.core.database import get_db
from app.models.dataset import Dataset, DatasetSample
from app.models.user import User
from app.schemas.dataset import DatasetOut, OMICS_TYPES
from app.services.io import load_expression_matrix, resolve_dataset_path
from app.utils.files import save_upload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetOut])
def list_datasets(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Dataset]:
    get_project_for_user(project_id, user, db)
    return db.query(Dataset).filter(Dataset.project_id == project_id).order_by(Dataset.created_at.desc()).all()


@router.post("", response_model=DatasetOut, status_code=201)
async def upload_dataset(
    project_id: str = Form(...),
    name: str = Form(...),
    omics_type: str = Form(...),
    platform: str = Form(""),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dataset:
    get_project_for_user(project_id, user, db)
    if omics_type not in OMICS_TYPES:
        raise HTTPException(status_code=422, detail=f"omics_type must be one of {OMICS_TYPES}")
    content = await file.read()
    path, stored = save_upload(content, file.filename or "data.csv")
    ds = Dataset(
        project_id=project_id, name=name, omics_type=omics_type, platform=platform,
        file_path=str(path), format=path.suffix.lstrip(".").lower(), uploaded_by=user.id,
    )
    try:
        df = load_expression_matrix(str(path))
        ds.n_samples = int(df.shape[1])
        ds.n_features = int(df.shape[0])
        ds.status = "ready"
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not parse uploaded file %s: %s", file.filename, exc)
        ds.status = "uploaded"
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dataset:
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    get_project_for_user(ds.project_id, user, db)
    return ds


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    get_project_for_user(ds.project_id, user, db)
    db.delete(ds)
    db.commit()
    return {"message": "Dataset deleted"}


@router.post("/{dataset_id}/preview")
def preview_dataset(dataset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    get_project_for_user(ds.project_id, user, db)
    try:
        df = load_expression_matrix(ds.file_path)
        return {
            "shape": {"rows": int(df.shape[0]), "cols": int(df.shape[1])},
            "index": list(df.index[:20]),
            "columns": list(df.columns[:20]),
            "head": df.iloc[:5, :5].round(3).values.tolist(),
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Cannot preview dataset: {exc}") from exc
