"""Differential expression analysis.

Primary engine: **limma-style linear modelling with empirical-Bayes moderated
t-statistics** (Smyth 2004) implemented in Python, with optional voom-like
mean-variance weighting for count data. When Bioconductor's `limma`/`DESeq2`
are installed, the analysis is delegated to R through the rpy2 bridge for
maximum community reproducibility.

Output: per-gene table {gene, log2fc, ave_expr, t, pvalue, fdr, sig} plus a
summary of up/down regulated genes.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from app.r_integration.client import has_package, run_r_script, with_r_or_python

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core statistical machinery
# ---------------------------------------------------------------------------
def _design_matrix(metadata: pd.DataFrame, group_column: str, case: str, control: str, covariates: list[str]) -> tuple[np.ndarray, list[str]]:
    """Build a design matrix: intercept-free? Use treatment coding with control as baseline."""
    meta = metadata.copy()
    cols = ["(Intercept)"]
    X = np.ones((len(meta), 1))
    # group effect: case vs control
    if group_column not in meta.columns:
        raise ValueError(f"group column '{group_column}' not found in metadata")
    g = meta[group_column].astype(str)
    valid = g.isin([case, control])
    meta = meta[valid].copy()
    g = g[valid]
    X = X[valid]
    X = np.column_stack([X, (g == case).astype(float)])
    cols.append(f"group{case}vs{control}")
    for cov in covariates:
        if cov not in meta.columns:
            logger.warning("covariate '%s' not found; skipped", cov)
            continue
        vals = pd.to_numeric(meta[cov], errors="coerce").fillna(meta[cov].astype(str).astype("category").cat.codes)
        X = np.column_stack([X, vals.values])
        cols.append(cov)
    return X, cols, valid


def _empirical_bayes_moderated_t(X: np.ndarray, Y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Fit per-gene linear models and apply empirical-Bayes variance moderation.

    Returns (coefficients, moderated_t, pvalues, std_errors) for the LAST
    coefficient column (the case-vs-control effect), which callers should have
    placed in column 1.
    """
    n_genes, n_samples = Y.shape
    p = X.shape[1]
    # least-squares fits
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ Y  # p × genes
    resid = Y - X @ beta
    df_resid = n_samples - p
    sigma2 = (resid**2).sum(axis=0) / max(df_resid, 1)  # per-gene residual variance

    # prior: inverse-gamma fitted by moments on observed variances
    s2 = sigma2
    # sample moments of log(s2)
    with np.errstate(all="ignore"):
        log_s2 = np.log(np.maximum(s2, 1e-12))
    mean_log_s2 = log_s2.mean()
    var_log_s2 = log_s2.var()
    # prior df (d0) and prior variance (s0^2) via method-of-moments approximation
    trigamma_inv = 0.5 / (var_log_s2 + 1e-12) if var_log_s2 > 1e-12 else df_resid / 2
    d0 = max(2.0, min(2 * trigamma_inv, 1000.0))
    s0_2 = np.exp(mean_log_s2 - np.log(d0 / 2) + np.log((d0 / 2 + 1)) - np.log(d0 / 2))
    s0_2 = max(s0_2, 1e-12)

    # moderated variance: (d0*s0^2 + df_resid*s2) / (d0 + df_resid)
    d_post = d0 + df_resid
    s2_post = (d0 * s0_2 + df_resid * s2) / d_post
    se2 = np.diag(XtX_inv)[1] * s2_post
    coef = beta[1]
    t_stat = coef / np.sqrt(se2)
    pval = 2 * stats.t.sf(np.abs(t_stat), df=d_post)
    return coef, t_stat, pval, np.sqrt(se2)


def differential_expression_python(
    matrix: pd.DataFrame,
    metadata: pd.DataFrame,
    group_column: str = "group",
    case: str = "AD",
    control: str = "CN",
    covariates: list[str] | None = None,
    voom_like: bool = True,
) -> pd.DataFrame:
    """Python limma-style DE analysis. Returns annotated per-gene results."""
    meta = metadata.copy()
    meta.index = meta.index.astype(str)
    common = [c for c in matrix.columns if c in meta.index]
    if not common:
        raise ValueError("No samples overlap between expression matrix and metadata")
    matrix = matrix[common].astype(float)
    meta = meta.loc[common]
    X, _, valid = _design_matrix(meta, group_column, case, control, covariates or [])
    Y = matrix.values.T  # samples × genes
    if voom_like:
        # mean-variance weighting: lowly-expressed genes get downweighted (voom-inspired)
        means = Y.mean(axis=0)
        sds = Y.std(axis=0)
        ok = means > 0
        if ok.sum() > 3:
            log_m = np.log2(means[ok] + 0.5)
            log_s = np.log2(sds[ok] + 0.5)
            slope, intercept, *_ = np.polyfit(log_m, log_s, 1)
            pred_var = 2 ** (intercept + slope * np.log2(means + 0.5))
            w = 1.0 / np.maximum(pred_var, 1e-9)
            Y = Y * np.sqrt(w)[None, :]
    coef, t_stat, pval, _se = _empirical_bayes_moderated_t(X, Y)
    ave_expr = np.log2(matrix.values.mean(axis=1) + 1e-6)
    fdr = _bh_fdr(pval)
    res = pd.DataFrame(
        {
            "gene": matrix.index,
            "log2fc": coef,
            "ave_expr": ave_expr,
            "t": t_stat,
            "pvalue": pval,
            "fdr": fdr,
        }
    )
    res["sig"] = res["fdr"] < 0.05
    res["direction"] = np.where(res["log2fc"] > 0, "up", "down")
    return res.sort_values("pvalue")


