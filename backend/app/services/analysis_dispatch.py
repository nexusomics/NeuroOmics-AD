"""Analysis dispatcher: routes analysis runs to the correct service and persists artifacts."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd

from app.models.analysis import Analysis
from app.services.io import load_expression_matrix, load_metadata, resolve_dataset_path
from app.utils.files import artifact_dir

logger = logging.getLogger(__name__)


def _load_dataset_matrix(db, dataset_id: str) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Load expression matrix + metadata for a dataset record."""
    from app.models.dataset import Dataset

    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise ValueError(f"dataset {dataset_id} not found")
    matrix = load_expression_matrix(ds.file_path)
    meta_path = None
    if ds.metadata_json and ds.metadata_json.get("metadata_file"):
        meta_path = resolve_dataset_path(ds.metadata_json["metadata_file"])
    metadata = load_metadata(meta_path) if meta_path and meta_path.exists() else _synthetic_metadata(matrix, ds)
    return matrix, metadata


def _synthetic_metadata(matrix: pd.DataFrame, ds) -> pd.DataFrame:
    """If no metadata file, synthesize a group column (case/control) from sample names."""
    samples = list(matrix.columns)
    groups = []
    for s in samples:
        sl = s.lower()
        if any(k in sl for k in ("ad", "case", "disease", "alz")):
            groups.append("AD")
        elif any(k in sl for k in ("cn", "ctrl", "control", "healthy", "normal")):
            groups.append("CN")
        else:
            groups.append("AD" if samples.index(s) % 2 == 0 else "CN")
    return pd.DataFrame({"group": groups}, index=samples)


def _save_json_artifact(analysis_id: str, name: str, data) -> None:
    out = artifact_dir(analysis_id) / f"{name}.json"
    out.write_text(json.dumps(data, default=str, indent=2))
    from app.models.analysis import ResultArtifact
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        db.add(ResultArtifact(analysis_id=analysis_id, name=name, kind="json", format="json",
                              file_path=str(out), size_bytes=out.stat().st_size,
                              metadata_json={"name": name}))
        db.commit()
    finally:
        db.close()


def dispatch_analysis(analysis: Analysis, db, progress_cb: Optional[Callable[[int], None]] = None) -> dict:
    """Execute the analysis described by `analysis` and persist artifacts."""
    atype = analysis.analysis_type
    cfg = analysis.config or {}
    if progress_cb:
        progress_cb(10)

    if atype in ("differential_expression", "de"):
        return _run_de(analysis, cfg, db, progress_cb)
    if atype == "preprocessing":
        return _run_preprocessing(analysis, cfg, db, progress_cb)
    if atype == "enrichment":
        return _run_enrichment(analysis, cfg, progress_cb)
    if atype == "network":
        return _run_network(analysis, cfg, progress_cb)
    if atype == "meta_analysis":
        return _run_meta(analysis, cfg, db, progress_cb)
    if atype == "deconvolution":
        return _run_deconvolution(analysis, cfg, db, progress_cb)
    if atype == "integration":
        return _run_integration(analysis, cfg, db, progress_cb)
    if atype == "ml":
        return _run_ml(analysis, cfg, db, progress_cb)
    if atype == "single_cell":
        return _run_single_cell(analysis, cfg, db, progress_cb)
    if atype == "genomics":
        return _run_genomics(analysis, cfg, db, progress_cb)
    if atype == "epigenomics":
        return _run_epigenomics(analysis, cfg, db, progress_cb)
    if atype == "clinical":
        return _run_clinical(analysis, cfg, db, progress_cb)
    if atype == "drug_repurposing":
        return _run_drugs(analysis, cfg, progress_cb)
    # plugin-provided analysis types
    from app.plugins.base import registry

    if atype in registry.analyses:
        plugin = registry.analyses[atype]
        return plugin.run(cfg, {"analysis_id": analysis.id})
    raise ValueError(f"unsupported analysis type: {atype}")


