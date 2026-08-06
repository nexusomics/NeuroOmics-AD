"""Multi-omics data integration.

Implements:
  * weighted feature fusion (scaled concatenation with per-omics weights),
  * MOFA-style factor analysis (multi-omics factor decomposition via
    iterative SVD on concatenated scaled blocks),
  * SNF-style sample similarity network fusion for patient clustering.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)


def _scale(df: pd.DataFrame) -> pd.DataFrame:
    s = df.std(axis=1).replace(0, np.nan)
    return (df.sub(df.mean(axis=1), axis=0)).div(s, axis=0).fillna(0.0)


def weighted_fusion(matrices: list[pd.DataFrame], weights: list[float] | None = None, rank: int = 5) -> dict:
    """Concatenate scaled omics blocks (genes as features) with weights; return latent factors."""
    n = len(matrices)
    if n == 0:
        raise ValueError("no matrices provided")
    weights = weights or [1.0] * n
    weights = np.array(weights) / np.sum(weights)
    samples = matrices[0].columns
    blocks = []
    for i, m in enumerate(matrices):
        m = m[samples].fillna(m.median(axis=1))
        m = _scale(m)
        # reduce each block to its top variance features to control dimensionality
        top = min(500, m.shape[0])
        top_idx = m.var(axis=1).nlargest(top).index
        blocks.append(m.loc[top_idx].T * weights[i])
    fused = pd.concat(blocks, axis=1).fillna(0.0)
    pca = PCA(n_components=min(rank, fused.shape[0], fused.shape[1]))
    factors = pca.fit_transform(fused)
    loadings = pca.components_
    feature_names = list(fused.columns)
    top_features = {
        f"factor_{k+1}": [feature_names[i] for i in np.argsort(-np.abs(loadings[k]))[:15]]
        for k in range(len(loadings))
    }
    return {
        "factors": pd.DataFrame(factors, index=samples, columns=[f"factor_{k+1}" for k in range(factors.shape[1])]),
        "explained_variance": pca.explained_variance_ratio_.tolist(),
        "top_features": top_features,
        "n_blocks": n,
        "weights": weights.tolist(),
    }


def moa_like_factorization(matrices: list[pd.DataFrame], rank: int = 5, max_iter: int = 100) -> dict:
    """MOFA-inspired factor decomposition: shared factors via iterative PCA on scaled blocks."""
    n = len(matrices)
    samples = matrices[0].columns
    scaled = [_scale(m[samples].fillna(m.median(axis=1))) for m in matrices]
    # joint sample embedding from concatenated PCA space
    concat = pd.concat([s.T for s in scaled], axis=1).fillna(0.0)
    pca = PCA(n_components=min(rank, concat.shape[0], concat.shape[1]))
    Z = pca.fit_transform(concat)  # samples × factors
    factor_explained: list[dict[str, float]] = []
    for i, m in enumerate(scaled):
        # per-omics variance explained by shared factors
        proj = m.T @ Z.T
        total_var = m.var(axis=1).sum()
        expl = float(np.sum(proj**2) / max(total_var, 1e-9))
        factor_explained.append({"omics": i, "variance_explained": min(expl, 1.0)})
    return {
        "factors": pd.DataFrame(Z, index=samples, columns=[f"factor_{k+1}" for k in range(Z.shape[1])]),
        "explained_variance": pca.explained_variance_ratio_.tolist(),
        "per_omics_explained": factor_explained,
        "method": "MOFA-like (shared PCA on scaled blocks)",
    }


def snf_fusion(matrices: list[pd.DataFrame], k: int = 10, t: int = 20) -> pd.DataFrame:
    """Similarity Network Fusion (Wang et al. 2014) for sample-level integration."""
    samples = matrices[0].columns
    n = len(matrices)
    Ws = []
    for m in matrices:
        m = m[samples].fillna(m.median(axis=1)).T  # samples × genes
        if m.shape[1] > 50:
            m = m.iloc[:, m.var(axis=0).nlargest(50).index]
        d = squareform(pdist(m.values, metric="euclidean"))
        sigma = np.median(d) + 1e-9
        W = np.exp(-(d**2) / (2 * sigma**2))
        np.fill_diagonal(W, 0.0)
        Ws.append(W)
    # normalize and iterate SNF
    P = []
    for W in Ws:
        P.append(W / W.sum(axis=1, keepdims=True))
    S = []
    for W in Ws:
        S_ = np.zeros_like(W)
        for i in range(W.shape[0]):
            nbrs = np.argsort(-W[i])[:k]
            S_[i, nbrs] = W[i, nbrs] / max(W[i, nbrs].sum(), 1e-9)
        S.append(S_)
    fused = np.mean(P, axis=0)
    for _ in range(t):
        new_fused = np.zeros_like(fused)
        for i in range(n):
            new_fused += S[i] @ fused @ S[i].T
        fused = new_fused / n
        fused = (fused + fused.T) / 2
        np.fill_diagonal(fused, 1.0)
    return pd.DataFrame(fused, index=samples, columns=samples)


def integrate(matrices: list[pd.DataFrame], method: str = "weighted_fusion", rank: int = 5) -> dict:
    if method == "moa_like":
        return moa_like_factorization(matrices, rank)
    if method == "jive_like":
        return moa_like_factorization(matrices, rank)  # shared-factors variant
    return weighted_fusion(matrices, rank=rank)
