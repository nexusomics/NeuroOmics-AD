"""Project management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_project_for_user
from app.core.database import get_db
from app.models.project import Project, ProjectMembership
from app.models.user import User
from app.schemas.project import MemberAdd, MemberOut, ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


def _list_projects(db: Session, user: User) -> list[Project]:
    owned = db.query(Project).filter(Project.owner_id == user.id).all()
    member_ids = [m.project_id for m in db.query(ProjectMembership).filter(ProjectMembership.user_id == user.id).all()]
    shared = db.query(Project).filter(Project.id.in_(member_ids)).all() if member_ids else []
    seen = {p.id: p for p in owned}
    for p in shared:
        seen.setdefault(p.id, p)
    return list(seen.values())


@router.get("", response_model=list[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Project]:
    return _list_projects(db, user)


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Project:
    project = Project(name=payload.name, description=payload.description, disease=payload.disease,
                      species=payload.species, owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    db.add(ProjectMembership(project_id=project.id, user_id=user.id, role="owner"))
    db.commit()
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Project:
    return get_project_for_user(project_id, user, db)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, payload: ProjectUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> Project:
    project = get_project_for_user(project_id, user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    project = get_project_for_user(project_id, user, db)
    if project.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the owner can delete the project")
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


@router.post("/{project_id}/members", response_model=MemberOut)
def add_member(project_id: str, payload: MemberAdd, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)) -> MemberOut:
    project = get_project_for_user(project_id, user, db)
    if project.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the owner can add members")
    member = db.query(User).filter(User.email == payload.email.lower()).first()
    if not member:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(ProjectMembership).filter(ProjectMembership.project_id == project_id,
                                                  ProjectMembership.user_id == member.id).first()
    if not existing:
        db.add(ProjectMembership(project_id=project_id, user_id=member.id, role=payload.role))
        db.commit()
    return MemberOut(user_id=member.id, email=member.email, full_name=member.full_name, role=payload.role)


@router.get("/{project_id}/members", response_model=list[MemberOut])
def list_members(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[MemberOut]:
    get_project_for_user(project_id, user, db)
    members = db.query(ProjectMembership).filter(ProjectMembership.project_id == project_id).all()
    out = []
    for m in members:
        u = db.get(User, m.user_id)
        if u:
            out.append(MemberOut(user_id=u.id, email=u.email, full_name=u.full_name, role=m.role))
    return out


@router.get("/{project_id}/summary")
def project_summary(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    get_project_for_user(project_id, user, db)
    from app.models.analysis import Analysis
    from app.models.dataset import Dataset
    from app.models.drug import DrugCandidate

    datasets = db.query(Dataset).filter(Dataset.project_id == project_id).count()
    analyses = db.query(Analysis).filter(Analysis.project_id == project_id).count()
    drugs = db.query(DrugCandidate).filter(DrugCandidate.project_id == project_id).count()
    by_type = dict(db.query(Analysis.analysis_type, func.count()).filter(Analysis.project_id == project_id).group_by(Analysis.analysis_type).all())
    return {"datasets": datasets, "analyses": analyses, "drug_candidates": drugs, "analyses_by_type": by_type}
