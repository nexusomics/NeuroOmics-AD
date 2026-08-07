"""QC & surrogate-variable layer for the causal multi-omics module.

Implements:
  * Surrogate Variable Analysis (SVA; Leek & Storey 2007) — iteratively
    reweighted SVD to estimate hidden confounders for transcriptomics.
  * PEER-inspired factor inference (Stegle et al. 2010) — factor model over
    residualized data (computational PEER proxy).
  * ComBat-style empirical-Bayes batch correction (Johnson et al. 2007) and a
    linear mixed-model (LMM) batch adjustment (used for proteomics/metabolomics).
  * Ancestry-aware genotype QC: per-variant filters, LD-light pruning, PCA to
    estimate ancestry PCs, and admixture-like cluster assignment.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Surrogate Variable Analysis (SVA)
# ---------------------------------------------------------------------------
def estimate_sva(
    expression: pd.DataFrame,  # genes x samples
    phenotype: Optional[pd.Series] = None,
    covariates: Optional[pd.DataFrame] = None,
    n_sv: Optional[int] = None,
    max_n_sv: int = 10,
    seed: int = 42,
) -> pd.DataFrame:
    """Estimate surrogate variables capturing hidden confounders.

    Returns an (n_sv x samples) DataFrame of surrogate variables.
    """
    X = expression.values.astype(float)  # genes x samples
    X = np.nan_to_num(X, nan=np.nanmean(X, axis=1, keepdims=True))
    n_genes, n_samps = X.shape
    rng = np.random.default_rng(seed)

    # design matrix of observed covariates (intercept + optional phenotype)
    design_cols = []
    if covariates is not None:
        for col in covariates.columns:
            v = pd.to_numeric(covariates[col], errors="coerce").fillna(0.0).values
            design_cols.append(v)
    if phenotype is not None:
        design_cols.append(pd.to_numeric(phenotype, errors="coerce").fillna(0.0).values)
    if not design_cols:
        design_cols = [np.ones(n_samps)]
    D = np.column_stack(design_cols)
    D = np.column_stack([np.ones(n_samps), D])
    if D.shape[1] >= n_samps:
        D = D[:, : max(1, n_samps - 1)]
    P_D = D @ np.linalg.pinv(D.T @ D) @ D.T
    R = X - (P_D @ X.T).T  # residual matrix (genes x samples)

    # iterative reweighted SVD (IRW-SVA style)
    for _ in range(3):
        U, S, Vt = np.linalg.svd(R, full_matrices=False)
        # reweight: scale rows by inverse residual std
        w = 1.0 / (R.std(axis=1) + 1e-9)
        R = (R * w[:, None]) - (P_D @ (R * w[:, None]).T).T
        U, S, Vt = np.linalg.svd(R, full_matrices=False)
    sv = Vt  # samples x min(n,p)
    if n_sv is None:
        # permutation-style heuristic: keep PCs whose singular value exceeds
        # the 95th percentile of randomized singular values (fast proxy)
        n_sv = min(max_n_sv, sv.shape[0])
        null_s = []
        for _ in range(5):
            Rp = R[:, rng.permutation(n_samps)]
            null_s.append(np.atleast_1d(np.linalg.svd(Rp, compute_uv=False)))
        null_95 = np.percentile(np.concatenate(null_s), 95)
        n_sv = max(1, int((S[:n_sv] > null_95).sum()))
    return pd.DataFrame(sv[:n_sv].T, index=expression.columns,
                        columns=[f"SV{i+1}" for i in range(n_sv)])


# ---------------------------------------------------------------------------
# PEER-inspired factor model
# ---------------------------------------------------------------------------
def peer_like_factors(
    expression: pd.DataFrame,
    covariates: Optional[pd.DataFrame] = None,
    n_factors: int = 15,
    n_iter: int = 100,
    seed: int = 42,
) -> pd.DataFrame:
    """PEER-style hidden-factor inference (computational proxy).

    Alternates least squares between hidden factors (samples x k) and their
    effects (k x genes) on residualized expression, with ARD-like shrinkage
    on factor precision — a deterministic stand-in for the full Bayesian PEER.
    """
    rng = np.random.default_rng(seed)
    X = expression.values.astype(float)
    X = np.nan_to_num(X, nan=np.nanmean(X, axis=1, keepdims=True))
    n_genes, n_samps = X.shape
    if covariates is not None:
        C = covariates.values.astype(float)
        C = np.column_stack([np.ones(n_samps), C])
        X = X - (np.linalg.pinv(C.T @ C) @ C.T @ X.T).T @ C.T
    k = min(n_factors, n_samps - 2, n_genes)
    W = rng.normal(0, 0.1, size=(n_samps, k))  # factors
    alpha = np.ones(k)
    for it in range(n_iter):
        # effects given factors
        V = np.linalg.pinv(W.T @ W + np.diag(alpha)) @ W.T @ X  # k x genes
        # factors given effects
        W = X @ V.T @ np.linalg.pinv(V @ V.T + 1e-3 * np.eye(k))
        # ARD-style update of precisions
        alpha = 1.0 / (np.mean(V**2, axis=1) + 1e-6)
        W = W * np.sqrt(alpha)[None, :]  # normalize scale
    return pd.DataFrame(W, index=expression.columns,
                        columns=[f"PEER{i+1}" for i in range(k)])


# ---------------------------------------------------------------------------
# Batch correction: ComBat (EB) + LMM
# ---------------------------------------------------------------------------
def combat_adjust(
    matrix: pd.DataFrame, batch_labels: pd.Series,
    covariates: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """ComBat-style empirical-Bayes batch correction (per-gene)."""
    batch_labels = batch_labels.fillna('NA')
    batches = list(dict.fromkeys(batch_labels.astype(str)))
    X = matrix.values.astype(float)
    X = np.where(np.isnan(X), np.nanmean(X, axis=1, keepdims=True), X)
    n_genes, n = X.shape
    design = pd.DataFrame({f"B_{b}": (batch_labels.astype(str) == b).astype(float) for b in batches})
    if covariates is not None:
        design = pd.concat([covariates.reset_index(drop=True), design.reset_index(drop=True)], axis=1)
    D = np.column_stack([np.ones(n), design.values])
    beta = np.linalg.pinv(D.T @ D) @ D.T @ X.T  # p x genes
    resid = X.T - D @ beta
    var_pooled = resid.var(axis=0) + 1e-9
    idx = {b: np.where(batch_labels.astype(str) == b)[0] for b in batches}
    Xc = X.T.copy()
    for b in batches:
        i = idx[b]
        if len(i) < 2:
            continue
        Db = np.column_stack([np.ones(len(i)), design.values[i]])
        betab = np.linalg.pinv(Db.T @ Db) @ Db.T @ Xc[i]
        rb = Xc[i] - Db @ betab
        # EB shrink batch variance toward pooled
        delta = rb.std(axis=0) + 1e-9
        shrink = var_pooled / (var_pooled + delta**2)
        Xc[i] = (Xc[i] - np.outer(np.ones(len(i)), betab[0])) * np.sqrt(shrink) + np.outer(np.ones(len(i)), beta[0])
    return pd.DataFrame(Xc.T, index=matrix.index, columns=matrix.columns)


def lmm_adjust(
    matrix: pd.DataFrame, batch_labels: pd.Series,
    random_slope: bool = False,
) -> pd.DataFrame:
    """Linear mixed-model batch adjustment (batch as random intercept).

    Estimates per-gene fixed (intercept) + random (batch) effects via best
    linear unbiased prediction (BLUP) and returns batch-adjusted values.
    """
    X = matrix.values.astype(float)  # genes x samples
    n_genes, n = X.shape
    b = batch_labels.astype("category").cat.codes
    n_b = b.max() + 1
    Z = np.eye(n_b)[b]  # sample x batch dummies
    Xadj = X.copy()
    for g in range(n_genes):
        y = X[g]
        # fixed intercept
        mu = y.mean()
        # random batch means
        batch_mean = np.array([y[b == k].mean() if (b == k).sum() else mu for k in range(n_b)])
        # shrinkage toward grand mean (BLUP-style)
        nk = np.array([(b == k).sum() for k in range(n_b)])
        shrink = nk / (nk + 1.0)
        blup = mu + (batch_mean - mu) * shrink
        Xadj[g] = y - (blup[b] - mu)
    return pd.DataFrame(Xadj, index=matrix.index, columns=matrix.columns)


# ---------------------------------------------------------------------------
# Ancestry-aware genotype QC
# ---------------------------------------------------------------------------
def genotype_qc(
    genotypes: pd.DataFrame,  # samples x variants (dosage 0/1/2)
    maf_min: float = 0.01,
    missing_max: float = 0.05,
    hwe_p_min: float = 1e-6,
    ld_prune_r2: float = 0.8,
    seed: int = 42,
) -> tuple[pd.DataFrame, dict]:
    """Filter variants (MAF, missingness, HWE), LD-light prune, return QC log."""
    G = genotypes.astype(float)
    n = G.shape[0]
    maf = (G.sum(axis=0) / (2 * n)).clip(0, 1)
    miss = G.isna().mean(axis=0)
    # HWE exact-test approximation (Wigginton et al. 2005 style via chi2)
    hwe_p = pd.Series(1.0, index=G.columns)
    for v in G.columns:
        a = G[v].fillna(G[v].mean())
        p_allele = (a / 2).mean()
        q = 1 - p_allele
        nAA = int(((a == 0) & ~G[v].isna()).sum())
        nAB = int(((a == 1) & ~G[v].isna()).sum())
        nBB = int(((a == 2) & ~G[v].isna()).sum())
        obs = np.array([nAA, nAB, nBB], dtype=float)
        exp = np.array([n * p_allele**2, 2 * n * p_allele * q, n * q**2])
        if exp.min() < 5:
            continue  # chi2 approximation invalid for rare variants -> keep
        chi2 = float(np.sum((obs - exp) ** 2 / exp))
        from scipy import stats

        hwe_p[v] = stats.chi2.sf(chi2, 1)
    keep = (maf >= maf_min) & (miss <= missing_max) & (hwe_p >= hwe_p_min)
    G = G.loc[:, keep]
    # LD-light pruning: greedy on correlation, keeps representative variant
    rng = np.random.default_rng(seed)
    corr = G.corr(method="pearson").abs()
    drop = set()
    for i in range(corr.shape[0]):
        if corr.index[i] in drop:
            continue
        for j in range(i + 1, corr.shape[1]):
            if corr.columns[j] in drop:
                continue
            if corr.iloc[i, j] > ld_prune_r2:
                drop.add(corr.columns[j])
    G = G.drop(columns=list(drop))
    log = {
        "variants_before": int(genotypes.shape[1]),
        "variants_after": int(G.shape[1]),
        "dropped_maf": int((~keep).sum()),
        "dropped_ld": len(drop),
        "n_samples": int(n),
    }
    return G, log


def ancestry_pca(
    genotypes: pd.DataFrame,
    n_components: int = 10,
    n_clusters: Optional[int] = None,
    seed: int = 42,
) -> dict:
    """PCA on genotype matrix → ancestry PCs + admixture-like cluster labels."""
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.impute import SimpleImputer

    X = SimpleImputer(strategy="mean").fit_transform(genotypes.values)
    pca = PCA(n_components=min(n_components, X.shape[0], X.shape[1]))
    scores = pca.fit_transform(X)
    pcs = pd.DataFrame(scores, index=genotypes.index,
                       columns=[f"PC{i+1}" for i in range(scores.shape[1])])
    n_clusters = n_clusters or 3
    km = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10).fit(pcs.iloc[:, : min(5, scores.shape[1])])
    labels = pd.Series(km.labels_, index=genotypes.index).map(lambda x: f"ANC{x+1}")
    return {
        "pcs": pcs,
        "cluster": labels,
        "variance_explained": pca.explained_variance_ratio_.tolist(),
        "n_clusters": n_clusters,
    }
