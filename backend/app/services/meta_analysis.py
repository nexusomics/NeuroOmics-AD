"""Cross-cohort meta-analysis.

Combines per-cohort effect sizes (Cohen's d / Hedges' g / log2FC) with either
fixed-effects (inverse-variance) or random-effects (DerSimonian–Laird) models,
computing pooled effect, heterogeneity (I²), z-test p-values and BH-FDR.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats

from app.services.differential_expression import differential_expression_python

logger = logging.getLogger(__name__)


def _effect_size_cohens_d(control: np.ndarray, case: np.ndarray) -> tuple[float, float]:
    """Cohen's d (pooled SD) and its variance."""
    n1, n2 = len(control), len(case)
    sp = np.sqrt(((n1 - 1) * control.var(ddof=1) + (n2 - 1) * case.var(ddof=1)) / (n1 + n2 - 2) + 1e-12)
    d = (case.mean() - control.mean()) / sp
    var_d = (n1 + n2) / (n1 * n2) + d**2 / (2 * (n1 + n2))
    return d, var_d


def _effect_size_hedges_g(control: np.ndarray, case: np.ndarray) -> tuple[float, float]:
    d, var_d = _effect_size_cohens_d(control, case)
    n1, n2 = len(control), len(case)
    df_ = n1 + n2 - 2
    j = 1 - 3 / (4 * df_ - 1)
    return d * j, var_d * j**2


def _per_cohort_effects(matrix: pd.DataFrame, metadata: pd.DataFrame, case: str, control: str, method: str) -> pd.DataFrame:
    """Compute per-gene effect sizes within a single cohort."""
    meta = metadata.copy()
    meta.index = meta.index.astype(str)
    common = [c for c in matrix.columns if c in meta.index]
    if not common:
        return pd.DataFrame()
    m = matrix[common]
    g = meta.loc[common, "group"].astype(str)
    rows = {}
    for gene in m.index:
        case_vals = m.loc[gene, g == case].values.astype(float)
        ctrl_vals = m.loc[gene, g == control].values.astype(float)
        if len(case_vals) < 2 or len(ctrl_vals) < 2:
            continue
        if method == "log2fc":
            d = case_vals.mean() - ctrl_vals.mean()
            v = case_vals.var(ddof=1) / len(case_vals) + ctrl_vals.var(ddof=1) / len(ctrl_vals)
        elif method == "hedges_g":
            d, v = _effect_size_hedges_g(ctrl_vals, case_vals)
        else:
            d, v = _effect_size_cohens_d(ctrl_vals, case_vals)
        rows[gene] = (d, v)
    out = pd.DataFrame(rows, index=["effect", "var"]).T
    out.index.name = "gene"
    return out


def meta_analysis(
    matrices: list[pd.DataFrame],
    metadata_list: list[pd.DataFrame],
    case: str = "AD",
    control: str = "CN",
    effect_size_method: str = "cohens_d",
    fixed_effects: bool = True,
) -> dict:
    """Combine per-cohort effect sizes. Returns pooled table + heterogeneity metrics."""
    if len(matrices) != len(metadata_list):
        raise ValueError("matrices and metadata must have equal length")
    if len(matrices) < 2:
        raise ValueError("meta-analysis requires ≥ 2 cohorts")

    cohort_effects = []
    for i, (m, md) in enumerate(zip(matrices, metadata_list)):
        ce = _per_cohort_effects(m, md, case, control, effect_size_method)
        ce.columns = [f"effect_{i}", f"var_{i}"]
        cohort_effects.append(ce)
    merged = cohort_effects[0]
    for ce in cohort_effects[1:]:
        merged = merged.join(ce, how="outer")
    genes = merged.index
    n_cohorts = len(cohort_effects)

    pooled, pvals, i2s, qs = [], [], [], []
    for gene in genes:
        row = merged.loc[gene]
        eff = np.array([row[f"effect_{i}"] for i in range(n_cohorts)], dtype=float)
        var = np.array([row[f"var_{i}"] for i in range(n_cohorts)], dtype=float)
        valid = np.isfinite(eff) & (var > 0)
        if valid.sum() == 0:
            pooled.append(np.nan); pvals.append(np.nan); i2s.append(np.nan); qs.append(np.nan)
            continue
        eff, var = eff[valid], var[valid]
        w = 1.0 / var
        if fixed_effects or valid.sum() < 2:
            theta = (w * eff).sum() / w.sum()
            se = np.sqrt(1 / w.sum())
            q = np.nan
            i2 = np.nan
        else:
            # DerSimonian-Laird random effects
            theta_fe = (w * eff).sum() / w.sum()
            q = (w * (eff - theta_fe) ** 2).sum()
            df = valid.sum() - 1
            c = w.sum() - (w**2).sum() / w.sum()
            tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
            w_star = 1.0 / (var + tau2)
            theta = (w_star * eff).sum() / w_star.sum()
            se = np.sqrt(1 / w_star.sum())
            i2 = max(0.0, 100 * (q - df) / q) if q > 0 else 0.0
        z = theta / se
        p = 2 * stats.norm.sf(abs(z))
        pooled.append(theta); pvals.append(p); i2s.append(i2); qs.append(q)

    res = pd.DataFrame(
        {
            "gene": genes,
            "pooled_effect": pooled,
            "se": np.nan,
            "pvalue": pvals,
            "n_cohorts": n_cohorts,
        }
    )
    # recompute SE column cleanly
    se_vals = []
    for gene in genes:
        row = merged.loc[gene]
        var = np.array([row[f"var_{i}"] for i in range(n_cohorts)], dtype=float)
        valid = np.isfinite(var) & (var > 0)
        w = 1.0 / var[valid]
        se_vals.append(np.sqrt(1 / w.sum()) if w.sum() > 0 else np.nan)
    res["se"] = se_vals
    res["fdr"] = _bh_fdr(np.nan_to_num(res["pvalue"].values, nan=1.0))
    res["i2_percent"] = i2s
    res["heterogeneity_q"] = qs
    res["sig"] = res["fdr"] < 0.05
    res = res.sort_values("pvalue")
    return {
        "table": res.reset_index(drop=True).to_dict(orient="records"),
        "summary": {
            "cohorts": n_cohorts,
            "method": "fixed-effects (inverse variance)" if fixed_effects else "random-effects (DerSimonian-Laird)",
            "effect_size": effect_size_method,
            "genes_tested": int(len(res)),
            "significant": int(res["sig"].sum()),
            "median_i2": float(np.nanmedian(res["i2_percent"].values)) if np.isfinite(res["i2_percent"]).any() else None,
        },
    }


def _bh_fdr(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    n = len(p)
    adj = p[order] * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty_like(adj)
    out[order] = np.minimum(adj, 1.0)
    return out
