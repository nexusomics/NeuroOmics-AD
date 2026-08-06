"""Report generator: converts structured analysis results into multi-format reports."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from app.reports.formats.writers import write_csv, write_docx, write_html, write_pdf, write_pptx, write_xlsx
from app.reports.model import ReportData, ReportFigure, ReportSection, ReportTable

logger = logging.getLogger(__name__)

DEFAULT_REFERENCES = [
    "Love MI, Huber W, Anders S (2014). Moderated estimation of fold change and dispersion for RNA-seq data with DESeq2. Genome Biology 15:550.",
    "Ritchie ME, Phipson B, Wu D, et al. (2015). limma powers differential expression analyses for RNA-sequencing and microarray studies. Nucleic Acids Research 43:e47.",
    "Johnson WE, Li C, Rabinovic A (2007). Adjusting batch effects in microarray expression data using empirical Bayes methods. Biostatistics 8:118–127.",
    "Subramanian A, et al. (2017). A Next Generation Connectivity Map: L1000 platform and the first 1,000,000 profiles. Cell 171:1437–1452.",
    "Menche J, et al. (2015). Uncovering disease-disease relationships through the incomplete interactome. Science 347:1257601.",
    "Newman AM, et al. (2015). Robust enumeration of cell subsets from tissue expression profiles. Nature Methods 12:453–457.",
    "Benjamini Y, Hochberg Y (1995). Controlling the false discovery rate: a practical and powerful approach to multiple testing. JRSS-B 57:289–300.",
    "Wang B, et al. (2014). Similarity network fusion for aggregating data types on a genomic scale. Nature Methods 11:333–337.",
    "Smyth GK (2004). Linear models and empirical Bayes methods for assessing differential expression in microarray experiments. Statistical Applications in Genetics and Molecular Biology 3:Article3.",
    "Szklarczyk D, et al. (2023). The STRING database in 2023. Nucleic Acids Research 51:D923–D931.",
]


def build_report(
    title: str,
    subtitle: str,
    sections: list[dict],
    tables: list[dict],
    figures: list[dict],
    references: Optional[list[str]] = None,
    metadata: Optional[dict] = None,
) -> ReportData:
    """Build a ReportData object from plain dicts.

    sections: [{title, paragraphs: [...], subsections: [...]}]
    tables:   [{name, data: pd.DataFrame, caption}]
    figures:  [{name, path, caption}]
    """
    report = ReportData(
        title=title,
        subtitle=subtitle,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        references=references or DEFAULT_REFERENCES,
        metadata=metadata or {},
    )
    for sec in sections:
        s = report.add_section(sec.get("title", ""), sec.get("paragraphs", []))
        for sub in sec.get("subsections", []):
            s.subsections.append(ReportSection(sub.get("title", ""), sub.get("paragraphs", [])))
    for t in tables:
        report.tables.append(ReportTable(t["name"], t["data"], t.get("caption", "")))
    for fig in figures:
        report.figures.append(ReportFigure(fig["name"], fig["path"], fig.get("caption", "")))
    return report


def generate_report(report: ReportData, formats: list[str], out_dir: Path, dpi: int = 300, include_code: bool = False) -> dict[str, str]:
    """Write the report in all requested formats; returns {format: path}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    produced: dict[str, str] = {}
    for fmt in formats:
        try:
            if fmt == "csv":
                paths = write_csv(report, out_dir)
                produced[fmt] = str(paths[0]) if paths else ""
            elif fmt == "xlsx":
                produced[fmt] = str(write_xlsx(report, out_dir))
            elif fmt == "docx":
                produced[fmt] = str(write_docx(report, out_dir, include_code))
            elif fmt == "pptx":
                produced[fmt] = str(write_pptx(report, out_dir))
            elif fmt == "pdf":
                produced[fmt] = str(write_pdf(report, out_dir, dpi))
            elif fmt == "html":
                produced[fmt] = str(write_html(report, out_dir))
            else:
                logger.warning("unsupported format %s", fmt)
        except Exception as exc:  # noqa: BLE001
            logger.error("failed to write %s report: %s", fmt, exc)
    return produced
