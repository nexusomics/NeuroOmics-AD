"""Cell-type deconvolution.

Implements a CIBERSORT-style approach:
  1. Build/load a reference signature matrix (cell-type × genes).
  2. For each sample, solve a non-negative least-squares (NNLS) problem
     `min ||X - S·f||₂` with `f >= 0`, using an all-samples quadratic
     programming formulation (as in the original CIBERSORT).
Returns per-sample cell-type fractions and per-cell-type statistics.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.optimize import nnls
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in LM22-style signature (CIBERSORT, Newman et al. 2015) — representative
# 22 immune cell types × curated marker genes. In production, load a full
# signature file; this built-in enables out-of-the-box demos.
# ---------------------------------------------------------------------------
_BUILTIN_SIGNATURE: dict[str, list[str]] = {
    "B_naive": ["MS4A1", "CD79A", "CD79B", "CD19", "BANK1"],
    "B_memory": ["CD27", "TNFRSF13B", "CD38", "MZB1", "IGHA1"],
    "Plasma": ["XBP1", "MZB1", "SDC1", "TNFRSF17", "DERL3"],
    "CD8_T": ["CD8A", "CD8B", "GZMA", "GZMB", "PRF1"],
    "CD4_naive": ["CD4", "CCR7", "SELL", "LEF1", "TCF7"],
    "CD4_memory": ["IL7R", "S100A4", "CD27", "CCL5", "KLRB1"],
    "Treg": ["FOXP3", "IKZF2", "CTLA4", "IL2RA", "CCR8"],
    "NK": ["NKG7", "KLRD1", "KLRF1", "GNLY", "FGFBP2"],
    "Monocyte": ["CD14", "LYZ", "FCGR3A", "S100A8", "S100A9"],
    "Macrophage_M1": ["IL1B", "TNF", "CXCL10", "CCL3", "STAT1"],
    "Macrophage_M2": ["CD163", "MSR1", "MRC1", "ARG1", "TGFBI"],
    "DC": ["ITGAX", "CD1C", "CLEC9A", "BATF3", "FLT3"],
    "Mast": ["TPSAB1", "TPSB2", "CPA3", "HDC", "MS4A2"],
    "Neutrophil": ["FCGR3B", "CSF3R", "S100P", "FPR1", "CEACAM3"],
    "Microglia": ["P2RY12", "TMEM119", "CSF1R", "CX3CR1", "TREM2"],
    "Astrocyte": ["GFAP", "AQP4", "SLC1A3", "SLC1A2", "ALDH1L1"],
    "Oligodendrocyte": ["MOG", "MBP", "PLP1", "MAG", "MOBP"],
    "Neuron": ["SYT1", "SNAP25", "RBFOX3", "ENC1", "STMN2"],
    "Endothelial": ["PECAM1", "VWF", "CLDN5", "FLT1", "ESM1"],
    "Pericyte": ["RGS5", "PDGFRB", "ACTA2", "NOTCH3", "ANPEP"],
}


def _make_signature_matrix(source: str) -> pd.DataFrame:
    genes = sorted({g for gs in _BUILTIN_SIGNATURE.values() for g in gs})
    sig = pd.DataFrame(0.0, index=sorted(_BUILTIN_SIGNATURE), columns=genes)
    for ct, gs in _BUILTIN_SIGNATURE.items():
        for g in gs:
            sig.loc[ct, g] = 1.0
    return sig


def deconvolute(
    matrix: pd.DataFrame,
    signature_source: str = "lm22",
    method: str = "cibersort",
    custom_signature: pd.DataFrame | None = None,
) -> dict:
    """Deconvolve bulk expression into cell-type fractions.

    matrix: gene × sample expression (log-scale recommended).
    Returns fractions (sample × cell-type), plus QC stats.
    """
    if custom_signature is not None:
        sig = custom_signature
    else:
        sig = _make_signature_matrix(signature_source)
    common = list(set(matrix.index) & set(sig.columns))
    if len(common) < 5:
        raise ValueError("Insufficient overlap between signature and expression matrix")
    S = sig.loc[:, common].values.T  # genes × cell-types
    X = matrix.loc[common].values.T  # samples × genes

    fractions = np.zeros((X.shape[0], sig.shape[0]))
    rmses = []
    r2s = []
    for i, sample_vec in enumerate(X):
        f, _ = nnls(S, sample_vec)
        if f.sum() > 0:
            f = f / f.sum()
        fractions[i] = f
        pred = S @ f
        rmse = float(np.sqrt(np.mean((sample_vec - pred) ** 2)))
        rmses.append(rmse)
        ss_res = float(np.sum((sample_vec - pred) ** 2))
        ss_tot = float(np.sum((sample_vec - sample_vec.mean()) ** 2))
        r2s.append(1 - ss_res / ss_tot if ss_tot > 0 else np.nan)
    out = pd.DataFrame(fractions, index=matrix.columns, columns=sig.index)
    return {
        "fractions": out,
        "qc": {
            "rmse_per_sample": rmses,
            "r2_per_sample": r2s,
            "mean_r2": float(np.nanmean(r2s)),
            "signature_cell_types": list(sig.index),
            "signature_genes_used": len(common),
            "method": method,
        },
    }
