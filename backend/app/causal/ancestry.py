"""Ancestry-stratified association & trans-ethnic meta-analysis.

Per-ancestry association of omics features with a phenotype (OLS with ancestry
PCs + covariates), then inverse-variance fixed-effect and DerSimonian–Laird
random-effect meta-analysis across ancestries with I² and Cochran's Q, flagging
ancestry-specific signals (significant heterogeneity + one-ancestry-only
effect). Mirrors the design that revealed >60% of EUR/AFR plasma proteomic and
metabolomic findings as previously unreported.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


def stratified_association(
    matrix: pd.DataFrame,  # features x samples
    phenotype: pd.Series,
    ancestry: pd.Series,
    covariates: pd.DataFrame | None = None,
    fdr_method: str = "bh",
) -> dict:
    """Per-ancestry, per-feature association (OLS). Returns betas/SEs/p."""
    out = {}
    for anc in ancestry.astype(str).unique():
        idx = ancestry.astype(str) == anc
        X = matrix.loc[:, idx].astype(float)
        y = phenotype.reindex(X.columns).astype(float)
        ok = y.notna() & ~X.isna().any(axis=0)
        X, y = X.loc[:, ok], y[ok]
        design = np.column_stack([np.ones(X.shape[1]), (y.values)])
        if covariates is not None:
            C = covariates.reindex(X.columns).fillna(0.0)
            design = np.column_stack([design, C.values])
        D = np.column_stack([np.ones(X.shape[1]), y.values] + ([covariates.reindex(X.columns).fillna(0.0).values] if covariates is not None else []))
        beta, se, p = [], [], []
        for f in X.index:
            xv = X.loc[f].values
            if np.std(xv) == 0:
                beta.append(0.0); se.append(np.nan); p.append(1.0)
                continue
            B = np.linalg.lstsq(D, xv, rcond=None)[0]
            resid = xv - D @ B
            dof = len(xv) - D.shape[1]
            sigma2 = np.sum(resid**2) / max(dof, 1)
            covB = sigma2 * np.linalg.pinv(D.T @ D)
            se_b = np.sqrt(covB[1, 1]) if np.isfinite(covB[1, 1]) else np.nan
            t = B[1] / (se_b + 1e-12)
            beta.append(float(B[1])); se.append(float(se_b)); p.append(float(2 * stats.t.sf(abs(t), max(dof, 1))))
        fdr = _fdr(p)
        out[anc] = pd.DataFrame({"feature": X.index, "beta": beta, "se": se, "pvalue": p, "fdr": fdr,
                                 "n": int(X.shape[1]), "ancestry": anc})
    return out


def transethnic_meta(
    results: dict[str, pd.DataFrame],
    features: list[str] | None = None,
    random_effects: bool = True,
) -> pd.DataFrame:
    """Meta-analyze per-ancestry betas/SEs; report I², Q, and ancestry-specific flags."""
    anc_names = list(results)
    if features is None:
        features = sorted({f for df in results.values() for f in df["feature"]})
    rows = []
    for f in features:
        betas, ses = [], []
        for a in anc_names:
            row = results[a][results[a]["feature"] == f]
            if len(row) and np.isfinite(row["se"].iloc[0]) and row["se"].iloc[0] > 0:
                betas.append((a, row["beta"].iloc[0], row["se"].iloc[0], row["pvalue"].iloc[0]))
        if len(betas) < 2:
            continue
        b = np.array([x[1] for x in betas]); v = np.array([x[2] ** 2 for x in betas])
        w = 1.0 / v
        b_fe = float(np.sum(w * b) / np.sum(w))
        se_fe = float(np.sqrt(1 / np.sum(w)))
        z = b_fe / (se_fe + 1e-12)
        p_fe = 2 * stats.norm.sf(abs(z))
        q = float(np.sum(w * (b - b_fe) ** 2))
        dof = len(b) - 1
        i2 = max(0.0, 100 * (q - dof) / q) if q > 0 else 0.0
        q_p = float(stats.chi2.sf(q, dof))
        if random_effects:
            c = np.sum(w) - np.sum(w**2) / np.sum(w)
            tau2 = max(0.0, (q - dof) / c) if c > 0 else 0.0
            w_star = 1.0 / (v + tau2)
            b_re = float(np.sum(w_star * b) / np.sum(w_star))
            se_re = float(np.sqrt(1 / np.sum(w_star)))
            b_eff, se_eff = b_re, se_re
            method = "random-effects (DL)"
        else:
            b_eff, se_eff = b_fe, se_fe
            method = "fixed-effects (IV)"
        z_eff = b_eff / (se_eff + 1e-12)
        p_eff = 2 * stats.norm.sf(abs(z_eff))
        # ancestry-specific flag: heterogeneity significant + only one ancestry nominal
        anc_p = {x[0]: x[3] for x in betas}
        sig_anc = [a for a, p in anc_p.items() if p < 0.05]
        specific = bool(q_p < 0.05 / max(len(features), 1) and len(sig_anc) == 1)
        rows.append({"feature": f, "beta": b_eff, "se": se_eff, "pvalue": p_eff, "n_ancestries": len(betas),
                     "i2_percent": round(i2, 1), "q_pvalue": q_p, "method": method,
                     "ancestry_specific": specific, "ancestry_effects": {a: round(b, 4) for a, b, _, _ in betas}})
    meta = pd.DataFrame(rows)
    if len(meta):
        meta["fdr"] = _fdr(meta["pvalue"].values)
    return meta.sort_values("pvalue")


def _fdr(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    n = len(p)
    adj = p[order] * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty_like(adj)
    out[order] = np.minimum(adj, 1.0)
    return out
