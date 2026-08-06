"""User & role models."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False, default="")
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="researcher")  # researcher | admin | reviewer
    organization = Column(String(255), default="")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=dt.datetime.now(dt.timezone.utc))
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    projects = relationship("ProjectMembership", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "organization": self.organization,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
