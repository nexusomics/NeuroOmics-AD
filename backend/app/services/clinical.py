"""Clinical data analysis: survival analysis, subgroup comparison, risk modelling.

  * Kaplan–Meier survival curves & log-rank tests,
  * Cox proportional hazards regression (via statsmodels),
  * demographic / biomarker subgroup comparisons (t-test / chi²),
  * patient stratification helpers (k-means on biomarker panel).
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


def kaplan_meier(time: np.ndarray, event: np.ndarray, groups: np.ndarray) -> dict:
    """KM survival estimates per group + log-rank p-value."""
    groups = np.asarray(groups).astype(str)
    out = {}
    for g in np.unique(groups):
        idx = groups == g
        t = np.asarray(time)[idx].astype(float)
        e = np.asarray(event)[idx].astype(int)
        order = np.argsort(t)
        t, e = t[order], e[order]
        n = len(t)
        survival = 1.0
        times, surv, at_risk, events = [0.0], [1.0], [n], [0]
        for i in range(n):
            at_risk.append(n - i)
            events.append(int(e[i]))
            if e[i]:
                survival *= (n - i - 1) / max(n - i, 1)
            times.append(float(t[i]))
            surv.append(survival)
        out[g] = {"time": times, "survival": surv, "at_risk": at_risk, "events": events, "n": n}
    logrank_p = _logrank_test(time, event, groups)
    return {"curves": out, "logrank_pvalue": float(logrank_p), "n_groups": len(out)}


def _logrank_test(time: np.ndarray, event: np.ndarray, groups: np.ndarray) -> float:
    groups = np.asarray(groups).astype(str)
    labels = np.unique(groups)
    if len(labels) < 2:
        return 1.0
    t = np.asarray(time).astype(float)
    e = np.asarray(event).astype(int)
    order = np.argsort(t)
    t, e, g = t[order], e[order], groups[order]
    obs = {lab: 0 for lab in labels}
    exp_var = {lab: [0.0, 0.0] for lab in labels}  # [E, V]
    for i in range(len(t)):
        if not e[i]:
            continue
        at_risk = t[i:] <= t[i] + 1e-12 if False else None
        risk_set = t >= t[i] - 1e-12
        n_risk = int(risk_set.sum())
        if n_risk <= 1:
            break
        d_total = int((e[risk_set]).sum())
        for lab in labels:
            n_g = int((g[risk_set] == lab).sum())
            d_g = int((e[risk_set] & (g == lab)).sum())
            obs[lab] += d_g
            exp = n_g * d_total / n_risk
            exp_var[lab][0] += exp
            exp_var[lab][1] += (n_g * (n_risk - n_g) * d_total * (n_risk - d_total)) / (n_risk**2 * (n_risk - 1)) if n_risk > 1 else 0
    # multi-group log-rank statistic
    chi2 = 0.0
    for lab in labels:
        o, (E, V) = obs[lab], exp_var[lab]
        if V > 0:
            chi2 += (o - E) ** 2 / V
    df = len(labels) - 1
    return float(stats.chi2.sf(chi2, df))


def cox_proportional_hazards(df: pd.DataFrame, time_col: str, event_col: str, covariates: list[str]) -> dict:
    """Cox PH model via statsmodels; returns coefficients, HRs, p-values."""
    import statsmodels.duration.hazard_regression as hr

    data = df[[time_col, event_col] + covariates].dropna().copy()
    model = hr.PHReg(data[time_col], data[covariates], status=data[event_col])
    result = model.fit()
    params = result.params
    cov = result.cov_params()
    ses = np.sqrt(np.diag(cov))
    pvals = 2 * stats.norm.sf(np.abs(params / ses))
    out = []
    for name in params.index:
        out.append({
            "covariate": name,
            "coef": float(params[name]),
            "hazard_ratio": float(np.exp(params[name])),
            "se": float(ses[params.index.get_loc(name)]),
            "pvalue": float(pvals[params.index.get_loc(name)]),
        })
    return {"results": sorted(out, key=lambda r: r["pvalue"]), "n_subjects": int(len(data)), "n_events": int(data[event_col].sum())}


def subgroup_compare(df: pd.DataFrame, group_col: str, value_col: str, groups: list[str] | None = None) -> dict:
    """Two-group comparison of a continuous biomarker (Welch t-test + effect size)."""
    g = df[group_col].astype(str)
    a, b = groups or sorted(g.unique())[:2]
    va = df.loc[g == a, value_col].dropna().values
    vb = df.loc[g == b, value_col].dropna().values
    t, p = stats.ttest_ind(va, vb, equal_var=False)
    d = (va.mean() - vb.mean()) / np.sqrt((va.var(ddof=1) + vb.var(ddof=1)) / 2 + 1e-12)
    return {
        "group_a": a, "group_b": b,
        "mean_a": float(va.mean()), "mean_b": float(vb.mean()),
        "n_a": int(len(va)), "n_b": int(len(vb)),
        "t_statistic": float(t), "pvalue": float(p),
        "cohens_d": float(d),
    }


def stratify_patients(features: pd.DataFrame, n_clusters: int = 4, seed: int = 42) -> dict:
    """Unsupervised patient stratification (standardized k-means)."""
    X = StandardScaler().fit_transform(features.fillna(features.median()))
    km = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
    labels = km.fit_predict(X)
    centers = pd.DataFrame(km.cluster_centers_, columns=features.columns)
    sizes = {f"subtype_{i+1}": int((labels == i).sum()) for i in range(n_clusters)}
    return {
        "labels": pd.Series(labels, index=features.index).to_dict(),
        "cluster_centers": centers,
        "subtype_sizes": sizes,
        "n_clusters": n_clusters,
        "inertia": float(km.inertia_),
    }
