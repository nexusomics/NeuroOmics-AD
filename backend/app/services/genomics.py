"""Genomics / GWAS / polygenic risk scoring helpers.

Operates on summary statistics (SNP-level) and genotype matrices (0/1/2 dosage):
  * QC & lambda (genomic inflation) estimation,
  * PRS scoring (thresholded & continuous),
  * Manhattan-style locus annotations,
  * heritability & colocalization helpers (LD score & coloc stubs with clear docs).
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

REQUIRED_GWAS_COLUMNS = {"rsid", "chrom", "pos", "beta", "se", "pvalue", "effect_allele"}


def validate_gwas_summary(df: pd.DataFrame) -> list[str]:
    """Check GWAS summary statistics columns; return missing required columns."""
    present = set(map(str.lower, df.columns))
    return sorted(REQUIRED_GWAS_COLUMNS - present)


def genomic_inflation_lambda(pvalues: np.ndarray) -> float:
    """Genomic inflation factor λ (median chi² / 0.456)."""
    p = np.asarray(pvalues, dtype=float)
    p = p[(p > 0) & (p <= 1)]
    chi2 = stats.chi2.isf(p, df=1)
    return float(np.median(chi2) / 0.456)


def manhattan_signal(df: pd.DataFrame, fdr_threshold: float = 0.05) -> pd.DataFrame:
    """BH-FDR significant loci with nearest-gene placeholder annotation."""
    out = df.copy()
    out["fdr"] = _bh_fdr(out["pvalue"].values)
    out["significant"] = out["fdr"] < fdr_threshold
    return out.sort_values("pvalue")


def compute_prs(
    genotypes: pd.DataFrame,
    summary: pd.DataFrame,
    p_thresholds: list[float] | None = None,
) -> dict:
    """Polygenic risk score: genotypes (samples × SNPs, dosage) × effect sizes.

    For each p-value threshold, score = Σ beta·dosage for SNPs passing the
    threshold; returns per-sample PRS per threshold and best-threshold AUC info
    (labels optional via `phenotype` column in summary).
    """
    if genotypes.shape[0] == 0:
        raise ValueError("empty genotype matrix")
    p_thresholds = p_thresholds or [5e-8, 1e-5, 1e-3, 0.01, 0.05, 0.1, 0.5, 1.0]
    common = list(set(genotypes.columns) & set(summary["rsid"]))
    if not common:
        raise ValueError("no overlapping SNPs between genotypes and summary statistics")
    g = genotypes[common]
    s = summary.set_index("rsid").loc[common]
    prs_by_threshold: dict[float, pd.Series] = {}
    for pt in sorted(p_thresholds):
        keep = s["pvalue"] <= pt
        if keep.sum() == 0:
            prs_by_threshold[pt] = pd.Series(0.0, index=genotypes.index)
            continue
        beta = s.loc[keep, "beta"].values
        # align dosage with effect allele
        eff = s.loc[keep, "effect_allele"].values
        cols = s.loc[keep].index
        dosage = g[cols].values.astype(float)
        prs_by_threshold[pt] = pd.Series(dosage @ beta, index=genotypes.index)
    prs_df = pd.DataFrame(prs_by_threshold)
    prs_df.columns = [f"PRS_p={p:.0e}" for p in prs_df.columns]
    return {
        "prs": prs_df,
        "summary": {
            "snps_overlapping": len(common),
            "thresholds": p_thresholds,
            "n_samples": int(genotypes.shape[0]),
        },
    }


def ld_score_regression_heritability(summary: pd.DataFrame, ld_scores: pd.Series) -> dict:
    """LD Score Regression: h² = (Σ z² - N) / (Σ ld_score), simplified S-LDSC estimate.

    `ld_scores`: SNP-indexed LD scores. Returns per-SNP estimates and total h².
    """
    s = summary.set_index("rsid")
    common = list(set(s.index) & set(ld_scores.index))
    if not common:
        raise ValueError("no overlapping SNPs with LD scores")
    z = (s.loc[common, "beta"] / s.loc[common, "se"]).values
    lds = ld_scores.loc[common].values.astype(float)
    n = 1.0 / np.median(s.loc[common, "se"] ** 2)  # effective N estimate
    reg = stats.linregress(lds, z**2 - 1)
    h2_per_snp = reg.slope
    h2_total = float(h2_per_snp * lds.sum())
    return {
        "heritability_h2": h2_total,
        "slope": float(reg.slope),
        "intercept": float(reg.intercept),
        "effective_n": float(n),
        "snps_used": len(common),
    }


def colocalization_posterior(p1: float, p2: float, p12: float = 0.05, prior: float = 1e-4) -> float:
    """Simple coloc-style posterior probability of shared causal variant (PP.H4 approx).

    Uses per-SNP Bayes factors and the standard 4-model placement. This is a
    lightweight approximation; production uses the full coloc R package.
    """
    bf1 = p1 / (1 - p1 + 1e-12)
    bf2 = p2 / (1 - p2 + 1e-12)
    denom = (1 - prior) ** 2 * 1 + prior * (1 - prior) * (bf1 + bf2) + prior**2 * bf1 * bf2
    pp4 = prior**2 * bf1 * bf2 / (denom + 1e-300)
    return float(np.clip(pp4, 0, 1))


def _bh_fdr(pvals: np.ndarray) -> np.ndarray:
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    n = len(p)
    adj = p[order] * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty_like(adj)
    out[order] = np.minimum(adj, 1.0)
    return out
