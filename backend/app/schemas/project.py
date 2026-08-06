"""Project schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    disease: str = "Alzheimer's disease"
    species: str = "Homo sapiens"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    disease: Optional[str] = None
    species: Optional[str] = None
    status: Optional[str] = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    disease: str
    species: str
    owner_id: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MemberAdd(BaseModel):
    email: str
    role: str = "member"


class MemberOut(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
