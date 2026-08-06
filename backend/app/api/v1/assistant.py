"""AI research assistant endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.assistant.engine import ask, draft_manuscript
from app.core.database import get_db
from app.models.analysis import Analysis
from app.models.project import Project
from app.models.user import User
from app.schemas.assistant import AssistantRequest, ManuscriptRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["ai-assistant"])


def _load_analysis_results(db: Session, analysis_ids: list[str]) -> list[dict]:
    """Load JSON results for the referenced analyses, tagged by type."""
    import json
    from pathlib import Path

    out = []
    for aid in analysis_ids:
        analysis = db.get(Analysis, aid)
        if not analysis:
            continue
        from app.models.analysis import ResultArtifact

        artifact = db.query(ResultArtifact).filter(ResultArtifact.analysis_id == aid, ResultArtifact.kind == "json").first()
        payload = {}
        if artifact and Path(artifact.file_path).exists():
            try:
                payload = json.loads(Path(artifact.file_path).read_text())
            except Exception:  # noqa: BLE001
                payload = {}
        out.append({"type": analysis.analysis_type, "analysis_id": aid, "name": analysis.name, "result": payload})
    return out


@router.post("/chat")
def chat(payload: AssistantRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    project_name, disease = "", ""
    if payload.project_id:
        project = db.get(Project, payload.project_id)
        if project:
            project_name, disease = project.name, project.disease
    results = _load_analysis_results(db, payload.analysis_ids)
    response = ask(
        message=payload.message,
        project_name=project_name,
        disease=disease,
        analysis_results=results,
        history=[m.model_dump() for m in payload.history],
        temperature=payload.temperature,
    )
    return response


@router.post("/manuscript")
def manuscript(payload: ManuscriptRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    results = _load_analysis_results(db, payload.analysis_ids)
    project = None
    for r in results:
        a = db.get(Analysis, r["analysis_id"])
        if a:
            project = db.get(Project, a.project_id)
            break
    return draft_manuscript(
        project_name=project.name if project else "NeuroOmics-AD study",
        disease=project.disease if project else "Alzheimer's disease",
        analysis_results=results,
        include_discussion=payload.include_discussion,
        include_methods=payload.include_methods,
    )


@router.get("/mode")
def assistant_mode(user: User = Depends(get_current_user)) -> dict:
    from app.core.config import settings

    return {"mode": settings.ASSISTANT_MODE, "model": settings.ASSISTANT_MODEL}
