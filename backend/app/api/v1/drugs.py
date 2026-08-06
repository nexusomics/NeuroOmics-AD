"""Drug repurposing endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_project_for_user
from app.core.database import get_db
from app.drugs.knowledge import all_drugs, search_drugs
from app.drugs.pipeline import run_drug_pipeline
from app.models.drug import DrugCandidate
from app.models.user import User
from app.schemas.drug import DrugCombinationRequest, DrugPipelineRequest, DrugTargetMapRequest
from app.workers.tasks import run_drug_pipeline_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/drugs", tags=["drug-repurposing"])


@router.post("/pipeline")
def drug_pipeline(payload: DrugPipelineRequest, user: User = Depends(get_current_user)) -> dict:
    result = run_drug_pipeline(
        gene_list=payload.gene_list,
        weights=payload.weights,
        max_candidates=payload.max_candidates,
        require_bbb_positive=payload.require_bbb_positive,
        min_clinical_phase=payload.min_clinical_phase,
        sources=payload.sources,
    )
    return result


@router.post("/pipeline/{project_id}/save", status_code=201)
def run_and_save_drug_pipeline(project_id: str, payload: DrugPipelineRequest,
                               user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    get_project_for_user(project_id, user, db)
    result = run_drug_pipeline_task.run(
        project_id=project_id,
        gene_list=payload.gene_list,
        config=payload.model_dump(),
    )
    return {"task": "completed", "n_candidates": len(result.get("candidates", []))}


@router.get("/candidates")
def list_candidates(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    get_project_for_user(project_id, user, db)
    rows = db.query(DrugCandidate).filter(DrugCandidate.project_id == project_id).order_by(DrugCandidate.rank).all()
    return [r.to_dict() for r in rows]


@router.post("/drug-target-map")
def drug_target_map(payload: DrugTargetMapRequest, user: User = Depends(get_current_user)) -> dict:
    """Build drug–target interaction map (Sankey + table) for a gene list."""
    from app.drugs.knowledge import all_drugs
    from app.drugs.ranking import build_sankey

    genes = {g.upper() for g in payload.gene_list}
    hits = []
    for key, rec in all_drugs().items():
        overlap = [t for t in rec.get("targets", []) if t in genes]
        if overlap:
            hits.append({"drug": rec["name"], "targets": overlap, "mechanism": rec.get("mechanism", "")})
    dummy = [{"drug_name": h["drug"], "targets": h["targets"], "composite_score": 1.0} for h in hits]
    sankey = build_sankey(dummy) if dummy else {"nodes": ["Disease module"], "links": [], "node_labels": ["Disease module"]}
    return {"hits": hits, "n_drugs": len(hits), "sankey": sankey}


@router.post("/combinations")
def drug_combinations(payload: DrugCombinationRequest, user: User = Depends(get_current_user)) -> dict:
    result = run_drug_pipeline(gene_list=payload.gene_list, max_candidates=payload.top_n)
    return {"combinations": result["combinations"], "candidates": result["candidates"][:payload.top_n]}


@router.get("/search")
def search(query: str, user: User = Depends(get_current_user)) -> list[dict]:
    hits = search_drugs(query)
    return [{"drug_name": h["name"], "drugbank_id": h.get("drugbank_id"), "mechanism": h.get("mechanism"),
             "targets": h.get("targets"), "fda_status": h.get("fda_status")} for h in hits]


@router.get("/knowledge-base")
def knowledge_base(user: User = Depends(get_current_user)) -> dict:
    drugs = all_drugs()
    return {"n_drugs": len(drugs), "drugs": [{"key": k, "name": v["name"], "targets": v["targets"],
                                              "fda_status": v["fda_status"]} for k, v in drugs.items()]}
