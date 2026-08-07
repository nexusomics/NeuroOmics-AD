"""Celery tasks: long-running analysis jobs with progress tracking.

Tasks update the `Analysis` / step rows in the database so the web UI can
poll status & progress. When `TASK_ALWAYS_EAGER=true` (dev), they run inline.
"""
from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.analysis import Analysis, AnalysisStep, ResultArtifact
from app.utils.files import artifact_dir

logger = logging.getLogger(__name__)


def _update_analysis(analysis_id: str, **kwargs) -> None:
    db = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        if analysis:
            for k, v in kwargs.items():
                setattr(analysis, k, v)
            db.commit()
    finally:
        db.close()


def _add_step(analysis_id: str, step_name: str, message: str = "", duration: float = 0.0) -> None:
    db = SessionLocal()
    try:
        step = AnalysisStep(analysis_id=analysis_id, step_name=step_name, status="completed",
                            message=message, duration_seconds=duration,
                            started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc))
        db.add(step)
        db.commit()
    finally:
        db.close()


def _save_artifact(analysis_id: str, name: str, kind: str, fmt: str, path: Path, metadata: dict | None = None) -> None:
    db = SessionLocal()
    try:
        db.add(ResultArtifact(analysis_id=analysis_id, name=name, kind=kind, format=fmt,
                              file_path=str(path), size_bytes=path.stat().st_size if path.exists() else 0,
                              metadata_json=metadata or {}))
        db.commit()
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_analysis_task", bind=True, track_started=True)
def run_analysis_task(self, analysis_id: str) -> dict:
    """Dispatch an analysis to the appropriate service based on its type.

    Failure handling: the analysis row is marked `failed` with a readable
    error_message, and the task returns a failure payload WITHOUT re-raising —
    so in eager mode (dev/Render free tier) the API returns the created
    analysis (201) instead of a 500, while Celery still records FAILURE state
    for monitoring.
    """
    from app.core.database import init_db
    from app.services.analysis_dispatch import dispatch_analysis

    init_db()
    db = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        if not analysis:
            raise ValueError(f"analysis {analysis_id} not found")
        _update_analysis(analysis_id, status="running", started_at=datetime.now(timezone.utc), progress=5)
        result = dispatch_analysis(analysis, db, progress_cb=lambda p: _update_analysis(analysis_id, progress=p))
        _update_analysis(analysis_id, status="completed", progress=100, finished_at=datetime.now(timezone.utc))
        return {"analysis_id": analysis_id, "status": "completed", "result": result}
    except Exception as exc:  # noqa: BLE001
        logger.error("analysis %s failed: %s\n%s", analysis_id, exc, traceback.format_exc())
        _update_analysis(analysis_id, status="failed", error_message=str(exc)[:2000], finished_at=datetime.now(timezone.utc))
        try:
            self.update_state(state="FAILURE", meta={"error": str(exc)[:2000]})
        except Exception:  # noqa: BLE001
            pass
        return {"analysis_id": analysis_id, "status": "failed", "error": str(exc)[:2000]}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_drug_pipeline_task", bind=True, track_started=True)
def run_drug_pipeline_task(self, project_id: str, gene_list: list[str], config: dict) -> dict:
    from app.drugs.pipeline import run_drug_pipeline
    from app.core.database import init_db
    from app.models.drug import DrugCandidate

    init_db()
    direction = config.get("direction")
    result = run_drug_pipeline(
        gene_list=gene_list,
        direction=direction,
        weights=config.get("weights"),
        max_candidates=config.get("max_candidates", 50),
        require_bbb_positive=config.get("require_bbb_positive", False),
        min_clinical_phase=config.get("min_clinical_phase", "preclinical"),
        sources=config.get("sources"),
    )
    # persist top candidates
    db = SessionLocal()
    try:
        for i, c in enumerate(result["candidates"], start=1):
            db.add(DrugCandidate(
                project_id=project_id,
                drug_name=c["drug_name"],
                drugbank_id=c.get("drugbank_id", ""),
                chebi_id=c.get("chebi_id", ""),
                pubchem_cid=c.get("pubchem_cid", ""),
                mol_formula="",
                mol_weight=c.get("mw", 0.0),
                mechanism=c.get("mechanism", ""),
                targets=c.get("targets", []),
                indication=c.get("indication", ""),
                fda_status=c.get("fda_status", ""),
                evidence_sources=c.get("evidence_sources", []),
                score_network=c["scores"]["network"],
                score_pathway_reversal=c["scores"]["pathway_reversal"],
                score_target_overlap=c["scores"]["target_overlap"],
                score_bbb=c["scores"]["bbb"],
                score_admet=c["scores"]["admet"],
                score_clinical=c["scores"]["clinical"],
                composite_score=c["composite_score"],
                rank=i,
                details={"rationale": c.get("evidence", []), "scores_normalized": c.get("scores_normalized", {})},
            ))
        db.commit()
    finally:
        db.close()
    return result


@celery_app.task(name="app.workers.tasks.generate_report_task", bind=True, track_started=True)
def generate_report_task(self, report_payload: dict) -> dict:
    """Generate a multi-format report from stored analysis artifacts."""
    from app.core.database import init_db
    from app.services.report_builder import build_report_from_analyses

    init_db()
    out_dir = artifact_dir(report_payload.get("analysis_ids", ["batch"])[0])
    produced = build_report_from_analyses(
        analysis_ids=report_payload["analysis_ids"],
        formats=report_payload.get("formats", ["pdf", "docx"]),
        out_dir=out_dir,
        title=report_payload.get("title"),
        dpi=report_payload.get("dpi", 300),
        include_code=report_payload.get("include_code", False),
    )
    return {"files": produced, "status": "completed"}
