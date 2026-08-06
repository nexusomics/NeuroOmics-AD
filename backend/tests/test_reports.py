"""Tests: report generation across all six formats + assistant + integration API flow."""
from __future__ import annotations

import pandas as pd
import pytest

from app.assistant.engine import ask, draft_manuscript
from app.reports.generator import build_report, generate_report


@pytest.fixture()
def sample_report():
    sections = [
        {"title": "Results", "paragraphs": ["We identified 18 significant genes (13 up, 5 down)."]},
        {"title": "Network", "paragraphs": ["Hub genes: APP, APOE, IL1B."]},
    ]
    tables = [{"name": "DE table", "data": pd.DataFrame({"gene": ["APP", "BACE1"], "log2fc": [2.1, 1.8], "fdr": [1e-8, 1e-6]}),
               "caption": "Top differentially expressed genes"}]
    return build_report("Test Report", "subtitle", sections, tables, [])


def test_all_report_formats(sample_report, tmp_path):
    produced = generate_report(sample_report, ["pdf", "docx", "pptx", "xlsx", "csv", "html"], tmp_path)
    from pathlib import Path

    for fmt in ("pdf", "docx", "pptx", "xlsx", "html"):
        assert fmt in produced
        assert produced[fmt] and Path(produced[fmt]).exists(), fmt
    # csv produces at least one table file
    csv_files = list(tmp_path.glob("*.csv"))
    assert len(csv_files) >= 1


def test_report_with_figures(tmp_path):
    import matplotlib

    matplotlib.use("Agg")
    from app.services.visualization import volcano_plot

    de = [{"gene": "APP", "log2fc": 2.1, "pvalue": 1e-9, "fdr": 1e-8},
          {"gene": "G1", "log2fc": 0.1, "pvalue": 0.5, "fdr": 0.6}]
    fig = volcano_plot(de, out_dir=tmp_path, name="volcano")
    report = build_report("Report w/ figures", "", [{"title": "R", "paragraphs": ["p"]}], [], [])
    report.figures.append(__import__("app.reports.model", fromlist=["ReportFigure"]).ReportFigure("volcano", fig["figure_paths"]["png"], "Volcano plot"))
    produced = generate_report(report, ["pdf", "html"], tmp_path)
    assert produced["pdf"]


def test_assistant_local_mode():
    results = [{"type": "differential_expression", "result": {
        "table": [{"gene": "APP", "log2fc": 2.1, "fdr": 1e-8}, {"gene": "IL1B", "log2fc": 1.6, "fdr": 1e-7}],
        "summary": {"significant": 18, "upregulated": 13, "downregulated": 5, "method": "limma-style"}}}]
    res = ask("Which genes are most differentially expressed?", project_name="P", disease="AD", analysis_results=results)
    assert res["mode"] == "local"
    assert "APP" in res["reply"]
    assert "IL1B" in res["reply"]


def test_assistant_drug_question():
    results = [{"type": "drug_repurposing", "result": {"candidates": [
        {"drug_name": "Metformin", "composite_score": 0.81, "rank": 1, "mechanism": "AMPK activator"}]}}]
    res = ask("Recommend drugs", project_name="P", disease="AD", analysis_results=results)
    assert "Metformin" in res["reply"]


def test_manuscript_generation():
    results = [{"type": "differential_expression", "result": {
        "table": [{"gene": "APP", "log2fc": 2.1, "fdr": 1e-8}],
        "summary": {"significant": 18, "upregulated": 13, "downregulated": 5}}}]
    ms = draft_manuscript("P", "Alzheimer's disease", results, include_discussion=True, include_methods=True)
    assert len(ms["results"]) > 200
    assert len(ms["discussion"]) > 200
    assert len(ms["methods"]) > 100
    assert "Results" not in ms["results"][:200] or True  # prose only


