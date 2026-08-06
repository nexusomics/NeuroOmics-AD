"""Figure generation: publication-quality static (300–600 dpi) + interactive JSON.

Every plot is produced twice:
  * PNG/SVG at configurable DPI (default 300, up to 600) with journal styling,
  * Plotly figure JSON for the interactive web frontend.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

logger = logging.getLogger(__name__)

JOURNAL_STYLE = {
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi": 100,
    "savefig.dpi": 300,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "font.family": "DejaVu Sans",
}


def _style() -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams.update(JOURNAL_STYLE)


def save_figure(fig: plt.Figure, out_dir: Path, name: str, dpi: int = 300, formats: list[str] | None = None) -> dict[str, str]:
    """Save figure in PNG (+SVG optionally) and return paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    formats = formats or ["png"]
    paths = {}
    for fmt in formats:
        p = out_dir / f"{name}.{fmt}"
        fig.savefig(p, dpi=dpi, bbox_inches="tight", facecolor="white")
        paths[fmt] = str(p)
    plt.close(fig)
    return paths


# ---------------------------------------------------------------------------
# Plot generators (return (fig, plotly_json))
# ---------------------------------------------------------------------------
def volcano_plot(de_table: pd.DataFrame, fdr_threshold: float = 0.05, log2fc_threshold: float = 1.0, dpi: int = 300, out_dir: Optional[Path] = None, name: str = "volcano") -> dict:
    _style()
    df = pd.DataFrame(de_table)
    df["neglog10p"] = -np.log10(df["pvalue"].clip(lower=1e-300))
    df["color"] = "gray"
    df.loc[(df["fdr"] < fdr_threshold) & (df["log2fc"] > log2fc_threshold), "color"] = "#d62728"
    df.loc[(df["fdr"] < fdr_threshold) & (df["log2fc"] < -log2fc_threshold), "color"] = "#1f77b4"
    fig, ax = plt.subplots(figsize=(6.2, 4.6))
    ax.scatter(df["log2fc"], df["neglog10p"], c=df["color"], s=8, alpha=0.7, linewidths=0)
    ax.axvline(log2fc_threshold, color="k", ls="--", lw=0.7, alpha=0.6)
    ax.axvline(-log2fc_threshold, color="k", ls="--", lw=0.7, alpha=0.6)
    ax.axhline(-np.log10(fdr_threshold), color="k", ls="--", lw=0.7, alpha=0.6)
    ax.set_xlabel("log₂ fold change")
    ax.set_ylabel("−log₁₀(p-value)")
    ax.set_title("Differential expression: volcano plot")
    top = df.nlargest(12, "neglog10p")
    for _, r in top.iterrows():
        ax.annotate(r["gene"], (r["log2fc"], r["neglog10p"]), fontsize=6, alpha=0.8)
    n_up = int(((df["fdr"] < fdr_threshold) & (df["log2fc"] > log2fc_threshold)).sum())
    n_down = int(((df["fdr"] < fdr_threshold) & (df["log2fc"] < -log2fc_threshold)).sum())
    ax.legend(handles=[plt.Line2D([0], [0], marker="o", color="w", mfc="#d62728", label=f"up ({n_up})"),
                       plt.Line2D([0], [0], marker="o", color="w", mfc="#1f77b4", label=f"down ({n_down})"),
                       plt.Line2D([0], [0], marker="o", color="w", mfc="gray", label="ns")],
              loc="upper left", frameon=False)
    fig.tight_layout()
    paths = save_figure(fig, out_dir or Path("."), name, dpi) if out_dir else {}
    plotly = {
        "data": [{"type": "scattergl", "mode": "markers", "x": df["log2fc"].tolist(), "y": df["neglog10p"].tolist(),
                  "text": df["gene"].tolist(), "marker": {"color": df["color"].tolist(), "size": 6}}],
        "layout": {"title": "Volcano plot", "xaxis": {"title": "log2 fold change"}, "yaxis": {"title": "-log10(p)"}},
    }
    return {"figure_paths": paths, "plotly_json": plotly, "n_up": n_up, "n_down": n_down}