# ---------------------------------------------------------------------------
def _run_de(analysis, cfg, db, progress_cb) -> dict:
    from app.services.differential_expression import differential_expression
    from app.services.visualization import volcano_plot, heatmap, pca_plot, write_plotly_json

    if progress_cb:
        progress_cb(20)
    matrix, metadata = _load_dataset_matrix(db, cfg["dataset_id"])
    res = differential_expression(
        matrix, metadata,
        group_column=cfg.get("group_column", "group"),
        case=cfg.get("case_group", "AD"),
        control=cfg.get("control_group", "CN"),
        covariates=cfg.get("covariates", []),
        method=cfg.get("method", "auto"),
        fdr_threshold=cfg.get("fdr_threshold", 0.05),
        log2fc_threshold=cfg.get("log2fc_threshold", 1.0),
    )
    if progress_cb:
        progress_cb(60)
    out = artifact_dir(analysis.id)
    de_df = pd.DataFrame(res["table"])
    vol = volcano_plot(res["table"], cfg.get("fdr_threshold", 0.05), cfg.get("log2fc_threshold", 1.0), dpi=cfg.get("dpi", 300), out_dir=out, name="volcano")
    write_plotly_json(vol["plotly_json"], out, "volcano")
    sig = de_df[de_df["sig"]]
    if len(sig) > 2:
        hm = heatmap(matrix.loc[sig["gene"].head(50)], out_dir=out, name="DE_heatmap", top_n=50)
        write_plotly_json(hm["plotly_json"], out, "DE_heatmap")
    de_df.to_csv(out / "differential_expression_table.csv", index=False)
    _save_json_artifact(analysis.id, "differential_expression", res)
    _register_artifact(analysis.id, "differential_expression_table", "table", "csv", out / "differential_expression_table.csv")
    _register_artifact(analysis.id, "volcano", "figure", "png", Path(vol["figure_paths"]["png"]))
    if progress_cb:
        progress_cb(100)
    return res


def _run_preprocessing(analysis, cfg, db, progress_cb) -> dict:
    from app.services.preprocessing import run_preprocessing
    from app.services.visualization import heatmap, pca_plot, write_plotly_json
    from sklearn.decomposition import PCA

    matrix, metadata = _load_dataset_matrix(db, cfg["dataset_id"])
    out = run_preprocessing(
        matrix, metadata,
        normalize_method=cfg.get("normalize_method", "quantile"),
        log_transform=cfg.get("log_transform", False),
        batch_correct=cfg.get("batch_correct", False),
        batch_column=cfg.get("batch_column", "batch"),
        impute_method=cfg.get("impute_method", "knn"),
        remove_outlier_samples=cfg.get("remove_outliers", True),
    )
    norm = out["matrix"]
    out_dir = artifact_dir(analysis.id)
    norm.to_csv(out_dir / "normalized_matrix.csv")
    labels = metadata["group"].reindex(norm.columns) if metadata is not None and "group" in metadata.columns else None
    pca = PCA(n_components=min(3, norm.shape[1], norm.shape[0])).fit_transform(norm.T.values.astype(float))
    pca_fig = pca_plot(pca, labels.values if labels is not None else None, out_dir=out_dir, name="pca_after_qc")
    write_plotly_json(pca_fig["plotly_json"], out_dir, "pca_after_qc")
    _save_json_artifact(analysis.id, "preprocessing_report", out["report"])
    _register_artifact(analysis.id, "normalized_matrix", "table", "csv", out_dir / "normalized_matrix.csv")
    _register_artifact(analysis.id, "pca_after_qc", "figure", "png", Path(pca_fig["figure_paths"]["png"]))
    return {"report": out["report"], "outliers": out["report"].get("outliers", [])}


def _run_enrichment(analysis, cfg, progress_cb) -> dict:
    from app.services.enrichment import enrich
    from app.services.visualization import enrichment_barplot, write_plotly_json

    res = enrich(
        cfg.get("gene_list", []),
        background=cfg.get("background"),
        databases=cfg.get("databases"),
        fdr_threshold=cfg.get("fdr_threshold", 0.05),
    )
    out_dir = artifact_dir(analysis.id)
    if res["table"]:
        fig = enrichment_barplot(res["table"], out_dir=out_dir, name="enrichment")
        write_plotly_json(fig["plotly_json"], out_dir, "enrichment")
        _register_artifact(analysis.id, "enrichment_barplot", "figure", "png", Path(fig["figure_paths"]["png"]))
    _save_json_artifact(analysis.id, "enrichment", res)
    return res