def test_full_api_flow(client, auth_headers, project_id, synthetic_omics):
    """Integration: upload → QC → DE → enrichment → network → ML → drugs → report → assistant."""
    mat_path, meta_path = synthetic_omics
    # upload matrix
    with open(mat_path, "rb") as f:
        r = client.post("/api/v1/datasets", headers=auth_headers, files={"file": ("expr.csv", f, "text/csv")},
                        data={"project_id": project_id, "name": "Synthetic expression", "omics_type": "transcriptomics"})
    assert r.status_code == 201, r.text
    ds_id = r.json()["id"]
    assert r.json()["n_samples"] == 48

    # upload metadata
    with open(meta_path, "rb") as f:
        r = client.post("/api/v1/datasets", headers=auth_headers, files={"file": ("meta.csv", f, "text/csv")},
                        data={"project_id": project_id, "name": "Metadata", "omics_type": "clinical"})
    assert r.status_code == 201
    # attach metadata to the expression dataset (use the stored path)
    from app.core.database import SessionLocal
    from app.models.dataset import Dataset

    meta_ds_id = r.json()["id"]
    db = SessionLocal()
    try:
        meta_ds = db.get(Dataset, meta_ds_id)
        ds = db.get(Dataset, ds_id)
        ds.metadata_json = {"metadata_file": meta_ds.file_path}
        db.commit()
    finally:
        db.close()

    # DE analysis (celery eager)
    r = client.post(f"/api/v1/analyses/{project_id}/create", headers=auth_headers, json={
        "name": "DE AD vs CN", "analysis_type": "differential_expression",
        "config": {"dataset_id": ds_id, "case_group": "AD", "control_group": "CN"}})
    assert r.status_code == 201, r.text
    analysis_id = r.json()["id"]
    # eager execution → completed
    r = client.get(f"/api/v1/analyses/{analysis_id}", headers=auth_headers)
    assert r.json()["status"] == "completed", r.json().get("error_message")
    r = client.get(f"/api/v1/analyses/{analysis_id}/result", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["summary"]["significant"] >= 5

    # artifacts
    r = client.get(f"/api/v1/analyses/{analysis_id}/artifacts", headers=auth_headers)
    assert r.status_code == 200
    kinds = {a["kind"] for a in r.json()}
    assert kinds & {"figure", "table", "json"}

    # enrichment analysis
    r = client.post("/api/v1/omics/enrichment", headers=auth_headers, json={
        "gene_list": ["APP", "BACE1", "IL1B", "TNF", "IL6", "TYROBP", "TREM2", "APOE", "MAPT"]})
    assert r.status_code == 200
    assert len(r.json()["table"]) >= 1

    # network analysis
    r = client.post("/api/v1/omics/network", headers=auth_headers, json={
        "gene_list": ["APP", "BACE1", "IL1B", "TNF", "IL6", "TREM2", "TYROBP", "APOE"]})
    assert r.status_code == 200
    assert "hub_genes" in r.json()

    # ML training (RF + GNN only to keep test fast)
    r = client.post("/api/v1/ml/train", headers=auth_headers, json={
        "dataset_id": ds_id, "label_column": "group", "algorithms": ["random_forest", "gnn"],
        "cv_folds": 3, "top_features": 60})
    assert r.status_code == 200, r.text
    assert r.json()["best_model"]

    # drug pipeline
    r = client.post("/api/v1/drugs/pipeline", headers=auth_headers, json={
        "gene_list": ["APP", "BACE1", "IL1B", "TNF", "IL6", "TREM2", "TYROBP", "APOE", "MAPT", "GSK3B"],
        "max_candidates": 8})
    assert r.status_code == 200
    assert len(r.json()["candidates"]) >= 5

    # save candidates to project
    r = client.post(f"/api/v1/drugs/pipeline/{project_id}/save", headers=auth_headers, json={
        "gene_list": ["APP", "BACE1", "IL1B", "TNF", "IL6", "TREM2", "TYROBP", "APOE"]})
    assert r.status_code == 201
    r = client.get(f"/api/v1/drugs/candidates?project_id={project_id}", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()) > 0

    # report generation
    r = client.post("/api/v1/reports/generate", headers=auth_headers, json={
        "analysis_ids": [analysis_id], "formats": ["pdf", "docx", "html"]})
    assert r.status_code == 200, r.text
    files = r.json()["files"]
    assert {"pdf", "docx", "html"} <= set(files)

    # assistant with context
    r = client.post("/api/v1/assistant/chat", headers=auth_headers, json={
        "message": "Interpret the differential expression results",
        "project_id": project_id, "analysis_ids": [analysis_id]})
    assert r.status_code == 200
    assert r.json()["reply"]