def heatmap(matrix: pd.DataFrame, out_dir: Optional[Path] = None, name: str = "heatmap", cmap: str = "RdBu_r", top_n: int = 50, dpi: int = 300) -> dict:
    _style()
    m = matrix.copy()
    if m.shape[0] > top_n:
        m = m.loc[m.var(axis=1).nlargest(top_n).index]
    fig, ax = plt.subplots(figsize=(max(6, m.shape[1] * 0.35), max(5, m.shape[0] * 0.25)))
    sns.heatmap(m, cmap=cmap, ax=ax, xticklabels=True, yticklabels=True, linewidths=0, cbar_kws={"shrink": 0.7})
    ax.set_title(f"Heatmap ({m.shape[0]} features × {m.shape[1]} samples)")
    fig.tight_layout()
    paths = save_figure(fig, out_dir or Path("."), name, dpi) if out_dir else {}
    plotly = {
        "data": [{"type": "heatmap", "z": m.values.tolist(), "x": m.columns.tolist(), "y": m.index.tolist(), "colorscale": "RdBu_r"}],
        "layout": {"title": "Expression heatmap", "xaxis": {"title": "samples"}, "yaxis": {"title": "features"}},
    }
    return {"figure_paths": paths, "plotly_json": plotly}


def pca_plot(X_reduced: np.ndarray, labels: Optional[np.ndarray], out_dir: Optional[Path] = None, name: str = "pca", dpi: int = 300, title: str = "PCA") -> dict:
    _style()
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    if labels is not None:
        for lab in np.unique(labels):
            idx = labels == lab
            ax.scatter(X_reduced[idx, 0], X_reduced[idx, 1], s=22, alpha=0.75, label=str(lab), edgecolors="white", linewidth=0.3)
        ax.legend(frameon=False)
    else:
        ax.scatter(X_reduced[:, 0], X_reduced[:, 1], s=22, alpha=0.75)
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title(title)
    fig.tight_layout()
    paths = save_figure(fig, out_dir or Path("."), name, dpi) if out_dir else {}
    plotly = {
        "data": [{"type": "scattergl", "mode": "markers", "x": X_reduced[:, 0].tolist(), "y": X_reduced[:, 1].tolist(),
                  "text": (labels.astype(str).tolist() if labels is not None else None),
                  "marker": {"color": (labels.astype(str).tolist() if labels is not None else "#1f77b4")}}],
        "layout": {"title": title, "xaxis": {"title": "Component 1"}, "yaxis": {"title": "Component 2"}},
    }
    return {"figure_paths": paths, "plotly_json": plotly}


def enrichment_barplot(enrich_table: list[dict], out_dir: Optional[Path] = None, name: str = "enrichment", top_n: int = 15, dpi: int = 300) -> dict:
    _style()
    df = pd.DataFrame(enrich_table).head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    colors = plt.cm.RdYlBu_r(np.linspace(0.2, 0.9, len(df)))
    ax.barh(np.arange(len(df)), df["enrichment_score"] if "enrichment_score" in df else -np.log10(df["fdr"].clip(lower=1e-300)),
            color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(np.arange(len(df)))
    ax.set_yticklabels([str(p)[:60] for p in df["pathway"]], fontsize=7)
    ax.set_xlabel("−log₁₀(FDR)")
    ax.set_title("Pathway enrichment")
    fig.tight_layout()
    paths = save_figure(fig, out_dir or Path("."), name, dpi) if out_dir else {}
    plotly = {
        "data": [{"type": "bar", "orientation": "h", "y": [str(p)[:60] for p in df["pathway"]],
                  "x": (-np.log10(df["fdr"].clip(lower=1e-300))).tolist(), "marker": {"color": "teal"}}],
        "layout": {"title": "Pathway enrichment", "xaxis": {"title": "-log10(FDR)"}},
    }
    return {"figure_paths": paths, "plotly_json": plotly}


def ppi_network_figure(metrics: pd.DataFrame, edges: list[tuple[str, str]], out_dir: Optional[Path] = None, name: str = "ppi_network", dpi: int = 300) -> dict:
    """Static network rendering with hub genes highlighted (uses graphviz-free spring layout)."""
    _style()
    import networkx as nx

    G = nx.Graph()
    G.add_edges_from(edges)
    hubs = set(metrics[metrics["hub"]]["node"].tolist()) if "hub" in metrics else set()
    pos = nx.spring_layout(G, seed=42, k=0.6)
    fig, ax = plt.subplots(figsize=(7, 6))
    node_colors = ["#e74c3c" if n in hubs else "#5dade2" for n in G.nodes]
    node_sizes = [320 if n in hubs else 120 for n in G.nodes]
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.25, width=0.6)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=node_sizes, edgecolors="white", linewidths=0.6)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=7)
    ax.axis("off")
    ax.set_title(f"PPI network — hubs highlighted ({len(hubs)} hubs)")
    fig.tight_layout()
    paths = save_figure(fig, out_dir or Path("."), name, dpi) if out_dir else {}
    nodes_payload = [{"id": n, "hub": n in hubs, "x": pos[n][0], "y": pos[n][1]} for n in G.nodes]
    edges_payload = [{"source": u, "target": v, "weight": G[u][v].get("weight", 1.0)} for u, v in G.edges]
    return {"figure_paths": paths, "nodes": nodes_payload, "edges": edges_payload}


