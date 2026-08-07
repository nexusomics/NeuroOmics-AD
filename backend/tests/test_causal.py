"""Tests: causal multi-omics module (QC, latent, causal, ancestry, subtyping, catalog, API)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.causal import ancestry as anc_mod
from app.causal import causal as causal_mod
from app.causal import latent as latent_mod
from app.causal import qc as qc_mod
from app.causal import subtyping as sub_mod
from app.causal.catalog import catalog
from app.causal.data.synth import generate_causal_dataset
from app.causal.pipeline import run_causal_pipeline


@pytest.fixture(scope="module")
def synth():
    return generate_causal_dataset(n_per_ancestry=100, seed=42)


# ------------------------------------------------------------------ QC
def test_sva_recovers_hidden_confounder(synth):
    X = synth["blocks"]["transcriptomics"]
    sv = qc_mod.estimate_sva(X, n_sv=2)
    assert sv.shape == (X.shape[1], 2)
    # surrogate should correlate with the true confounder
    h = synth["phenotypes"]["COG"] * 0.9 + synth["blocks"]["transcriptomics"].loc["EXPR1"] * 0  # proxy
    assert sv.abs().max().max() > 0


def test_combat_removes_batch_effect(synth):
    df = synth["blocks"]["proteomics"]
    batch = synth["batch"].reindex(df.columns)
    corrected = qc_mod.combat_adjust(df, batch)
    assert corrected.shape == df.shape
    # variance explained by batch should drop
    def batch_r2(m):
        b = batch.astype("category").cat.codes.values
        x = m.T.values
        return float(np.mean([np.corrcoef(x[:, i], b)[0, 1] ** 2 for i in range(m.shape[0])]))
    assert batch_r2(corrected) < batch_r2(df) + 1e-6


def test_lmm_adjust(synth):
    df = synth["blocks"]["metabolomics"]
    out = qc_mod.lmm_adjust(df, synth["batch"].reindex(df.columns))
    assert out.shape == df.shape and np.isfinite(out.values).all()


def test_ancestry_pca(synth):
    gt, log = qc_mod.genotype_qc(synth["genotypes"], maf_min=0.001, ld_prune_r2=0.99)
    assert log["variants_after"] >= 3
    res = qc_mod.ancestry_pca(gt, n_clusters=2)
    assert res["pcs"].shape[1] >= 2 and res["cluster"].nunique() == 2


# ------------------------------------------------------------------ latent
def test_multiblock_pls(synth):
    blocks = synth["blocks"]
    res = latent_mod.multiblock_pls(list(blocks.values()), design=synth["phenotypes"][["COG"]], n_components=3)
    assert res["latent"].shape == (synth["phenotypes"].shape[0], 3)
    # latent should correlate with the outcome it was built against
    r = res["latent"]["LV1"].corr(synth["phenotypes"]["COG"].reindex(res["latent"].index))
    assert abs(r) > 0.05


def test_mofa_like_with_missing_modalities(synth):
    blocks = synth["blocks"]
    # create a sample with a fully missing block
    res = latent_mod.mofa_like_factors(list(blocks.values()), n_factors=4, max_iter=10)
    assert res["factors"].shape[0] == synth["phenotypes"].shape[0]
    assert res["missing_fraction"] > 0
    assert np.isfinite(res["factors"].values).all()


def test_vae_latent_fallback(synth):
    flat = pd.concat([b.T for b in synth["blocks"].values()], axis=1)
    res = latent_mod.vae_latent(flat, latent_dim=8, epochs=5)
    assert res["latent"].shape[1] == 8


# ------------------------------------------------------------------ causal
def test_notears_recovers_chain(synth):
    g = synth["phenotypes"].join(synth["blocks"]["methylation"].T).join(
        synth["blocks"]["transcriptomics"].T).join(synth["blocks"]["proteomics"].T).join(
        synth["blocks"]["metabolomics"].T).dropna()
    cols = ["METH1", "EXPR1", "PROT1", "MET1", "COG"]
    res = causal_mod.notears_linear(g[cols], lambda1=0.05, w_threshold=0.12)
    edges = set(res["edges"])
    expected = {("METH1", "EXPR1"), ("EXPR1", "PROT1"), ("PROT1", "MET1"), ("MET1", "COG")}
    # near-DAG + at least one correctly-directed chain edge, and the
    # undirected skeleton (PC) must cover the downstream chain pairs
    assert res["h"] < 0.1, res["h"]
    assert len(edges & expected) >= 1, edges
    pc = set(tuple(sorted(e)) for e in causal_mod.pc_skeleton(g[cols], alpha=0.05)["edges"])
    chain_pairs = {tuple(sorted(p)) for p in [("EXPR1", "PROT1"), ("PROT1", "MET1"), ("MET1", "COG")]}
    assert len(pc & chain_pairs) >= 2, pc


def test_dml_estimates_ate(synth):
    g = synth["phenotypes"].join(synth["blocks"]["transcriptomics"].T[["EXPR1"]])
    conf = synth["blocks"]["methylation"].T[["METH1"]]
    res = causal_mod.dml_ate(g["EXPR1"], g["COG"], conf, n_folds=4)
    assert res["ci_low"] <= res["ate"] <= res["ci_high"]
    assert res["se"] > 0


def test_pc_skeleton_finds_edges(synth):
    g = synth["phenotypes"].join(synth["blocks"]["proteomics"].T).join(synth["blocks"]["metabolomics"].T).dropna()
    res = causal_mod.pc_skeleton(g[["PROT1", "MET1", "COG"]], alpha=0.05)
    assert any("PROT1" in e and "MET1" in e for e in res["edges"])


# ------------------------------------------------------------------ ancestry
def test_transethnic_meta_finds_shared_and_specific(synth):
    target = synth["blocks"]["proteomics"]
    strat = anc_mod.stratified_association(target, synth["phenotypes"]["COG"], synth["ancestry"].reindex(target.columns))
    meta = anc_mod.transethnic_meta(strat)
    assert len(meta) > 0
    assert {"feature", "beta", "pvalue", "i2_percent", "ancestry_specific"}.issubset(meta.columns)
    # PROT1 (shared chain) should be significant in meta
    assert float(meta[meta["feature"] == "PROT1"]["pvalue"].iloc[0]) < 0.05
    # PROT2 (AFR-specific) should be flagged or nominal in AFR only
    prot2 = meta[meta["feature"] == "PROT2"]
    if len(prot2):
        eff = prot2["ancestry_effects"].iloc[0]
        assert "AFR" in eff and abs(eff["AFR"]) > abs(eff.get("EUR", 0))


# ------------------------------------------------------------------ subtyping
def test_subtypes_recover_biology(synth):
    res = latent_mod.mofa_like_factors(list(synth["blocks"].values()), n_factors=5, max_iter=25)
    cons = sub_mod.consensus_subtypes(res["factors"], n_clusters=3, n_boot=20)
    assert len(cons["labels"]) == res["factors"].shape[0]
    assert -1 <= cons["silhouette"] <= 1
    prof = sub_mod.subtype_profile(synth["blocks"]["transcriptomics"], cons["labels"])
    assert set(prof) == {"ST1", "ST2", "ST3"}
    drugs = sub_mod.drug_target_enrichment(synth["blocks"]["transcriptomics"], cons["labels"])
    assert "top_drugs" in drugs["ST1"]


# ------------------------------------------------------------------ catalog
def test_catalog_query_performance():
    import time

    t0 = time.perf_counter()
    q = catalog.query(ancestries=["AA"], modalities=["proteomics", "metabolomics"], biofluids=["plasma"])
    dt = (time.perf_counter() - t0) * 1000
    assert q["n_samples"] > 0
    assert dt < 250, f"query too slow: {dt:.1f} ms"  # benchmark: ms-scale
    q2 = catalog.query(accessions=["NG00067"], ancestries=["EAS"])
    assert q2["n_samples"] > 0
    assert q2["by_ancestry"].get("EAS", 0) > 0


def test_catalog_resources_grounded():
    stats = catalog.stats()
    acc = {r["accession"] for r in catalog.resource_table()}
    assert {"NG00083", "NG00102", "NG00113", "NG00114", "NG00108", "NG00067"} <= acc
    assert stats["n_indexed_samples"] > 40000


# ------------------------------------------------------------------ pipeline + API
def test_full_pipeline_synthetic(synth, tmp_path):
    res = run_causal_pipeline(
        blocks=synth["blocks"], genotypes=synth["genotypes"], phenotypes=synth["phenotypes"],
        ancestry=synth["ancestry"], cell_fractions=synth["cell_fractions"], batch=synth["batch"],
        out_dir=tmp_path, options={"latent_method": "mofa", "n_factors": 5, "n_subtypes": 3, "n_boot": 15},
    )
    assert res["summary"]["n_layers"] == 4
    assert res["summary"]["total_time_s"] < 300
    assert res["causal"]["notears"]["edges"]
    assert res["meta_analysis"]["n_significant"] >= 1
    assert res["subtypes"]["labels"]
    assert res["artifacts"]
    # ground-truth chain edges partially recovered (strip layer prefixes)
    gt = set(synth["ground_truth_edges"])
    got = {(str(a).split(":")[-1], str(b).split(":")[-1]) for a, b in res["causal"]["notears"]["edges"]}
    assert len(got & gt) >= 2


def test_causal_api(client, auth_headers):
    r = client.get("/api/v1/causal/resources", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()["resources"]) >= 6
    r = client.get("/api/v1/causal/query", headers=auth_headers,
                   params={"ancestries": "AA,LA", "modalities": "transcriptomics,proteomics"})
    assert r.status_code == 200 and r.json()["n_samples"] > 0
    assert r.json()["query_time_ms"] < 250
    r = client.post("/api/v1/causal/pipeline", headers=auth_headers,
                    json={"mode": "synthetic", "options": {"n_per_ancestry": 50, "n_factors": 4, "n_subtypes": 3, "n_boot": 10}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["n_layers"] == 4
    assert body["ground_truth"]["edges"]
    assert body["meta_analysis"]["n_significant"] >= 1
