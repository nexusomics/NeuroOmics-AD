"""Cell-type-aware integration for bulk multi-omics.

Approach: deconvolve bulk expression into cell-type fractions (NNLS vs a
signature), then (a) adjust bulk features for composition before latent/causal
modeling, and (b) perform cell-type-conditioned association to nominate
cell-type-specific regulatory effects. Mirrors how snRNA-seq priors are used
to inform bulk models (e.g., TREM2-microglia axis).
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from app.services.deconvolution import deconvolute

logger = logging.getLogger(__name__)

CNS_CELL_SIGNATURES: dict[str, list[str]] = {
    "Microglia": ["TREM2", "TYROBP", "P2RY12", "CSF1R", "CX3CR1", "AIF1", "CD68", "SPI1", "IRF8", "C1QA"],
    "Astrocyte": ["GFAP", "AQP4", "SLC1A3", "SLC1A2", "ALDH1L1", "GJA1", "VIM"],
    "Oligodendrocyte": ["MOG", "MBP", "PLP1", "MAG", "MOBP", "OLIG1"],
    "Excitatory_Neuron": ["SLC17A7", "CAMK2A", "GRIN1", "SATB2", "NRGN", "SYT1"],
    "Inhibitory_Neuron": ["GAD1", "GAD2", "SLC32A1", "PVALB", "SST"],
    "Endothelial": ["PECAM1", "VWF", "CLDN5", "FLT1", "ESM1"],
    "Pericyte": ["RGS5", "PDGFRB", "ACTA2", "NOTCH3"],
}


def cell_fractions(matrix: pd.DataFrame) -> pd.DataFrame:
    """Bulk -> cell-type fractions using the CNS signature panel (NNLS)."""
    sig = pd.DataFrame(0.0, index=list(CNS_CELL_SIGNATURES), columns=sorted({g for gs in CNS_CELL_SIGNATURES.values() for g in gs}))
    for ct, gs in CNS_CELL_SIGNATURES.items():
        for g in gs:
            if g in sig.columns:
                sig.loc[ct, g] = 1.0
    res = deconvolute(matrix, signature_source="lm22", method="cibersort", custom_signature=sig)
    return res["fractions"]


def composition_adjusted(matrix: pd.DataFrame, fractions: pd.DataFrame) -> pd.DataFrame:
    """Regress out cell-type composition from bulk features (per-gene OLS)."""
    F = fractions.values  # samples x celltypes
    F = np.column_stack([np.ones(F.shape[0]), F])
    X = matrix.values.astype(float)
    beta = np.linalg.pinv(F.T @ F) @ F.T @ X.T  # (ct+1) x genes
    resid = X.T - F @ beta
    return pd.DataFrame(resid.T, index=matrix.index, columns=matrix.columns)


def celltype_conditioned_assoc(
    matrix: pd.DataFrame,
    fractions: pd.DataFrame,
    feature: str,
    phenotype: pd.Series,
) -> dict:
    """Association of a bulk feature with phenotype conditioned on composition.

    Reports the bulk (marginal) and composition-adjusted (conditional) effect
    to reveal whether a signal is explained by cell-type shifts vs within-cell
    regulation.
    """
    y = phenotype.astype(float).reindex(matrix.columns)
    x = matrix.loc[feature].astype(float)
    ok = y.notna() & x.notna()
    # marginal
    slope_m, _, r_m, p_m, _ = __import__("scipy.stats", fromlist=["linregress"]).linregress(x[ok], y[ok])
    # conditional: include microglia/neuron fractions
    F = fractions.reindex(matrix.columns).fillna(0.0)
    cols = [f for f in F.columns if f in ("Microglia", "Astrocyte", "Excitatory_Neuron", "Inhibitory_Neuron")]
    D = np.column_stack([np.ones(ok.sum()), x[ok].values] + [F.loc[ok, c].values for c in cols])
    beta = np.linalg.lstsq(D, y[ok].values, rcond=None)[0]
    resid = y[ok].values - D @ beta
    dof = len(resid) - D.shape[1]
    se = np.sqrt(np.sum(resid**2) / dof) / (np.std(D[:, 1], ddof=1) * np.sqrt(len(resid) - 1) + 1e-12)
    t = beta[1] / (se + 1e-12)
    p_c = 2 * __import__("scipy.stats", fromlist=["t"]).t.sf(abs(t), dof)
    return {"feature": feature, "marginal_beta": float(slope_m), "marginal_p": float(p_m),
            "adjusted_beta": float(beta[1]), "adjusted_p": float(p_c),
            "interpretation": "within-cell regulation" if p_c < 0.05 and p_m < 0.05 else "composition-driven" if p_m < 0.05 else "null"}