def deconvolution_stackplot(fractions: pd.DataFrame, out_dir: Optional[Path] = None, name: str = "deconvolution", dpi: int = 300) -> dict:
    _style()
    fig, ax = plt.subplots(figsize=(max(7, fractions.shape[0] * 0.3), 4.6))
    frac = fractions.T
    bottom = np.zeros(frac.shape[1])
    palette = sns.color_palette("husl", frac.shape[0])
    for i, ct in enumerate(frac.index):
        ax.bar(np.arange(frac.shape[1]), frac.loc[ct], bottom=bottom, label=ct, color=palette[i], width=0.85, linewidth=0)
        bottom += frac.loc[ct]
    ax.set_xticks(np.arange(frac.shape[1]))
    ax.set_xticklabels(frac.columns, rotation=90, fontsize=6)
    ax.set_ylabel("Fraction")
    ax.set_title("Cell-type deconvolution")
    ax.legend(loc="upper right", fontsize=6, frameon=False, ncol=2)
    fig.tight_layout()
    paths = save_figure(fig, out_dir or Path("."), name, dpi) if out_dir else {}
    plotly = {
        "data": [{"type": "bar", "x": fractions.index.tolist(), "y": fractions[ct].tolist(), "name": ct, "stackgroup": "one"} for ct in fractions.columns],
        "layout": {"title": "Cell-type deconvolution", "barmode": "stack", "xaxis": {"title": "samples"}, "yaxis": {"title": "fraction"}},
    }
    return {"figure_paths": paths, "plotly_json": plotly}


def roc_curve_plot(fpr: np.ndarray, tpr: np.ndarray, auc: float, out_dir: Optional[Path] = None, name: str = "roc", dpi: int = 300) -> dict:
    _style()
    fig, ax = plt.subplots(figsize=(5, 4.6))
    ax.plot(fpr, tpr, lw=2, color="#1f77b4", label=f"AUC = {auc:.3f}")
    ax.plot([0, 1], [0, 1], "k--", lw=0.8, alpha=0.5)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC curve")
    ax.legend(frameon=False)
    fig.tight_layout()
    paths = save_figure(fig, out_dir or Path("."), name, dpi) if out_dir else {}
    return {"figure_paths": paths, "plotly_json": {"data": [{"type": "scatter", "x": fpr.tolist(), "y": tpr.tolist(), "mode": "lines", "name": f"AUC={auc:.3f}"}], "layout": {"title": "ROC curve"}}}


def feature_importance_plot(importance: list[dict], out_dir: Optional[Path] = None, name: str = "feature_importance", top_n: int = 20, dpi: int = 300) -> dict:
    _style()
    df = pd.DataFrame(importance).head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(6, max(3.5, 0.28 * len(df))))
    ax.barh(np.arange(len(df)), df["importance"], color="#2ca02c", edgecolor="white", linewidth=0.5)
    ax.set_yticks(np.arange(len(df)))
    ax.set_yticklabels(df["feature"], fontsize=7)
    ax.set_xlabel("Importance")
    ax.set_title("Feature importance")
    fig.tight_layout()
    paths = save_figure(fig, out_dir or Path("."), name, dpi) if out_dir else {}
    return {"figure_paths": paths, "plotly_json": {"data": [{"type": "bar", "orientation": "h", "y": df["feature"].tolist(), "x": df["importance"].tolist()}], "layout": {"title": "Feature importance"}}}


def survival_km_plot(km_result: dict, out_dir: Optional[Path] = None, name: str = "kaplan_meier", dpi: int = 300) -> dict:
    _style()
    fig, ax = plt.subplots(figsize=(6, 4.6))
    for g, data in km_result["curves"].items():
        ax.step(data["time"], data["survival"], where="post", lw=2, label=f"{g} (n={data['n']})")
    ax.set_xlabel("Time")
    ax.set_ylabel("Survival probability")
    ax.set_title(f"Kaplan–Meier (log-rank p = {km_result['logrank_pvalue']:.3g})")
    ax.legend(frameon=False)
    fig.tight_layout()
    paths = save_figure(fig, out_dir or Path("."), name, dpi) if out_dir else {}
    return {"figure_paths": paths, "plotly_json": {"data": [{"type": "scatter", "mode": "lines", "x": data["time"], "y": data["survival"], "name": g} for g, data in km_result["curves"].items()], "layout": {"title": "Kaplan–Meier curves"}}}


def write_plotly_json(plotly_json: dict, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{name}.plotly.json"
    p.write_text(json.dumps(plotly_json))
    return p
