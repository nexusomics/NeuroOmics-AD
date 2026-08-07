"""Causal inference layer.

Implements:
  * NOTEARS (Zheng et al. 2018): continuous optimization for DAG structure
    learning of linear structural equation models, with L1 sparsity and the
    acyclicity constraint h(W)=tr(e^{W∘W})-d via augmented Lagrangian.
  * Double Machine Learning (Chernozhukov et al. 2018): cross-fitted,
    orthogonalized estimation of causal effects with Lasso nuisance models.
  * PC algorithm skeleton (Spirtes et al. 2000): constraint-based conditional
    independence testing with Fisher-z partial correlations.
"""
from __future__ import annotations

import logging
from itertools import combinations
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# NOTEARS — linear DAG learning
# ---------------------------------------------------------------------------
def _h_func(W: np.ndarray) -> float:
    """Acyclicity: h(W) = tr(exp(W∘W)) - d == 0 iff DAG."""
    from scipy.linalg import expm

    d = W.shape[0]
    return float(np.trace(expm(W * W)) - d)


def _h_grad(W: np.ndarray) -> np.ndarray:
    """Gradient of h: (exp(W∘W))^T ∘ (2W)."""
    from scipy.linalg import expm

    return expm(W * W).T * 2.0 * W


def _objective(W: np.ndarray, X: np.ndarray, lam: float, rho: float, alpha: float) -> float:
    d = X.shape[1]
    W = W.reshape(d, d)
    loss = 0.5 / X.shape[0] * np.sum((X - X @ W) ** 2)
    l1 = lam * np.sum(np.abs(W))
    h = _h_func(W)
    return float(loss + l1 + 0.5 * rho * h * h + alpha * h)


def _objective_grad(W: np.ndarray, X: np.ndarray, lam: float, rho: float, alpha: float) -> np.ndarray:
    d = X.shape[1]
    W = W.reshape(d, d)
    grad_loss = -1.0 / X.shape[0] * X.T @ (X - X @ W)
    grad_l1 = lam * np.sign(W)
    h = _h_func(W)
    grad_h = _h_grad(W)
    grad = grad_loss + grad_l1 + (rho * h + alpha) * grad_h
    return grad.ravel()


def notears_linear(
    X: pd.DataFrame,  # samples x variables
    lambda1: float = 0.05,
    max_iter: int = 30,
    h_tol: float = 1e-6,
    rho_max: float = 1e8,
    w_threshold: float = 0.3,
    seed: int = 42,
) -> dict:
    """Learn a DAG of linear SEMs via NOTEARS. Returns weighted adjacency W."""
    rng = np.random.default_rng(seed)
    d = X.shape[1]
    names = list(X.columns)
    Xn = X.values.astype(float)
    Xn = np.nan_to_num(Xn, nan=np.nanmean(Xn, axis=0, keepdims=True))
    Xn = (Xn - Xn.mean(axis=0)) / (Xn.std(axis=0) + 1e-9)
    W = rng.normal(0, 0.05, size=(d, d))
    np.fill_diagonal(W, 0.0)
    rho, alpha, h = 1e-2, 0.0, np.inf
    for _ in range(max_iter):
        res = minimize(
            _objective, W.ravel(), args=(Xn, lambda1, rho, alpha),
            method="L-BFGS-B", jac=_objective_grad,
            options={"maxiter": 200, "ftol": 1e-8},
        )
        W = res.x.reshape(d, d)
        np.fill_diagonal(W, 0.0)
        h = _h_func(W)
        if h > 0.25 * h_tol:
            alpha += rho * h
        rho = min(rho * 10, rho_max)
        if h <= h_tol:
            break
    W[abs(W) < w_threshold] = 0.0
    adj = pd.DataFrame(W, index=names, columns=names)
    edges = [(r, c) for r in names for c in names if abs(W[names.index(r), names.index(c)]) > 0]
    return {"adjacency": adj, "edges": edges, "h": float(h), "method": "NOTEARS (linear SEM)"}


