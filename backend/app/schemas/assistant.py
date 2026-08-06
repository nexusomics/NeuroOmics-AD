"""AI research assistant schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class AssistantMessage(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str


class AssistantRequest(BaseModel):
    message: str
    project_id: Optional[str] = None
    analysis_ids: list[str] = []
    history: list[AssistantMessage] = []
    temperature: Optional[float] = None


class AssistantResponse(BaseModel):
    reply: str
    mode: str  # local | llm
    context: dict[str, Any] = {}
    model: str = ""


class ManuscriptRequest(BaseModel):
    analysis_ids: list[str] = Field(..., min_length=1)
    journal_style: str = "nature-medicine"
    include_discussion: bool = True
    include_methods: bool = True
