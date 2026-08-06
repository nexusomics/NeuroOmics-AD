"""Data harmonization & quality control engine.

Implements the Layer-2 pipeline of the platform:
  * normalization (quantile, TMM-style, variance-stabilizing)
  * missing-value imputation (KNN, mean, median)
  * batch-effect correction (ComBat-style empirical Bayes)
  * outlier detection (robust z-score / PCA)
  * QC metrics (sample correlations, library stats)
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.impute import KNNImputer
from sklearn.preprocessing import QuantileTransformer

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Normalization
# --------------------------------------------------------------------------
def normalize_quantile(df: pd.DataFrame) -> pd.DataFrame:
    """Quantile normalization across samples (columns)."""
    q = QuantileTransformer(n_quantiles=min(1000, max(10, df.shape[0])), output_distribution="normal", random_state=0)
    out = pd.DataFrame(q.fit_transform(df.values), index=df.index, columns=df.columns)
    return out


def normalize_tmm(df: pd.DataFrame) -> pd.DataFrame:
    """Trimmed mean of M-values (TMM-style) — returns normalized counts (log-scale safe)."""
    logm = np.log2(np.where(df.values <= 0, np.nan, df.values))
    ref = np.nanmean(logm, axis=1)  # pseudo-reference per gene
    with np.errstate(all="ignore"):
        m = logm - ref[:, None]
        a = (logm + ref[:, None]) / 2.0
    m = np.nan_to_num(m, nan=0.0, posinf=0.0, neginf=0.0)
    a = np.nan_to_num(a, nan=1.0, posinf=1.0, neginf=1.0)
    trim_m = np.percentile(np.abs(m), 90) or 1.0
    keep = np.abs(m) <= trim_m
    with np.errstate(all="ignore"):
        w = 1.0 / np.maximum(a, 1e-6)
        weights = np.where(keep, w, 0.0)
        norm = np.nansum(m * weights, axis=0) / np.maximum(np.nansum(weights, axis=0), 1e-9)
    lib_size = df.sum(axis=0).replace(0, np.nan)
    scale = np.exp2(norm) * lib_size / np.nanmean(lib_size)
    out = df.divide(scale, axis=1)
    return out


def normalize_vst(df: pd.DataFrame, pseudo: float = 1.0) -> pd.DataFrame:
    """Variance-stabilizing-ish transform: log2(x + pseudo) after size-factor scaling."""
    size_factors = df.sum(axis=0)
    sf = size_factors / size_factors.mean()
    scaled = df.divide(sf, axis=1)
    return np.log2(scaled + pseudo)


def normalize(method: str, df: pd.DataFrame) -> pd.DataFrame:
    if method == "quantile":
        return normalize_quantile(df)
    if method == "tmm":
        return normalize_tmm(df)
    if method == "vst":
        return normalize_vst(df)
    return df


# --------------------------------------------------------------------------
# Imputation
# --------------------------------------------------------------------------
def impute_knn(df: pd.DataFrame, n_neighbors: int = 5) -> pd.DataFrame:
    """KNN imputation on transposed (sample × gene) space to exploit sample similarity."""
    imp = KNNImputer(n_neighbors=n_neighbors, weights="distance")
    out = imp.fit_transform(df.values.T).T
    return pd.DataFrame(out, index=df.index, columns=df.columns)


def impute_mice_like(df: pd.DataFrame, max_iter: int = 5, random_state: int = 0) -> pd.DataFrame:
    """Iterative chained-equation style imputation using ridge regression per column."""
    rng = np.random.default_rng(random_state)
    X = df.values.copy().astype(float)
    missing = np.isnan(X)
    if not missing.any():
        return df
    for col in range(X.shape[1]):
        if missing[:, col].any():
            mean = np.nanmean(X[:, col])
            X[np.isnan(X[:, col]), col] = mean
    observed = ~missing
    for _ in range(max_iter):
        for col in range(X.shape[1]):
            miss_rows = np.where(missing[:, col])[0]
            if not len(miss_rows):
                continue
            obs_rows = np.where(observed[:, col])[0]
            Xobs, yobs = X[obs_rows], X[obs_rows, col]
            # standardize features to avoid scale dominance
            mu = Xobs.mean(axis=0)
            sd = Xobs.std(axis=0) + 1e-9
            Xs = (Xobs - mu) / sd
            # ridge closed form
            ridge = 1.0
            beta = np.linalg.solve(Xs.T @ Xs + ridge * np.eye(Xs.shape[1]), Xs.T @ yobs)
            Xmiss = (X[miss_rows] - mu) / sd
            pred = Xmiss @ beta
            noise = rng.normal(0, yobs.std() * 0.1, size=len(miss_rows))
            X[miss_rows, col] = pred + noise
    return pd.DataFrame(X, index=df.index, columns=df.columns)


def impute(method: str, df: pd.DataFrame) -> pd.DataFrame:
    if method == "knn":
        return impute_knn(df)
    if method == "mice":
        return impute_mice_like(df)
    if method == "median":
        return df.fillna(df.median(axis=0))
    return df


# --------------------------------------------------------------------------
# Batch correction (ComBat-style empirical Bayes)
# --------------------------------------------------------------------------
def combat_batch_correction(df: pd.DataFrame, batch_labels: pd.Series, mod: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Empirical-Bayes batch correction (ComBat algorithm, parametric).

    Reference: Johnson, Li & Rabinovic (2007) Biostatistics.
    """
    batches = list(dict.fromkeys(batch_labels.astype(str)))
    if len(batches) < 2:
        return df
    design = pd.DataFrame({f"B_{b}": (batch_labels.astype(str) == b).astype(float) for b in batches})
    if mod is not None and len(mod.columns):
        design = pd.concat([mod.reset_index(drop=True), design.reset_index(drop=True)], axis=1)
    X = df.values.T  # samples × genes
    n, p = X.shape
    Xd = np.column_stack([np.ones(n), design.values])
    XtX_inv = np.linalg.pinv(Xd.T @ Xd)
    beta = XtX_inv @ Xd.T @ X
    resid = X - Xd @ beta
    # per-batch variance priors
    var_pooled = resid.var(axis=0) + 1e-9
    batch_inds = {b: np.where(batch_labels.astype(str) == b)[0] for b in batches}
    gamma_hat = np.array([beta[1:, :][list(design.columns).index(f"B_{b}")] for b in batches]) if False else None
    gamma_star = np.zeros((len(batches), p))
    delta_star = np.ones((len(batches), p))
    for i, b in enumerate(batches):
        idx = batch_inds[b]
        if len(idx) < 2:
            continue
        rb = resid[idx]
        xb = X[idx]
        n_b = len(idx)
        Xb_d = np.column_stack([np.ones(n_b), design.values[idx]])
        beta_b = np.linalg.pinv(Xb_d.T @ Xb_d) @ Xb_d.T @ xb
        gamma_b = beta_b[0] - beta[0]  # intercept shift relative to grand fit
        gamma_star[i] = gamma_b
        r2 = xb - Xb_d @ beta_b
        with np.errstate(all="ignore"):
            delta_b = np.sqrt(r2.var(axis=0)) + 1e-9
        delta_star[i] = delta_b
    # empirical Bayes shrinkage
    gamma_mean = gamma_star.mean(axis=0)
    gamma_var = gamma_star.var(axis=0) + 1e-9
    for i, b in enumerate(batches):
        idx = batch_inds[b]
        n_b = len(idx)
        delta2 = delta_star[i] ** 2
        shrink = (n_b * gamma_var) / (n_b * gamma_var + delta2 + 1e-9)
        gamma_adj = (1 - shrink) * gamma_mean + shrink * gamma_star[i]
        X[idx] = X[idx] - np.outer(np.ones(n_b), gamma_adj)
        X[idx] = X[idx] * (np.sqrt(var_pooled) / delta_star[i])
    corrected = pd.DataFrame(X, index=df.columns, columns=df.index).T
    corrected.index = df.index
    corrected.columns = df.columns
    return corrected


