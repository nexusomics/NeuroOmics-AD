"""Audit log model."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, Column, DateTime, String

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), index=True, default="")
    action = Column(String(64), nullable=False)
    resource_type = Column(String(64), default="")
    resource_id = Column(String(36), default="")
    details = Column(JSON, default=dict)
    ip_address = Column(String(64), default="")
    created_at = Column(DateTime(timezone=True), default=dt.datetime.now(dt.timezone.utc))