# ---------------------------------------------------------------------------
# Double Machine Learning (partialling-out ATE)
# ---------------------------------------------------------------------------
def dml_ate(
    treatment: pd.Series,
    outcome: pd.Series,
    confounders: pd.DataFrame,
    n_folds: int = 5,
    seed: int = 42,
    ci_level: float = 0.95,
) -> dict:
    """Estimate average treatment effect via cross-fitted DML with Lasso.

    Orthogonal score ψ = (Y - g(X))·(T - m(X)) / Var(T-m); SE from the
    variance of the score (Neyman orthogonality).
    """
    from sklearn.linear_model import LassoCV
    from sklearn.model_selection import KFold

    rng = np.random.default_rng(seed)
    n = len(outcome)
    ok = treatment.notna() & outcome.notna() & ~confounders.isna().any(axis=1)
    treatment, outcome = treatment[ok], outcome[ok]
    confounders = confounders.loc[ok]
    n = len(outcome)
    T = treatment.values.astype(float)
    Y = outcome.values.astype(float)
    Xc = confounders.values.astype(float)
    Xc = np.nan_to_num(Xc, nan=0.0)
    # standardize
    T = (T - T.mean()) / (T.std() + 1e-9)
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=seed)
    scores = np.zeros(n)
    for tr_idx, va_idx in kf.split(Xc):
        g = LassoCV(cv=3, random_state=seed).fit(Xc[tr_idx], Y[tr_idx])
        m = LassoCV(cv=3, random_state=seed).fit(Xc[tr_idx], T[tr_idx])
        y_res = Y[va_idx] - g.predict(Xc[va_idx])
        t_res = T[va_idx] - m.predict(Xc[va_idx])
        scores[va_idx] = y_res * t_res / np.mean(t_res**2)  # normalized score
    ate = float(np.mean(scores))
    se = float(np.std(scores) / np.sqrt(n))
    from scipy import stats as st

    z = st.norm.ppf(1 - (1 - ci_level) / 2)
    return {
        "ate": ate, "se": se,
        "ci_low": ate - z * se, "ci_high": ate + z * se,
        "n": n, "method": "DML (partialling-out, Lasso nuisance)",
        "ci_level": ci_level,
    }


# ---------------------------------------------------------------------------
# PC algorithm skeleton (Fisher-z partial correlation)
# ---------------------------------------------------------------------------
def _partial_corr_pvalue(data: np.ndarray, i: int, j: int, cond: list[int], n: int) -> float:
    """Fisher-z test of partial correlation rho_{ij|cond} = 0."""
    cols = [i, j] + cond
    sub = np.nan_to_num(data[:, cols], nan=0.0, posinf=0.0, neginf=0.0)
    C = np.corrcoef(sub.T)
    C = np.nan_to_num(C, nan=0.0, posinf=0.0, neginf=0.0)
    C = np.linalg.pinv(C, rcond=1e-6)
    r = -C[0, 1] / np.sqrt(C[0, 0] * C[1, 1] + 1e-12)
    r = np.clip(r, -1 + 1e-9, 1 - 1e-9)
    k = len(cond)
    z = 0.5 * np.log((1 + r) / (1 - r))
    se = 1.0 / np.sqrt(n - k - 3)
    p = 2 * stats.norm.sf(abs(z) / se)
    return float(p)


def pc_skeleton(
    X: pd.DataFrame,
    alpha: float = 0.05,
    max_cond_size: int = 2,
) -> dict:
    """PC algorithm skeleton: undirected graph of conditional dependencies."""
    names = list(X.columns)
    d = len(names)
    n = X.shape[0]
    Xv = X.values.astype(float)
    Xv = np.nan_to_num(Xv, nan=np.nanmean(Xv, axis=0, keepdims=True))
    data = (Xv - Xv.mean(axis=0)) / (Xv.std(axis=0) + 1e-9)
    adj = {i: set(range(d)) - {i} for i in range(d)}
    # zero-order
    for i, j in combinations(range(d), 2):
        if _partial_corr_pvalue(data, i, j, [], n) > alpha:
            adj[i].discard(j)
            adj[j].discard(i)
    # increasing conditioning sets
    for k in range(1, max_cond_size + 1):
        for i in range(d):
            nbrs = list(adj[i])
            for j in list(nbrs):
                for cond in combinations([x for x in nbrs if x != j], k):
                    p = _partial_corr_pvalue(data, i, j, list(cond), n)
                    if p > alpha:
                        adj[i].discard(j)
                        adj[j].discard(i)
                        break
    edges = sorted({tuple(sorted((names[i], names[j]))) for i in range(d) for j in adj[i] if j > i})
    sepsets = {}
    return {"edges": edges, "adjacency": {names[i]: [names[j] for j in adj[i]] for i in range(d)},
            "sepsets": sepsets, "method": "PC skeleton (Fisher-z)", "alpha": alpha}