# --------------------------------------------------------------------------
# Outlier detection
# --------------------------------------------------------------------------
def detect_outliers(df: pd.DataFrame, z_threshold: float = 4.0) -> list[str]:
    """Robust z-score (median/MAD) outlier detection on sample-level PC1/PC2."""
    X = df.values.T
    X = np.nan_to_num(X, nan=0.0)
    if X.shape[1] > 3:
        pca = PCA(n_components=2)
        score = pca.fit_transform(X)
    else:
        score = X
    med = np.median(score, axis=0)
    mad = np.median(np.abs(score - med), axis=0) + 1e-9
    z = np.abs((score - med) / mad).max(axis=1)
    return [str(c) for c, zi in zip(df.columns, z) if zi > z_threshold]


def remove_outliers(df: pd.DataFrame, z_threshold: float = 4.0) -> tuple[pd.DataFrame, list[str]]:
    outliers = detect_outliers(df, z_threshold)
    return df.drop(columns=outliers, errors="ignore"), outliers


# --------------------------------------------------------------------------
# QC metrics
# --------------------------------------------------------------------------
def qc_report(df: pd.DataFrame, batch_labels: Optional[pd.Series] = None) -> dict:
    """Compute QC metrics describing the (normalized) dataset.

    `df` is a gene × sample matrix; correlations are computed sample-wise.
    """
    X = df.values.astype(float).T  # samples × genes
    X = np.nan_to_num(X, nan=0.0)
    corr = np.corrcoef(X)
    n = corr.shape[0]
    off = corr[~np.eye(n, dtype=bool)]
    metrics = {
        "n_samples": int(df.shape[1]),
        "n_features": int(df.shape[0]),
        "missing_fraction": float(np.isnan(df.values).mean()),
        "mean_expression": float(np.nanmean(X)),
        "median_sample_correlation": float(np.nanmedian(off)),
        "min_sample_correlation": float(np.nanmin(off)),
        "top_variable_genes": [str(g) for g in df.index[np.argsort(-X.var(axis=1))[:10]]],
        "library_size_mean": float(X.sum(axis=0).mean()),
    }
    if batch_labels is not None:
        b = batch_labels.astype(str)
        within, between = [], []
        for i in range(n):
            for j in range(i + 1, n):
                same = b.iloc[i] == b.iloc[j]
                (within if same else between).append(corr[i, j])
        metrics["mean_corr_within_batch"] = float(np.mean(within)) if within else None
        metrics["mean_corr_between_batch"] = float(np.mean(between)) if between else None
    return metrics


