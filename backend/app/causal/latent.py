"""Multi-omics latent representation layer.

Implements:
  * Multi-block PLS (DIABLO-style; Rohart et al. 2017): each omics block is
    projected to a component maximizing covariance with a phenotype/design,
    with **missing-block handling** (blocks missing per sample are skipped and
    weights renormalized).
  * MOFA-style shared-factor factorization (Argelaguet et al. 2018): iterative
    low-rank completion (soft-impute-like) so samples with missing modalities
    still receive latent factors.
  * Deep variational autoencoder (optional, PyTorch) with PCA fallback for
    per-modality compression (used when torch is unavailable).
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _center(df: pd.DataFrame) -> pd.DataFrame:
    return df.sub(df.mean(axis=1), axis=0)


def multiblock_pls(
    blocks: list[pd.DataFrame],  # each genes x samples (aligned columns)
    design: Optional[pd.DataFrame] = None,  # samples x phenotype(s)
    n_components: int = 3,
    max_iter: int = 100,
    seed: int = 42,
    top_k_genes: int = 6,
) -> dict:
    """Sparse multi-block PLS (DIABLO-style; Rohart et al. 2017).

    For each component, per block: standardize genes, take the top-|cov|
    genes with the (deflated) outcome, project → block score; combine across
    blocks with per-sample presence renormalization (missing modalities
    contribute zero and the denominator counts observed blocks).
    """
    rng = np.random.default_rng(seed)
    samples = sorted(set().union(*[set(b.columns) for b in blocks]))
    n = len(samples)
    blocks = [b.reindex(columns=samples) for b in blocks]
    mask = np.ones((len(blocks), n), dtype=bool)
    for bi, b in enumerate(blocks):
        mask[bi] = ~b.isna().any(axis=0).values
    if design is None:
        Y = pd.DataFrame(np.eye(n), index=samples)
    else:
        Y = design.copy().astype(float).reindex(samples).fillna(0.0)
    Y = Y - Y.mean(axis=0)
    scores = np.zeros((n, n_components))
    for comp in range(n_components):
        num, den = np.zeros(n), np.zeros(n)
        for bi, b in enumerate(blocks):
            obs = mask[bi]
            if obs.sum() < 5:
                continue
            Xb = b.T.values.astype(float)  # samples x genes
            # NaN-aware: fill missing-sample rows with the gene's observed mean
            col_mean = np.nanmean(Xb, axis=0)
            col_mean = np.where(np.isnan(col_mean), 0.0, col_mean)
            Xb = np.where(np.isnan(Xb), col_mean, Xb)
            Xb = Xb - Xb.mean(axis=0)
            sd = Xb.std(axis=0) + 1e-9
            Xb = Xb / sd
            Xb[~obs] = 0.0  # missing rows contribute nothing
            yv = Y.values  # samples x d
            cov = Xb.T @ yv  # genes x d
            score_gene = np.linalg.norm(cov, axis=1)
            keep = np.argsort(-score_gene)[: min(top_k_genes, len(score_gene))]
            w = cov[keep].mean(axis=1)
            w = w / (np.linalg.norm(w) + 1e-9)
            s = Xb[:, keep] @ w
            num += np.where(obs, s, 0.0)
            den += obs.astype(float)
        s_all = np.divide(num, den, out=np.zeros(n), where=den > 0)
        scores[:, comp] = s_all
        # deflate outcome
        if np.linalg.norm(s_all) > 1e-9:
            Y = Y - np.outer(s_all, (s_all @ Y.values) / (s_all @ s_all + 1e-9))
    latent = pd.DataFrame(scores, index=samples, columns=[f"LV{comp+1}" for comp in range(n_components)])
    return {"latent": latent, "block_loadings": None, "n_blocks": len(blocks),
            "method": "sparse multi-block PLS (DIABLO-style)"}


def mofa_like_factors(
    blocks: list[pd.DataFrame],
    n_factors: int = 5,
    max_iter: int = 50,
    tol: float = 1e-4,
    seed: int = 42,
) -> dict:
    """MOFA-style shared factors with missing-modality completion.

    Alternates between estimating factor weights W_k (factors x features) and
    sample factors Z (samples x factors), using only observed samples per block
    (soft-impute style). Missing blocks are handled within the latent space.
    """
    rng = np.random.default_rng(seed)
    samples = sorted(set().union(*[set(b.columns) for b in blocks]))
    n = len(samples)
    blocks = [b.reindex(columns=samples) for b in blocks]
    scaled = []
    for b in blocks:
        st = b.sub(b.mean(axis=1), axis=0).div(b.std(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
        scaled.append(st.values.T)  # samples x genes
    masks = [~b.isna().any(axis=0).values for b in blocks]
    k = min(n_factors, n - 2, min(sc.shape[1] for sc in scaled))
    concat = np.column_stack([np.nan_to_num(sc, nan=0.0) for sc in scaled])
    U, S, _ = np.linalg.svd(concat, full_matrices=False)
    Z = U[:, :k].copy()
    Ws = []
    for sc in scaled:
        obs = masks[bi] if False else None
        Ws.append(np.zeros((k, sc.shape[1])))
    # initialize weights by regression on observed rows
    for bi, sc in enumerate(scaled):
        obs = masks[bi]
        if obs.sum() > k + 1:
            Ws[bi] = np.linalg.pinv(Z[obs].T @ Z[obs] + 1e-4 * np.eye(k)) @ Z[obs].T @ sc[obs]
        else:
            Ws[bi] = np.linalg.pinv(Z.T @ Z + 1e-4 * np.eye(k)) @ Z.T @ np.nan_to_num(sc)
    for _ in range(max_iter):
        Z_prev = Z.copy()
        for bi, sc in enumerate(scaled):
            obs = masks[bi]
            if obs.sum() > k + 1:
                Zo = Z[obs]
                Ws[bi] = np.linalg.pinv(Zo.T @ Zo + 1e-4 * np.eye(k)) @ Zo.T @ sc[obs]
        # update Z: average per-block contributions (observed only)
        num = np.zeros((n, k)); den = np.zeros((n, k))
        for bi, sc in enumerate(scaled):
            obs = masks[bi]
            score = sc @ Ws[bi].T  # n x k
            num += np.where(obs[:, None], score, 0.0)
            den += np.where(obs[:, None], 1.0, 0.0)
        Z = np.divide(num, den, out=np.zeros((n, k)), where=den > 0)
        Z, _ = np.linalg.qr(Z)
        if np.linalg.norm(Z - Z_prev) < tol:
            break
    var_explained = []
    for bi, sc in enumerate(scaled):
        rec = Z @ Ws[bi]
        total = np.nanvar(sc)
        var_explained.append(float(1 - np.nanvar(sc - rec) / (total + 1e-9)))
    return {
        "factors": pd.DataFrame(Z, index=samples, columns=[f"F{k_i+1}" for k_i in range(k)]),
        "weights": Ws,
        "variance_explained_per_block": var_explained,
        "method": "MOFA-like (soft-impute shared factors)",
        "missing_fraction": float(1 - np.mean([m.mean() for m in masks])),
    }


def vae_latent(
    matrix: pd.DataFrame,
    latent_dim: int = 16,
    epochs: int = 40,
    seed: int = 42,
) -> dict:
    """Variational autoencoder compression (PyTorch if available; PCA fallback)."""
    X = matrix.T.values.astype(float)  # samples x genes
    X = np.nan_to_num(X, nan=np.nanmean(X, axis=0, keepdims=True))
    from sklearn.preprocessing import StandardScaler

    X = StandardScaler().fit_transform(X)
    try:
        import torch
        import torch.nn as nn

        torch.manual_seed(seed)
        d, h = X.shape[1], 64
        enc = nn.Sequential(nn.Linear(h, 128), nn.ReLU(), nn.Linear(128, latent_dim * 2))
        dec = nn.Sequential(nn.Linear(latent_dim, 128), nn.ReLU(), nn.Linear(128, h))
        opt = torch.optim.Adam(list(enc.parameters()) + list(dec.parameters()), lr=1e-3)
        Xt = torch.tensor(X, dtype=torch.float32)
        for _ in range(epochs):
            opt.zero_grad()
            z_params = enc(Xt)
            mu, logvar = z_params[:, :latent_dim], z_params[:, latent_dim:]
            eps = torch.randn_like(mu)
            z = mu + eps * torch.exp(0.5 * logvar)
            recon = dec(z)
            recon_loss = torch.nn.functional.mse_loss(recon, Xt)
            kl = -0.5 * torch.sum(1 + logvar - mu**2 - torch.exp(logvar))
            (recon_loss + 1e-4 * kl).backward()
            opt.step()
        with torch.no_grad():
            mu = enc(Xt)[:, :latent_dim].numpy()
        method = "VAE (PyTorch)"
    except Exception:  # noqa: BLE001 - no torch / no GPU
        from sklearn.decomposition import PCA

        pca = PCA(n_components=min(latent_dim, X.shape[0], X.shape[1]))
        mu = pca.fit_transform(X)
        method = "PCA fallback (torch unavailable)"
    return {
        "latent": pd.DataFrame(mu, index=matrix.columns, columns=[f"Z{i+1}" for i in range(mu.shape[1])]),
        "method": method,
    }
