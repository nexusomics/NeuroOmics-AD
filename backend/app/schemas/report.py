"""Report generation schemas."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

REPORT_FORMATS = ["pdf", "docx", "pptx", "xlsx", "csv", "html"]


class ReportRequest(BaseModel):
    analysis_ids: list[str] = Field(..., min_length=1)
    formats: list[str] = Field(default_factory=lambda: ["pdf", "docx"])
    title: Optional[str] = None
    include_code: bool = False
    dpi: int = 300


class ReportOut(BaseModel):
    id: str
    analysis_id: str
    formats: list[str]
    files: dict[str, str]  # format -> artifact path
    status: str