# --------------------------------------------------------------------------
# Full pipeline
# --------------------------------------------------------------------------
def run_preprocessing(
    df: pd.DataFrame,
    metadata: Optional[pd.DataFrame] = None,
    normalize_method: str = "quantile",
    log_transform: bool = False,
    batch_correct: bool = False,
    batch_column: str = "batch",
    impute_method: str = "knn",
    remove_outlier_samples: bool = True,
) -> dict:
    """End-to-end harmonization pipeline returning processed matrix + report dict."""
    report: dict = {"steps": [], "outliers": []}
    out = df.copy().astype(float)
    out = out.replace([np.inf, -np.inf], np.nan)

    if impute_method and out.isna().any().any():
        out = impute(impute_method, out)
        report["steps"].append(f"imputation ({impute_method})")

    if batch_correct and metadata is not None and batch_column in metadata.columns:
        labels = metadata[batch_column].reindex(out.columns).astype(str)
        if len(set(labels)) > 1:
            out = combat_batch_correction(out, labels)
            report["steps"].append(f"batch correction (ComBat, {batch_column})")

    if normalize_method and normalize_method != "none":
        out = normalize(normalize_method, out)
        report["steps"].append(f"normalization ({normalize_method})")

    if log_transform:
        out = np.log2(out + 1.0)
        report["steps"].append("log2 transform")

    if remove_outlier_samples:
        out, outliers = remove_outliers(out)
        report["outliers"] = outliers
        if outliers:
            report["steps"].append(f"removed {len(outliers)} outlier samples")

    report["qc"] = qc_report(out, metadata[batch_column].reindex(out.columns) if metadata is not None and batch_column in metadata.columns else None)
    return {"matrix": out, "report": report}
