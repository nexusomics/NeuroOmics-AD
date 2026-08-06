"""Build structured reports from stored analysis results & artifacts."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from app.core.database import SessionLocal
from app.models.analysis import Analysis, ResultArtifact
from app.reports.generator import build_report, generate_report
from app.reports.model import ReportData

logger = logging.getLogger(__name__)

_TYPE_LABELS = {
    "differential_expression": "Differential Expression Analysis",
    "preprocessing": "Data Harmonization & Quality Control",
    "enrichment": "Pathway Enrichment Analysis",
    "network": "Protein–Protein Interaction Network Analysis",
    "meta_analysis": "Cross-Cohort Meta-Analysis",
    "deconvolution": "Cell-Type Deconvolution",
    "integration": "Multi-Omics Integration",
    "ml": "Machine Learning Analysis",
    "single_cell": "Single-Cell Analysis",
    "genomics": "Genomics / GWAS Analysis",
    "epigenomics": "Epigenomics Analysis",
    "clinical": "Clinical Analysis",
    "drug_repurposing": "Drug Repurposing",
}


def _load_analysis(db, analysis_id: str) -> Analysis | None:
    return db.get(Analysis, analysis_id)


def _json_result(analysis: Analysis) -> dict:
    """Reconstruct the JSON result payload from the stored json artifact."""
    db = SessionLocal()
    try:
        arts = db.query(ResultArtifact).filter(ResultArtifact.analysis_id == analysis.id, ResultArtifact.kind == "json").all()
        for a in arts:
            p = Path(a.file_path)
            if p.exists():
                return json.loads(p.read_text())
    finally:
        db.close()
    return {}


def _figure_artifacts(analysis_id: str) -> list[dict]:
    db = SessionLocal()
    try:
        arts = db.query(ResultArtifact).filter(ResultArtifact.analysis_id == analysis_id, ResultArtifact.kind == "figure").all()
        return [{"name": a.name, "path": a.file_path, "caption": f"{a.name} — {_TYPE_LABELS.get(analysis_id, '')}".strip()} for a in arts]
    finally:
        db.close()


def build_report_from_analyses(
    analysis_ids: list[str],
    formats: list[str],
    out_dir: Path,
    title: str | None = None,
    dpi: int = 300,
    include_code: bool = False,
) -> dict[str, str]:
    """Assemble a multi-analysis report and generate all requested formats."""
    db = SessionLocal()
    try:
        analyses = [a for aid in analysis_ids if (a := _load_analysis(db, aid)) is not None]
        if not analyses:
            raise ValueError("no valid analyses found")
    finally:
        db.close()

    sections: list[dict] = []
    tables: list[dict] = []
    figures: list[dict] = []
    references: list[str] = []

    for analysis in analyses:
        res = _json_result(analysis)
        label = _TYPE_LABELS.get(analysis.analysis_type, analysis.analysis_type.replace("_", " ").title())
        paragraphs: list[str] = [f"Analysis: {analysis.name} ({label}). Status: {analysis.status}."]
        if analysis.analysis_type in ("differential_expression", "de") and res.get("summary"):
            s = res["summary"]
            paragraphs.append(
                f"{s.get('tested_genes', 0)} genes tested; {s.get('significant', 0)} significant "
                f"({s.get('upregulated', 0)} up / {s.get('downregulated', 0)} down); method: {s.get('method')}.")
        if analysis.analysis_type == "meta_analysis" and res.get("summary"):
            s = res["summary"]
            paragraphs.append(f"Meta-analysis across {s.get('cohorts', 0)} cohorts ({s.get('method')}); "
                              f"{s.get('significant', 0)} genes significant; median I² = {s.get('median_i2')}.")
        if analysis.analysis_type == "network" and res.get("summary"):
            s = res["summary"]
            paragraphs.append(f"Network: {s.get('n_nodes')} nodes, {s.get('n_edges')} edges, "
                              f"{s.get('n_modules')} modules; hubs: {', '.join(s.get('hub_genes', [])[:8])}.")
        if analysis.analysis_type == "ml" and res.get("results"):
            for m in res["results"][:6]:
                met = m.get("metrics", {})
                paragraphs.append(f"{m.get('algorithm')}: accuracy {met.get('accuracy', 0):.3f}, "
                                  f"ROC-AUC {met.get('roc_auc', 0):.3f}.")
        if analysis.analysis_type == "drug_repurposing" and res.get("candidates"):
            for c in res["candidates"][:8]:
                paragraphs.append(f"#{c.get('rank')} {c.get('drug_name')} — {c.get('mechanism')} "
                                  f"(composite {c.get('composite_score', 0):.3f}); " + "; ".join(c.get("evidence", [])[:2]))
        if analysis.analysis_type == "enrichment" and res.get("table"):
            for e in res["table"][:6]:
                paragraphs.append(f"{e.get('pathway')}: FDR {e.get('fdr', 1):.2e}, "
                                  f"overlap {e.get('overlap_size')}/{e.get('set_size')} genes.")
        sections.append({"title": label, "paragraphs": paragraphs})

        # tables from csv artifacts
        db2 = SessionLocal()
        try:
            arts = db2.query(ResultArtifact).filter(ResultArtifact.analysis_id == analysis.id, ResultArtifact.kind == "table").all()
            for a in arts:
                p = Path(a.file_path)
                if p.exists() and a.format == "csv":
                    df = pd.read_csv(p)
                    if len(df):
                        tables.append({"name": a.name, "data": df, "caption": f"Output of {label}"})
            figures.extend(_figure_artifacts(analysis.id))
        finally:
            db2.close()

    report: ReportData = build_report(
        title=title or "NeuroOmics-AD Analysis Report",
        subtitle="Automatically generated multi-omics analysis report",
        sections=sections,
        tables=tables,
        figures=figures,
        references=references or None,
        metadata={"analyses": [a.id for a in analyses]},
    )
    return generate_report(report, formats, out_dir, dpi=dpi, include_code=include_code)