def _run_network(analysis, cfg, progress_cb) -> dict:
    from app.services.network import run_network_analysis
    from app.services.visualization import ppi_network_figure, write_plotly_json

    res = run_network_analysis(
        cfg.get("gene_list", []),
        confidence_threshold=cfg.get("confidence_threshold", 0.4),
        max_interactors=cfg.get("max_interactors", 50),
        source=cfg.get("source", "string"),
    )
    out_dir = artifact_dir(analysis.id)
    metrics = res["metrics"]
    fig = ppi_network_figure(metrics, list(res["graph"].edges()), out_dir=out_dir, name="ppi_network")
    write_plotly_json({"nodes": fig["nodes"], "edges": fig["edges"]}, out_dir, "ppi_network")
    metrics.to_csv(out_dir / "node_metrics.csv", index=False)
    _register_artifact(analysis.id, "ppi_network", "figure", "png", Path(fig["figure_paths"]["png"]))
    _register_artifact(analysis.id, "node_metrics", "table", "csv", out_dir / "node_metrics.csv")
    _save_json_artifact(analysis.id, "network", {"summary": res["summary"], "hub_genes": res["hub_genes"]})
    return {"summary": res["summary"], "hub_genes": res["hub_genes"], "metrics": metrics.to_dict(orient="records")}


def _run_meta(analysis, cfg, db, progress_cb) -> dict:
    from app.services.meta_analysis import meta_analysis

    matrices, metas = [], []
    for ds_id in cfg["dataset_ids"]:
        m, meta = _load_dataset_matrix(db, ds_id)
        matrices.append(m)
        metas.append(meta)
    res = meta_analysis(
        matrices, metas,
        case=cfg.get("case_group", "AD"),
        control=cfg.get("control_group", "CN"),
        effect_size_method=cfg.get("effect_size_method", "cohens_d"),
        fixed_effects=cfg.get("fixed_effects", True),
    )
    out_dir = artifact_dir(analysis.id)
    pd.DataFrame(res["table"]).to_csv(out_dir / "meta_analysis_table.csv", index=False)
    _register_artifact(analysis.id, "meta_analysis_table", "table", "csv", out_dir / "meta_analysis_table.csv")
    _save_json_artifact(analysis.id, "meta_analysis", res)
    return res


def _run_deconvolution(analysis, cfg, db, progress_cb) -> dict:
    from app.services.deconvolution import deconvolute
    from app.services.visualization import deconvolution_stackplot, write_plotly_json

    matrix, _ = _load_dataset_matrix(db, cfg["dataset_id"])
    res = deconvolute(matrix, signature_source=cfg.get("signature_source", "lm22"), method=cfg.get("method", "cibersort"))
    out_dir = artifact_dir(analysis.id)
    res["fractions"].to_csv(out_dir / "cell_fractions.csv")
    fig = deconvolution_stackplot(res["fractions"], out_dir=out_dir, name="deconvolution")
    write_plotly_json(fig["plotly_json"], out_dir, "deconvolution")
    _register_artifact(analysis.id, "cell_fractions", "table", "csv", out_dir / "cell_fractions.csv")
    _register_artifact(analysis.id, "deconvolution_stackplot", "figure", "png", Path(fig["figure_paths"]["png"]))
    _save_json_artifact(analysis.id, "deconvolution", {"qc": res["qc"]})
    return {"qc": res["qc"], "fractions": res["fractions"].to_dict(orient="index")}


def _run_integration(analysis, cfg, db, progress_cb) -> dict:
    from app.services.integration import integrate
    from app.services.visualization import pca_plot, write_plotly_json
    from sklearn.decomposition import PCA

    ds_ids = cfg.get("dataset_ids") or []
    if len(ds_ids) < 2:
        raise ValueError("Multi-omics integration requires ≥ 2 expression datasets (e.g. transcriptomics + proteomics). "
                         "Open the Analysis form and select two or more datasets of omics type transcriptomics / proteomics / metabolomics / epigenomics.")
    matrices, names = [], []
    for ds_id in ds_ids:
        ds = db.get(__import__("app.models.dataset", fromlist=["Dataset"]).Dataset, ds_id)
        if not ds:
            raise ValueError(f"dataset {ds_id} not found")
        if ds.omics_type == "clinical":
            raise ValueError(f"dataset '{ds.name}' is a clinical/metadata file and cannot be used for integration — "
                             "select expression datasets (transcriptomics/proteomics/metabolomics/epigenomics).")
        m, _ = _load_dataset_matrix(db, ds_id)
        matrices.append(m)
        names.append(ds.name)
    # intersect samples across blocks; error clearly if none overlap
    common = set(matrices[0].columns)
    for m in matrices[1:]:
        common &= set(m.columns)
    if len(common) < 5:
        raise ValueError("Datasets share too few samples for integration. "
                         "Ensure the selected datasets were measured on the same samples (sample IDs must match).")
    matrices = [m[list(common)] for m in matrices]
    res = integrate(matrices, method=cfg.get("method", "weighted_fusion"), rank=cfg.get("rank", 5))
    res["datasets_used"] = names
    out_dir = artifact_dir(analysis.id)
    res["factors"].to_csv(out_dir / "integrated_factors.csv")
    pca = PCA(n_components=2).fit_transform(res["factors"].values)
    fig = pca_plot(pca, None, out_dir=out_dir, name="integration_pca")
    write_plotly_json(fig["plotly_json"], out_dir, "integration_pca")
    _register_artifact(analysis.id, "integrated_factors", "table", "csv", out_dir / "integrated_factors.csv")
    _save_json_artifact(analysis.id, "integration", res)
    return res


