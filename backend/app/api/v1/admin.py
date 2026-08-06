"""Admin endpoints: user management, system stats, audit log."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.auth import UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}")
def update_user_role(user_id: str, role: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    if role not in ("researcher", "admin", "reviewer"):
        raise HTTPException(status_code=422, detail="invalid role")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    db.add(AuditLog(user_id=admin.id, action="role_change", resource_type="user", resource_id=user_id,
                    details={"role": role}))
    db.commit()
    return {"message": f"Role updated to {role}"}


@router.get("/stats")
def stats(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    from sqlalchemy import func

    from app.models.analysis import Analysis
    from app.models.dataset import Dataset
    from app.models.project import Project

    return {
        "users": db.query(func.count(User.id)).scalar(),
        "projects": db.query(func.count(Project.id)).scalar(),
        "datasets": db.query(func.count(Dataset.id)).scalar(),
        "analyses": db.query(func.count(Analysis.id)).scalar(),
        "analyses_by_status": dict(db.query(Analysis.status, func.count()).group_by(Analysis.status).all()),
    }


@router.get("/audit")
def audit_log(limit: int = 100, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [{"id": r.id, "user_id": r.user_id, "action": r.action, "resource_type": r.resource_type,
             "resource_id": r.resource_id, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]
