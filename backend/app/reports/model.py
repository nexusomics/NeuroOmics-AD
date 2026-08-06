"""Report data model shared by all format writers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd


@dataclass
class ReportTable:
    name: str
    data: pd.DataFrame
    caption: str = ""


@dataclass
class ReportFigure:
    name: str
    path: str  # path to PNG/SVG
    caption: str = ""


@dataclass
class ReportSection:
    title: str
    paragraphs: list[str] = field(default_factory=list)
    subsections: list["ReportSection"] = field(default_factory=list)


@dataclass
class ReportData:
    title: str
    subtitle: str = ""
    generated_at: str = ""
    tool_version: str = "NeuroOmics-AD 1.0.0"
    sections: list[ReportSection] = field(default_factory=list)
    tables: list[ReportTable] = field(default_factory=list)
    figures: list[ReportFigure] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_section(self, title: str, paragraphs: list[str] | None = None) -> ReportSection:
        sec = ReportSection(title=title, paragraphs=paragraphs or [])
        self.sections.append(sec)
        return sec