def _run_ml(analysis, cfg, db, progress_cb) -> dict:
    from app.ml.train import train_models

    matrix, metadata = _load_dataset_matrix(db, cfg["dataset_id"])
    label_column = cfg.get("label_column", "group")
    if metadata is None or label_column not in metadata.columns:
        raise ValueError(f"label column '{label_column}' not found in metadata")
    labels = metadata[label_column]
    res = train_models(
        matrix, labels,
        algorithms=cfg.get("algorithms", ["random_forest", "xgboost", "svm", "dnn"]),
        test_size=cfg.get("test_size", 0.2),
        cv_folds=cfg.get("cv_folds", 5),
        feature_selection=cfg.get("feature_selection", True),
        top_features=cfg.get("top_features", 100),
        gnn=cfg.get("gnn", True),
        hyperparameters=cfg.get("hyperparameters", {}),
    )
    _save_json_artifact(analysis.id, "ml_training", res)
    return res


def _run_single_cell(analysis, cfg, db, progress_cb) -> dict:
    from app.services.single_cell import pipeline
    from app.services.visualization import pca_plot, write_plotly_json

    matrix, _ = _load_dataset_matrix(db, cfg["dataset_id"])
    res = pipeline(matrix, n_pcs=cfg.get("n_pcs", 20), n_neighbors=cfg.get("n_neighbors", 15),
                   n_clusters=cfg.get("n_clusters"), min_genes=cfg.get("min_genes", 200))
    out_dir = artifact_dir(analysis.id)
    res["embedding"].to_csv(out_dir / "sc_embedding.csv")
    fig = pca_plot(res["embedding"][["UMAP1", "UMAP2"]].values, res["embedding"]["cluster"].values,
                   out_dir=out_dir, name="umap", title="UMAP (single-cell)")
    write_plotly_json(fig["plotly_json"], out_dir, "umap")
    _register_artifact(analysis.id, "sc_embedding", "table", "csv", out_dir / "sc_embedding.csv")
    _register_artifact(analysis.id, "umap", "figure", "png", Path(fig["figure_paths"]["png"]))
    _save_json_artifact(analysis.id, "single_cell", {"qc": res["qc"], "cluster_annotations": res["cluster_annotations"]})
    return {"qc": res["qc"], "cluster_annotations": res["cluster_annotations"], "n_clusters": res["n_clusters"]}


def _run_genomics(analysis, cfg, db, progress_cb) -> dict:
    from app.services.genomics import genomic_inflation_lambda, manhattan_signal, validate_gwas_summary

    ds = db.get(__import__("app.models.dataset", fromlist=["Dataset"]).Dataset, cfg["dataset_id"])
    if not ds:
        raise ValueError("dataset not found")
    gwas = pd.read_csv(resolve_dataset_path(ds.file_path), sep="\t" if str(ds.file_path).endswith((".tsv", ".txt")) else ",")
    missing = validate_gwas_summary(gwas)
    if missing:
        raise ValueError(
            f"GWAS analysis requires a summary-statistics file with columns: rsid, chrom, pos, beta, se, pvalue, effect_allele. "
            f"Dataset '{ds.name}' ({ds.omics_type}) is missing: {missing}. "
            "Upload a GWAS summary-stats file as a 'genomics' dataset, or choose a different analysis type for expression data.")
    gwas["lambda_gc"] = genomic_inflation_lambda(gwas["pvalue"].values)
    sig = manhattan_signal(gwas, fdr_threshold=cfg.get("fdr_threshold", 5e-8))
    out_dir = artifact_dir(analysis.id)
    sig.to_csv(out_dir / "gwas_significant_loci.csv", index=False)
    _register_artifact(analysis.id, "gwas_significant_loci", "table", "csv", out_dir / "gwas_significant_loci.csv")
    _save_json_artifact(analysis.id, "genomics", {"n_snps": len(gwas), "lambda_gc": float(gwas["lambda_gc"].iloc[0]),
                                                  "n_significant": int(sig["significant"].sum())})
    return {"n_snps": len(gwas), "lambda_gc": float(gwas["lambda_gc"].iloc[0]), "n_significant": int(sig["significant"].sum())}


