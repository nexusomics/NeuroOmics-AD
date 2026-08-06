"""Shared FastAPI dependencies: auth, RBAC, database session."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.project import Project, ProjectMembership
from app.models.user import User


def get_current_user(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token, expected_type="access")
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


def get_project_for_user(project_id: str, user: User, db: Session) -> Project:
    """Fetch a project, enforcing membership."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id and user.role != "admin":
        membership = db.query(ProjectMembership).filter(
            ProjectMembership.project_id == project_id, ProjectMembership.user_id == user.id).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Not a member of this project")
    return project
