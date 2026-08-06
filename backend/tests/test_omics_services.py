"""Tests: core statistical services (DE, enrichment, network, meta, deconvolution, preprocessing)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.deconvolution import deconvolute
from app.services.differential_expression import differential_expression
from app.services.enrichment import enrich
from app.services.meta_analysis import meta_analysis
from app.services.network import build_network, network_proximity, run_network_analysis
from app.services.preprocessing import combat_batch_correction, qc_report, run_preprocessing


@pytest.fixture()
def omics():
    from tests.conftest import make_synthetic_expression

    return make_synthetic_expression(seed=7)


def test_differential_expression_finds_signal(omics):
    df, meta = omics
    res = differential_expression(df, meta, case="AD", control="CN")
    table = pd.DataFrame(res["table"])
    assert res["summary"]["significant"] >= 5
    # known disease genes should be among top
    top_genes = set(table["gene"].head(15))
    assert top_genes & {"APP", "IL1B", "TYROBP"}
    # direction sanity: APP should be up
    app_row = table[table["gene"] == "APP"].iloc[0]
    assert app_row["log2fc"] > 0
    # FDR column present and within [0,1]
    assert table["fdr"].between(0, 1).all()


def test_bh_fdr_ordering(omics):
    df, meta = omics
    res = differential_expression(df, meta, case="AD", control="CN")
    table = pd.DataFrame(res["table"])
    assert (table["fdr"].diff().dropna() >= -1e-9).all() or len(table) < 2  # monotone non-decreasing


def test_enrichment_curated(omics):
    df, meta = omics
    res = differential_expression(df, meta, case="AD", control="CN")
    sig = [r["gene"] for r in res["table"] if r["sig"]]
    known = [g for g in sig if g in {"APP", "BACE1", "IL1B", "TNF", "IL6", "TYROBP", "TREM2", "APOE", "HMOX1",
                                     "MTOR", "BECN1", "GFAP", "CSF1R", "NFE2L2", "MAPT", "GSK3B", "CLU"}]
    enr = enrich(known, databases=None)
    assert enr["summary"]["source"].startswith("built-in")
    assert any("Neuroinflammation" in t["pathway"] for t in enr["table"])


def test_network_hubs_and_modules(omics):
    df, meta = omics
    res = differential_expression(df, meta, case="AD", control="CN")
    sig = [r["gene"] for r in res["table"] if r["sig"]][:30]
    net = run_network_analysis(sig)
    assert net["summary"]["n_nodes"] > 0
    assert net["summary"]["n_modules"] >= 1
    assert len(net["hub_genes"]) > 0


def test_network_proximity_sane():
    G = build_network(["APP", "BACE1", "PSEN1", "MAPT", "GSK3B"], confidence_threshold=0.4)
    z_near = network_proximity(G, {"APP", "BACE1"}, {"PSEN1", "NCSTN"})
    z_far = network_proximity(G, {"APP"}, {"NO_SUCH_GENE", "ALSO_MISSING"})
    assert np.isfinite(z_near)
    assert z_far == 2.0  # disconnected


def test_meta_analysis(omics):
    df, meta = omics
    df2 = df.copy()
    df2.loc["APP", [c for c in df2.columns if c.startswith("AD")]] *= 2.0
    res = meta_analysis([df, df2], [meta.copy(), meta.copy()], case="AD", control="CN")
    assert res["summary"]["cohorts"] == 2
    assert res["summary"]["significant"] > 0
    assert "i2_percent" in pd.DataFrame(res["table"]).columns


def test_meta_analysis_requires_two(omics):
    df, meta = omics
    with pytest.raises(ValueError):
        meta_analysis([df], [meta])


def test_deconvolution_runs(omics):
    df, _ = omics
    res = deconvolute(df)
    assert res["fractions"].shape[1] >= 5
    # fractions sum to ~1 per sample
    assert np.allclose(res["fractions"].sum(axis=1), 1.0, atol=0.05)


def test_preprocessing_pipeline(omics):
    df, meta = omics
    out = run_preprocessing(df, meta, normalize_method="quantile", batch_correct=True, batch_column="batch")
    assert out["report"]["steps"]
    assert out["matrix"].shape[1] > 10
    assert out["report"]["qc"]["n_samples"] == out["matrix"].shape[1]


def test_combat_batch_correction(omics):
    df, meta = omics
    corrected = combat_batch_correction(df, meta["batch"])
    assert corrected.shape == df.shape
    assert np.isfinite(corrected.values).all()


def test_qc_report(omics):
    df, meta = omics
    qc = qc_report(df, meta["batch"])
    assert qc["n_samples"] == df.shape[1]
    assert -1 <= qc["min_sample_correlation"] <= 1
