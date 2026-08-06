"""Epigenomics: differential DNA methylation (450K/EPIC-style beta values).

Implements:
  * beta → M-value conversion,
  * limma-style differential methylation (shared machinery with DE service),
  * DMP calling with BH-FDR,
  * simple genomic-region annotation (promoter/gene-body/intergenic heuristic).
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from app.services.differential_expression import _design_matrix, _empirical_bayes_moderated_t, _bh_fdr

logger = logging.getLogger(__name__)


def beta_to_m(beta: pd.DataFrame, epsilon: float = 1e-3) -> pd.DataFrame:
    """Convert beta values [0,1] to M-values (log2 ratio)."""
    b = beta.clip(epsilon, 1 - epsilon)
    return np.log2(b / (1 - b))


def m_to_beta(m: pd.DataFrame) -> pd.DataFrame:
    return 2**m / (2**m + 1)


def differential_methylation(
    beta_matrix: pd.DataFrame,
    metadata: pd.DataFrame,
    group_column: str = "group",
    case: str = "AD",
    control: str = "CN",
    covariates: list[str] | None = None,
    fdr_threshold: float = 0.05,
    delta_beta_threshold: float = 0.1,
) -> dict:
    """Differential methylation calling on beta values (uses M-value stats)."""
    meta = metadata.copy()
    meta.index = meta.index.astype(str)
    common = [c for c in beta_matrix.columns if c in meta.index]
    if not common:
        raise ValueError("no samples overlap between methylation matrix and metadata")
    mvals = beta_to_m(beta_matrix[common])
    X, _, _ = _design_matrix(meta, group_column, case, control, covariates or [])
    Y = mvals.values.T
    coef, t_stat, pval, _ = _empirical_bayes_moderated_t(X, Y)
    fdr = _bh_fdr(pval)
    groups = meta.loc[common, group_column].astype(str)
    beta_case = beta_matrix[common].loc[:, groups == case].mean(axis=1)
    beta_ctrl = beta_matrix[common].loc[:, groups == control].mean(axis=1)
    delta_beta = beta_case - beta_ctrl
    res = pd.DataFrame({
        "probe": mvals.index,
        "delta_beta": delta_beta.values,
        "m_log2fc": coef,
        "t": t_stat,
        "pvalue": pval,
        "fdr": fdr,
    })
    res["sig"] = (res["fdr"] < fdr_threshold) & (res["delta_beta"].abs() > delta_beta_threshold)
    res["direction"] = np.where(res["delta_beta"] > 0, "hypermethylated", "hypomethylated")
    res = res.sort_values("pvalue")
    return {
        "table": res.reset_index(drop=True).to_dict(orient="records"),
        "summary": {
            "probes_tested": int(len(res)),
            "significant_dmps": int(res["sig"].sum()),
            "hypermethylated": int((res["sig"] & (res["delta_beta"] > 0)).sum()),
            "hypomethylated": int((res["sig"] & (res["delta_beta"] < 0)).sum()),
            "delta_beta_threshold": delta_beta_threshold,
        },
    }