def _bh_fdr(pvals: np.ndarray) -> np.ndarray:
    """Benjamini–Hochberg FDR."""
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    n = len(p)
    adj = ranked * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty_like(adj)
    out[order] = np.minimum(adj, 1.0)
    return out


def differential_expression_r(
    matrix: pd.DataFrame,
    metadata: pd.DataFrame,
    group_column: str = "group",
    case: str = "AD",
    control: str = "CN",
    covariates: list[str] | None = None,
    method: str = "limma",
) -> pd.DataFrame:
    """Delegate to R (limma voom or DESeq2) when available."""
    import rpy2.robjects as ro
    from rpy2.robjects import pandas2ri

    pandas2ri.activate()
    meta = metadata.copy()
    meta.index = meta.index.astype(str)
    common = [c for c in matrix.columns if c in meta.index]
    matrix = matrix[common].astype(float)
    meta = meta.loc[common]
    ro.globalenv["expr_mat"] = matrix
    ro.globalenv["meta_df"] = meta.reset_index().rename(columns={"index": "sample"})
    ro.globalenv["case_group"] = case
    ro.globalenv["control_group"] = control
    ro.globalenv["group_col"] = group_column
    ro.globalenv["covs"] = ro.StrVector(covariates or [])
    if method == "deseq2" and has_package("DESeq2"):
        script = _DESEQ2_SCRIPT
    else:
        script = _LIMMA_SCRIPT
    df = run_r_script(script)
    pandas2ri.deactivate()
    res = pandas2ri.rpy2py(df) if not isinstance(df, pd.DataFrame) else df
    res = res.rename(columns=str)
    res["sig"] = res["fdr"] < 0.05
    res["direction"] = np.where(res["log2fc"] > 0, "up", "down")
    return res.sort_values("pvalue")


_LIMMA_SCRIPT = r"""
suppressMessages({library(limma)})
samples <- meta_df[[group_col]]
design <- model.matrix(~ 0 + factor(samples, levels=c(control_group, case_group)))
colnames(design) <- c("control","case")
if (length(covs) > 0) {
  for (cv in covs) { design <- cbind(design, meta_df[[cv]]) }
}
fit <- lmFit(expr_mat, design)
contr <- makeContrasts(case - control, levels=design)
fit2 <- contrasts.fit(fit, contr)
fit2 <- eBayes(fit2)
top <- topTable(fit2, number=Inf, sort.by="none")
data.frame(gene=rownames(top), log2fc=top$logFC, ave_expr=top$AveExpr,
           t=top$t, pvalue=top$P.Value, fdr=top$adj.P.Val)
"""

_DESEQ2_SCRIPT = r"""
suppressMessages({library(DESeq2)})
meta <- meta_df
rownames(meta) <- meta$sample
counts <- round(expr_mat)
counts <- counts[, rownames(meta)]
dds <- DESeqDataSetFromMatrix(countData=counts, colData=meta,
                              design=as.formula(paste("~", paste(c(covs, group_col), collapse=" + "))))
dds$group <- relevel(factor(dds[[group_col]]), ref=control_group)
dds <- DESeq(dds, quiet=TRUE)
res <- results(dds, contrast=c(group_col, case_group, control_group))
data.frame(gene=rownames(res), log2fc=res$log2FoldChange,
           ave_expr=rowMeans(counts(dds, normalized=TRUE)),
           stat=res$stat, pvalue=res$pvalue, fdr=res$padj)
"""


def differential_expression(
    matrix: pd.DataFrame,
    metadata: pd.DataFrame,
    group_column: str = "group",
    case: str = "AD",
    control: str = "CN",
    covariates: list[str] | None = None,
    method: str = "auto",
    fdr_threshold: float = 0.05,
    log2fc_threshold: float = 1.0,
) -> dict:
    """Top-level DE entry point: R when requested/available, else Python."""
    py = lambda: differential_expression_python(matrix, metadata, group_column, case, control, covariates)  # noqa: E731

    def r():
        return differential_expression_r(matrix, metadata, group_column, case, control, covariates, method)

    if method == "python":
        res = py()
    elif method in ("auto", "deseq2", "limma") and has_package("limma" if method != "deseq2" else "DESeq2"):
        res = r()
    else:
        res = py()
    res = res.copy()
    res["sig"] = (res["fdr"] < fdr_threshold) & (res["log2fc"].abs() > log2fc_threshold)
    n_up = int(((res["sig"]) & (res["log2fc"] > 0)).sum())
    n_down = int(((res["sig"]) & (res["log2fc"] < 0)).sum())
    return {
        "table": res.reset_index(drop=True).to_dict(orient="records"),
        "summary": {
            "tested_genes": int(len(res)),
            "significant": int(res["sig"].sum()),
            "upregulated": n_up,
            "downregulated": n_down,
            "fdr_threshold": fdr_threshold,
            "log2fc_threshold": log2fc_threshold,
            "method": "r:" + method if (method != "python" and has_package("limma")) else "python:limma-style",
        },
    }
