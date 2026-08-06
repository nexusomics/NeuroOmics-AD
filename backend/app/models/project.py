"""Project models (project container + memberships)."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    disease = Column(String(64), default="Alzheimer's disease")  # extensible: PD, ALS, HD, cancer
    species = Column(String(64), default="Homo sapiens")
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(32), default="active")  # active | archived
    created_at = Column(DateTime(timezone=True), default=dt.datetime.now(dt.timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=dt.datetime.now(dt.timezone.utc), onupdate=dt.datetime.now(dt.timezone.utc))

    members = relationship("ProjectMembership", back_populates="project", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="project", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="project", cascade="all, delete-orphan")
    drug_candidates = relationship("DrugCandidate", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "disease": self.disease,
            "species": self.species,
            "owner_id": self.owner_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProjectMembership(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    id = Column(String(36), primary_key=True, default=_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role = Column(String(32), default="member")  # owner | member | viewer
    added_at = Column(DateTime(timezone=True), default=dt.datetime.now(dt.timezone.utc))

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="projects")
