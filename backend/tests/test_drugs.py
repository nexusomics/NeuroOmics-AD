"""Tests: drug repurposing pipeline, scoring, ranking, BBB/ADMET."""
from __future__ import annotations

import pytest

from app.drugs.bbb_admet import admet_score, bbb_score
from app.drugs.knowledge import all_drugs, get_drug, search_drugs
from app.drugs.pipeline import run_drug_pipeline, suggest_combinations
from app.drugs.ranking import build_sankey, rank_candidates
from app.drugs.scoring import score_bbb, score_clinical, score_drug, score_network_proximity, score_pathway_reversal, score_target_overlap
from app.services.network import build_network


DISEASE_GENES = ["APP", "BACE1", "IL1B", "TNF", "IL6", "TREM2", "TYROBP", "APOE", "MAPT", "GSK3B"]


def test_knowledge_base():
    drugs = all_drugs()
    assert len(drugs) >= 50
    donepezil = get_drug("donepezil")
    assert donepezil and "ACHE" in donepezil["targets"]
    assert search_drugs("metformin")
    assert "APOE" in __import__("app.drugs.knowledge", fromlist=["CURATED_AD_RISK_GENES"]).CURATED_AD_RISK_GENES


def test_bbb_admet_scoring():
    rec = get_drug("memantine")
    bbb = bbb_score(rec)
    assert 0 <= bbb["score"] <= 1
    assert bbb["bbb_positive"] is True  # memantine is CNS-penetrant
    admet = admet_score(rec)
    assert 0 <= admet["score"] <= 1
    # biologics (antibodies) score low on BBB
    assert bbb_score(get_drug("aducanumab"))["score"] < 0.2


def test_scoring_criteria():
    G = build_network(DISEASE_GENES)
    rec = get_drug("metformin")
    scores = score_drug(rec, set(DISEASE_GENES), {g: 1 for g in DISEASE_GENES}, G)
    for k in ("network", "pathway_reversal", "target_overlap", "bbb", "admet", "clinical"):
        assert 0 <= scores[k] <= 1, k
    # direct target overlap
    assert score_target_overlap({"MTOR", "APP"}, ["MTOR"]) > 0
    # reversal: drug downregulates a disease-upregulated gene
    assert score_pathway_reversal({"IL1B": 1}, {"IL1B": -1}) == 1.0
    assert score_pathway_reversal({"IL1B": 1}, {"IL1B": 1}) == 0.0
    # clinical
    assert score_clinical(get_drug("donepezil")) > score_clinical(get_drug("sulforaphane"))


def test_pipeline_ranks_sensibly():
    res = run_drug_pipeline(DISEASE_GENES, max_candidates=10)
    candidates = res["candidates"]
    assert len(candidates) >= 5
    # composite scores in [0,1], ranks sequential
    for i, c in enumerate(candidates, start=1):
        assert 0 <= c["composite_score"] <= 1
        assert c["rank"] == i
    # deterministic order
    res2 = run_drug_pipeline(DISEASE_GENES, max_candidates=10)
    assert [c["drug_name"] for c in res["candidates"]] == [c["drug_name"] for c in res2["candidates"]]
    # sankey present
    assert res["sankey"]["nodes"]
    # combination suggestions
    combos = suggest_combinations(candidates, n_pairs=3)
    assert len(combos) <= 3
    for c in combos:
        assert c["drug_a"] != c["drug_b"]
        assert "rationale" in c


def test_pipeline_with_direction():
    direction = {"APP": 1, "BACE1": 1, "IL1B": 1, "TNF": 1, "MAPT": 1, "GSK3B": 1}
    res = run_drug_pipeline(DISEASE_GENES, direction=direction, max_candidates=6)
    assert res["candidates"]


def test_ranking_weights_and_bbb_filter():
    G = build_network(DISEASE_GENES)
    scored = [score_drug(get_drug(k), set(DISEASE_GENES), None, G) | {"drug_name": get_drug(k)["name"]}
              for k in ("donepezil", "memantine", "metformin", "minocycline", "aducanumab")]
    # build proper scored dicts
    scored = []
    for key in ("donepezil", "memantine", "metformin", "minocycline", "aducanumab", "sildenafil"):
        rec = get_drug(key)
        s = score_drug(rec, set(DISEASE_GENES), {g: 1 for g in DISEASE_GENES}, G)
        scored.append({**rec, "drug_name": rec["name"], "scores": s, "scores_normalized": {k: 0.0 for k in s}})
    ranked = rank_candidates(scored, max_candidates=10, require_bbb_positive=True)
    names = [c["drug_name"] for c in ranked["candidates"]]
    assert "Aducanumab" not in names  # low BBB filtered
    assert ranked["n_candidates_evaluated"] == 5  # aducanumab removed by BBB filter


def test_sankey_structure():
    candidates = [{"drug_name": "A", "targets": ["X", "Y"], "composite_score": 0.8},
                  {"drug_name": "B", "targets": ["Y", "Z"], "composite_score": 0.6}]
    sk = build_sankey(candidates)
    assert "Disease module" in sk["nodes"]
    assert sk["links"]
