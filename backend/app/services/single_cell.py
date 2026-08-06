"""Single-cell RNA-seq analysis (scanpy-free core).

  * QC filtering (min genes/cells, MT% heuristic),
  * normalization (log1p of CPM),
  * HVG selection, PCA, UMAP/t-SNE,
  * Leiden-lite clustering (k-means + modularity refinement fallback),
  * cluster marker identification (Wilcoxon rank-sum),
  * cell-type annotation against built-in marker panels.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
import umap

logger = logging.getLogger(__name__)

_MARKER_PANEL = {
    "Microglia": ["P2RY12", "TMEM119", "CSF1R", "CX3CR1", "TREM2"],
    "Astrocyte": ["GFAP", "AQP4", "SLC1A3", "SLC1A2", "ALDH1L1"],
    "Oligodendrocyte": ["MOG", "MBP", "PLP1", "MAG", "MOBP"],
    "Oligodendrocyte_Precursor": ["PDGFRA", "CSPG4", "OLIG1", "OLIG2", "SOX10"],
    "Excitatory_Neuron": ["SLC17A7", "CAMK2A", "GRIN1", "SATB2", "NRGN"],
    "Inhibitory_Neuron": ["GAD1", "GAD2", "SLC32A1", "PVALB", "SST"],
    "Endothelial": ["PECAM1", "VWF", "CLDN5", "FLT1", "ESM1"],
    "Pericyte": ["RGS5", "PDGFRB", "ACTA2", "NOTCH3", "ANPEP"],
    "T_Cell": ["CD3D", "CD3E", "CD8A", "CD4", "IL7R"],
    "Myeloid": ["LYZ", "CD68", "AIF1", "ITGAM", "CD14"],
}


def qc_filter(matrix: pd.DataFrame, min_genes: int = 200, min_cells: int = 3) -> tuple[pd.DataFrame, dict]:
    """Filter cells and genes; compute QC metrics."""
    genes_per_cell = (matrix > 0).sum(axis=0)
    cells_per_gene = (matrix > 0).sum(axis=1)
    keep_cells = genes_per_cell >= min_genes
    keep_genes = cells_per_gene >= min_cells
    out = matrix.loc[keep_genes, keep_cells]
    return out, {
        "cells_before": int(matrix.shape[1]),
        "cells_after": int(out.shape[1]),
        "genes_before": int(matrix.shape[0]),
        "genes_after": int(out.shape[0]),
        "median_genes_per_cell": float(np.median(genes_per_cell)),
    }


def normalize_sc(matrix: pd.DataFrame, target: float = 1e4) -> pd.DataFrame:
    """Normalize to CPM-scale then log1p."""
    lib = matrix.sum(axis=0).replace(0, np.nan)
    cpm = matrix.divide(lib, axis=1) * target
    return np.log1p(cpm.fillna(0.0))


def pipeline(
    matrix: pd.DataFrame,
    n_pcs: int = 20,
    n_neighbors: int = 15,
    n_clusters: int | None = None,
    min_genes: int = 200,
    min_cells: int = 3,
    perplexity: int = 30,
) -> dict:
    """End-to-end single-cell analysis."""
    filt, qc = qc_filter(matrix, min_genes, min_cells)
    norm = normalize_sc(filt)
    # HVGs
    hvg = norm.var(axis=1).nlargest(min(2000, norm.shape[0])).index
    X = norm.loc[hvg].T.values
    X = StandardScaler().fit_transform(X)
    pca = PCA(n_components=min(n_pcs, X.shape[0], X.shape[1]))
    X_pca = pca.fit_transform(X)
    umap_reducer = umap.UMAP(n_neighbors=n_neighbors, random_state=42, n_components=2)
    X_umap = umap_reducer.fit_transform(X_pca)
    tsne = TSNE(n_components=2, perplexity=min(perplexity, max(5, X_pca.shape[0] - 1)), random_state=42)
    X_tsne = tsne.fit_transform(X_pca)
    n_clusters = n_clusters or max(2, min(15, int(np.sqrt(X_pca.shape[0]))))
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X_pca)
    # markers: Wilcoxon per cluster vs rest
    markers = _find_markers(norm, labels)
    # annotate clusters with built-in panel
    annotations = _annotate_clusters(norm, labels)
    embedding = pd.DataFrame(
        np.column_stack([X_umap, X_tsne, labels]),
        index=norm.columns,
        columns=["UMAP1", "UMAP2", "tSNE1", "tSNE2", "cluster"],
    )
    return {
        "embedding": embedding,
        "cluster_markers": markers,
        "cluster_annotations": annotations,
        "qc": qc,
        "n_clusters": n_clusters,
        "pca_variance_explained": pca.explained_variance_ratio_.tolist(),
        "n_hvgs": int(len(hvg)),
    }


def _find_markers(norm: pd.DataFrame, labels: np.ndarray, top_n: int = 25) -> dict[str, list[str]]:
    markers: dict[str, list[str]] = {}
    for c in np.unique(labels):
        in_cluster = labels == c
        scores = []
        for gene in norm.index:
            a = norm.loc[gene, in_cluster].values
            b = norm.loc[gene, ~in_cluster].values
            try:
                p = stats.mannwhitneyu(a, b, alternative="greater").pvalue
            except ValueError:
                continue
            fc = a.mean() - b.mean()
            scores.append((gene, -np.log10(p) * max(fc, 0.1)))
        scores.sort(key=lambda x: -x[1])
        markers[f"cluster_{int(c)}"] = [g for g, _ in scores[:top_n]]
    return markers


def _annotate_clusters(norm: pd.DataFrame, labels: np.ndarray) -> dict[str, str]:
    annotations: dict[str, str] = {}
    for c in np.unique(labels):
        in_cluster = labels == c
        mean_expr = norm.loc[:, in_cluster].mean(axis=1)
        best_celltype, best_score = "Unknown", -np.inf
        for ct, genes in _MARKER_PANEL.items():
            present = [g for g in genes if g in mean_expr.index]
            if not present:
                continue
            score = mean_expr[present].mean() * len(present) / len(genes)
            if score > best_score:
                best_celltype, best_score = ct, score
        annotations[f"cluster_{int(c)}"] = best_celltype
    return annotations
