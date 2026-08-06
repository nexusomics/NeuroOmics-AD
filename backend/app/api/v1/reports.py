"""Report generation endpoints."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.report import ReportRequest
from app.services.report_builder import build_report_from_analyses
from app.utils.files import artifact_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate")
def generate(payload: ReportRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Generate a multi-format report from the given analyses."""
    from app.models.analysis import Analysis

    for aid in payload.analysis_ids:
        if db.get(Analysis, aid) is None:
            raise HTTPException(status_code=404, detail=f"analysis {aid} not found")
    out_dir = artifact_dir(payload.analysis_ids[0]) / "reports"
    produced = build_report_from_analyses(
        analysis_ids=payload.analysis_ids,
        formats=payload.formats,
        out_dir=out_dir,
        title=payload.title,
        dpi=payload.dpi,
        include_code=payload.include_code,
    )
    return {"files": produced, "status": "completed"}


@router.get("/download/{analysis_id}/{filename}")
def download(analysis_id: str, filename: str, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)) -> FileResponse:
    from app.models.analysis import Analysis

    analysis = db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    p = artifact_dir(analysis_id) / "reports" / filename
    if not p.exists():
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(p, filename=filename)


@router.get("/formats")
def formats() -> dict:
    return {"formats": ["pdf", "docx", "pptx", "xlsx", "csv", "html"],
            "dpi": "300–600", "note": "Publication-quality static figures embedded in PDF/Word/HTML/PPTX"}