def _run_epigenomics(analysis, cfg, db, progress_cb) -> dict:
    from app.services.epigenomics import differential_methylation

    matrix, metadata = _load_dataset_matrix(db, cfg["dataset_id"])
    res = differential_methylation(
        matrix, metadata,
        case=cfg.get("case_group", "AD"), control=cfg.get("control_group", "CN"),
        fdr_threshold=cfg.get("fdr_threshold", 0.05), delta_beta_threshold=cfg.get("delta_beta_threshold", 0.1),
    )
    out_dir = artifact_dir(analysis.id)
    pd.DataFrame(res["table"]).to_csv(out_dir / "dmps.csv", index=False)
    _register_artifact(analysis.id, "dmps", "table", "csv", out_dir / "dmps.csv")
    _save_json_artifact(analysis.id, "epigenomics", res)
    return res


def _run_clinical(analysis, cfg, db, progress_cb) -> dict:
    from app.services.clinical import kaplan_meier, stratify_patients
    from app.services.visualization import survival_km_plot, write_plotly_json

    matrix, metadata = _load_dataset_matrix(db, cfg["dataset_id"])
    if metadata is None:
        raise ValueError("clinical analysis requires sample metadata")
    results = {}
    if "time" in metadata.columns and "event" in metadata.columns and "group" in metadata.columns:
        km = kaplan_meier(metadata["time"].values, metadata["event"].values, metadata["group"].values)
        out_dir = artifact_dir(analysis.id)
        fig = survival_km_plot(km, out_dir=out_dir, name="kaplan_meier")
        write_plotly_json(fig["plotly_json"], out_dir, "kaplan_meier")
        _register_artifact(analysis.id, "kaplan_meier", "figure", "png", Path(fig["figure_paths"]["png"]))
        results["kaplan_meier"] = km
    if cfg.get("stratify") and matrix.shape[0] >= 4:
        strat = stratify_patients(matrix.T, n_clusters=cfg.get("n_clusters", 4))
        results["stratification"] = {k: v for k, v in strat.items() if k != "cluster_centers"}
    _save_json_artifact(analysis.id, "clinical", results)
    return results


def _run_drugs(analysis, cfg, progress_cb) -> dict:
    from app.drugs.pipeline import run_drug_pipeline

    res = run_drug_pipeline(
        gene_list=cfg.get("gene_list", []),
        direction=cfg.get("direction"),
        weights=cfg.get("weights"),
        max_candidates=cfg.get("max_candidates", 50),
        require_bbb_positive=cfg.get("require_bbb_positive", False),
        min_clinical_phase=cfg.get("min_clinical_phase", "preclinical"),
        sources=cfg.get("sources"),
    )
    out_dir = artifact_dir(analysis.id)
    pd.DataFrame([{**{"drug_name": c["drug_name"], "mechanism": c["mechanism"], "composite_score": c["composite_score"],
                      "rank": c["rank"], "fda_status": c["fda_status"]}, **c["scores"]} for c in res["candidates"]]) \
        .to_csv(out_dir / "drug_candidates.csv", index=False)
    _register_artifact(analysis.id, "drug_candidates", "table", "csv", out_dir / "drug_candidates.csv")
    _save_json_artifact(analysis.id, "drug_repurposing", res)
    return res


# ---------------------------------------------------------------------------
def _register_artifact(analysis_id: str, name: str, kind: str, fmt: str, path: Path) -> None:
    from app.core.database import SessionLocal
    from app.models.analysis import ResultArtifact

    db = SessionLocal()
    try:
        db.add(ResultArtifact(analysis_id=analysis_id, name=name, kind=kind, format=fmt,
                              file_path=str(path), size_bytes=path.stat().st_size if path.exists() else 0))
        db.commit()
    finally:
        db.close()
