"""Analysis run management endpoints (create, status, artifacts, download)."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_project_for_user
from app.core.database import get_db
from app.models.analysis import Analysis, ResultArtifact
from app.models.user import User
from app.schemas.analysis import AnalysisCreate, AnalysisOut, ArtifactOut
from app.workers.tasks import run_analysis_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.get("", response_model=list[AnalysisOut])
def list_analyses(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Analysis]:
    get_project_for_user(project_id, user, db)
    return db.query(Analysis).filter(Analysis.project_id == project_id).order_by(Analysis.created_at.desc()).all()


@router.post("/{project_id}/create", response_model=AnalysisOut, status_code=201)
def create_analysis_in_project(project_id: str, payload: AnalysisCreate, user: User = Depends(get_current_user),
                               db: Session = Depends(get_db)) -> Analysis:
    get_project_for_user(project_id, user, db)
    analysis = Analysis(
        project_id=project_id, name=payload.name, analysis_type=payload.analysis_type,
        config=payload.config, owner_id=user.id, status="queued",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    # dispatch to celery (eager in dev)
    run_analysis_task.delay(analysis.id)
    db.refresh(analysis)
    return analysis


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Analysis:
    analysis = _get_owned_analysis(analysis_id, user, db)
    return analysis


@router.get("/{analysis_id}/artifacts", response_model=list[ArtifactOut])
def list_artifacts(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ResultArtifact]:
    _get_owned_analysis(analysis_id, user, db)
    return db.query(ResultArtifact).filter(ResultArtifact.analysis_id == analysis_id).all()


@router.get("/{analysis_id}/result")
def get_result(analysis_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Fetch the JSON result payload of a completed analysis."""
    _get_owned_analysis(analysis_id, user, db)
    import json

    artifact = db.query(ResultArtifact).filter(ResultArtifact.analysis_id == analysis_id, ResultArtifact.kind == "json").first()
    if not artifact:
        return {"message": "No JSON result stored for this analysis"}
    p = Path(artifact.file_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Result file missing")
    return json.loads(p.read_text())


@router.get("/{analysis_id}/artifacts/{artifact_id}/download")
def download_artifact(analysis_id: str, artifact_id: str, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)) -> FileResponse:
    _get_owned_analysis(analysis_id, user, db)
    artifact = db.get(ResultArtifact, artifact_id)
    if not artifact or artifact.analysis_id != analysis_id:
        raise HTTPException(status_code=404, detail="Artifact not found")
    p = Path(artifact.file_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Artifact file missing")
    return FileResponse(p, filename=Path(artifact.file_path).name, media_type="application/octet-stream")


def _get_owned_analysis(analysis_id: str, user: User, db: Session) -> Analysis:
    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    get_project_for_user(analysis.project_id, user, db)
    return analysis
