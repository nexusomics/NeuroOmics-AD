"""Multi-omics subtype discovery with therapeutic & progression enrichment.

Consensus k-means over latent factors → stable subtypes; annotate each
subtype by differentially-abundant features, pathway enrichment (reuses the
core enrichment module), drug-target enrichment (reuses the drug knowledge
base), and association with clinical progression when available.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)


def consensus_subtypes(
    latent: pd.DataFrame,  # samples x factors
    n_clusters: int = 3,
    n_boot: int = 50,
    seed: int = 42,
) -> dict:
    """Consensus clustering: k-means over bootstrap samples → co-assignment."""
    rng = np.random.default_rng(seed)
    n = latent.shape[0]
    samples = latent.index
    X = latent.values
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-9)
    consensus = np.zeros((n, n))
    for b in range(n_boot):
        boot_idx = rng.integers(0, n, size=n)
        km = KMeans(n_clusters=n_clusters, random_state=seed + b, n_init=5).fit(X[boot_idx])
        lab = km.predict(X)
        for i in range(n):
            for j in range(i + 1, n):
                if lab[i] == lab[j]:
                    consensus[i, j] += 1
                    consensus[j, i] += 1
    consensus /= n_boot
    # final partition from consensus matrix (hierarchical on 1-consensus)
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    np.fill_diagonal(consensus, 0.0)
    dist_mat = 1 - consensus
    np.fill_diagonal(dist_mat, 0.0)
    dist = squareform(dist_mat)
    Z = linkage(dist, method="average")
    labels = fcluster(Z, t=n_clusters, criterion="maxclust") - 1
    labels = pd.Series(labels, index=samples).map(lambda x: f"ST{x+1}")
    # silhouette
    from sklearn.metrics import silhouette_score

    sil = float(silhouette_score(X, labels.astype("category").cat.codes, sample_size=min(n, 500)))
    return {"labels": labels, "consensus": pd.DataFrame(consensus, index=samples, columns=samples),
            "silhouette": sil, "n_clusters": n_clusters}


def subtype_profile(
    matrix: pd.DataFrame,  # features x samples
    labels: pd.Series,
    n_top: int = 25,
) -> dict:
    """Per-subtype differential features (t-test vs rest) + sizes."""
    out = {}
    for st in labels.astype(str).unique():
        in_st = labels.astype(str) == st
        rows = []
        for f in matrix.index:
            a = matrix.loc[f, in_st].values.astype(float)
            b = matrix.loc[f, ~in_st].values.astype(float)
            if len(a) < 3 or len(b) < 3 or a.std() == 0 and b.std() == 0:
                continue
            t, p = stats.ttest_ind(a, b, equal_var=False)
            fc = a.mean() - b.mean()
            rows.append((f, float(fc), float(p), float(t)))
        df = pd.DataFrame(rows, columns=["feature", "delta", "pvalue", "t"]).sort_values("pvalue")
        df["fdr"] = _fdr(df["pvalue"].values)
        out[st] = {"n": int(in_st.sum()), "top_features": df.head(n_top).to_dict(orient="records")}
    return out


def subtype_enrichment(
    matrix: pd.DataFrame,
    labels: pd.Series,
    databases: Optional[list[str]] = None,
) -> dict:
    """Pathway enrichment per subtype using the core enrichment service."""
    from app.services.enrichment import enrich

    res = {}
    for st in labels.astype(str).unique():
        in_st = labels.astype(str) == st
        a = matrix.loc[:, in_st].mean(axis=1)
        b = matrix.loc[:, ~in_st].mean(axis=1)
        fc = a - b
        p = _fdr(_t_pvalues(matrix, in_st))
        top = fc[fc > 0].sort_values(ascending=False).head(60).index.tolist()
        enr = enrich(top, databases=databases, fdr_threshold=0.25)
        res[st] = {"top_gene_sets": enr["table"][:8], "summary": enr["summary"]}
    return res


def _t_pvalues(matrix: pd.DataFrame, mask: pd.Series) -> np.ndarray:
    p = []
    for f in matrix.index:
        a = matrix.loc[f, mask].values.astype(float)
        b = matrix.loc[f, ~mask].values.astype(float)
        try:
            p.append(stats.ttest_ind(a, b, equal_var=False).pvalue)
        except ValueError:
            p.append(1.0)
    return np.array(p)


def drug_target_enrichment(
    matrix: pd.DataFrame, labels: pd.Series,
    top_n: int = 60,
) -> dict:
    """Per-subtype drug-target enrichment vs the curated AD drug knowledge base."""
    from app.drugs.knowledge import all_drugs

    drugs = all_drugs()
    res = {}
    for st in labels.astype(str).unique():
        in_st = labels.astype(str) == st
        fc = matrix.loc[:, in_st].mean(axis=1) - matrix.loc[:, ~in_st].mean(axis=1)
        up = set(fc.nlargest(top_n).index) | set(fc.nsmallest(top_n).index)
        hits = []
        for key, d in drugs.items():
            t = set(d.get("targets", []))
            ov = t & up
            if ov:
                hits.append({"drug": d["name"], "overlap": sorted(ov), "mechanism": d.get("mechanism", ""),
                             "fda_status": d.get("fda_status", "")})
        hits.sort(key=lambda h: -len(h["overlap"]))
        res[st] = {"n_drugs_with_targets": len(hits), "top_drugs": hits[:10]}
    return res


def subtype_outcome_assoc(
    labels: pd.Series,
    outcome: pd.Series,
) -> dict:
    """ANOVA of subtype on a continuous outcome (e.g., rate of decline)."""
    groups = [outcome.reindex(labels.index)[labels.astype(str) == st].dropna().values for st in labels.astype(str).unique()]
    groups = [g for g in groups if len(g) >= 3]
    if len(groups) < 2:
        return {"available": False}
    f, p = stats.f_oneway(*groups)
    means = {st: float(np.mean(outcome.reindex(labels.index)[labels.astype(str) == st])) for st in labels.astype(str).unique()}
    return {"available": True, "f": float(f), "pvalue": float(p), "means": means}


def _fdr(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    n = len(p)
    adj = p[order] * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty_like(adj)
    out[order] = np.minimum(adj, 1.0)
    return out
