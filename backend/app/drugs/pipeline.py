"""Drug repurposing pipeline orchestrator.

Input: prioritized disease genes (optionally with direction).
Steps: evidence assembly → six-criterion scoring → weighted ranking → output.
"""
from __future__ import annotations

import logging
from typing import Optional

import networkx as nx

from app.drugs.knowledge import CURATED_AD_RISK_GENES, all_drugs, drug_targets_graph
from app.drugs.ranking import CRITERIA, DEFAULT_WEIGHTS, rank_candidates
from app.drugs.scoring import score_drug
from app.drugs.sources import fetch_sources
from app.services.network import build_network

logger = logging.getLogger(__name__)


def run_drug_pipeline(
    gene_list: list[str],
    direction: Optional[dict[str, int]] = None,
    weights: Optional[dict[str, float]] = None,
    max_candidates: int = 50,
    require_bbb_positive: bool = False,
    min_clinical_phase: str = "preclinical",
    sources: Optional[list[str]] = None,
) -> dict:
    """Execute the full repurposing pipeline."""
    disease_genes = {g.upper() for g in gene_list} or set(CURATED_AD_RISK_GENES)
    if direction is None:
        direction = {g: 1 for g in disease_genes}

    # PPI network containing the disease module + expanders
    G = build_network(list(disease_genes), confidence_threshold=0.4, max_interactors=60)

    drugs = list(all_drugs().values())
    phase_rank = {"preclinical": 0, "phase1": 1, "phase2": 2, "phase3": 3, "approved": 4}
    min_rank = phase_rank.get(min_clinical_phase, 0)

    # live-source evidence (best-effort, offline-safe)
    extra_evidence = fetch_sources(list(disease_genes), drugs, sources)

    scored = []
    for rec in drugs:
        if phase_rank.get(rec.get("clinical_phase", "preclinical"), 0) < min_rank:
            continue
        scores = score_drug(rec, disease_genes, direction, G)
        rec_out = dict(rec)
        rec_out.update({
            "drug_name": rec["name"],
            "disease_genes": sorted(disease_genes),
            "scores": scores,
            "scores_normalized": {c: 0.0 for c in CRITERIA},
            "evidence_sources": ["curated"] + list({e.get("source") for e in extra_evidence if e.get("drug", "").lower() == rec["name"].lower()}),
        })
        scored.append(rec_out)

    ranked = rank_candidates(scored, weights, max_candidates, require_bbb_positive)
    # attach a simple drug-combination suggestion using top complementary mechanisms
    ranked["combinations"] = suggest_combinations(ranked["candidates"][:15])
    ranked["inputs"] = {
        "n_disease_genes": len(disease_genes),
        "disease_genes": sorted(disease_genes)[:50],
        "n_drugs_screened": len(scored),
        "live_sources_used": bool(extra_evidence),
    }
    return ranked


def suggest_combinations(top_candidates: list[dict], n_pairs: int = 5) -> list[dict]:
    """Suggest mechanism-complementary drug pairs (different target categories)."""
    categories: dict[str, list[dict]] = {}
    for c in top_candidates:
        cat = _mechanism_category(c.get("mechanism", ""))
        categories.setdefault(cat, []).append(c)
    cats = list(categories)
    pairs = []
    for i in range(len(cats)):
        for j in range(i + 1, len(cats)):
            for a in categories[cats[i]][:3]:
                for b in categories[cats[j]][:3]:
                    if a["drug_name"] == b["drug_name"]:
                        continue
                    pairs.append({
                        "drug_a": a["drug_name"],
                        "drug_b": b["drug_name"],
                        "rationale": f"{cats[i].capitalize()} + {cats[j].capitalize()} complementary mechanisms "
                                     f"(composite {a['composite_score']:.2f} & {b['composite_score']:.2f})",
                        "combined_score": round((a["composite_score"] + b["composite_score"]) / 2, 4),
                    })
    pairs.sort(key=lambda p: -p["combined_score"])
    return pairs[:n_pairs]


def _mechanism_category(mechanism: str) -> str:
    m = mechanism.lower()
    if any(k in m for k in ["amyloid", "bace", "gamma-secretase", "antibody"]):
        return "amyloid"
    if any(k in m for k in ["tau", "gsk", "kinase", "aggregation"]):
        return "tau/kinase"
    if any(k in m for k in ["cholinesterase", "acetylcholin", "nmda", "glutamate", "cholinergic"]):
        return "neurotransmitter"
    if any(k in m for k in ["inflamm", "immune", "jak", "interleukin", "tnf", "microglial", "cox", "nsaid"]):
        return "neuroinflammation"
    if any(k in m for k in ["mtor", "autophagy", "ampk", "insulin", "glp-1", "metabolism", "ppar", "diabetes", "statin", "lipid", "cholesterol"]):
        return "metabolism"
    if any(k in m for k in ["antioxidant", "oxidative", "nrf2", "mitochondr", "iron", "chelator"]):
        return "oxidative stress"
    if any(k in m for k in ["serotonin", "ssri", "dopamine", "antipsychotic", "antidepressant"]):
        return "psychiatric"
    if any(k in m for k in ["herp", "antiviral", "antibiotic", "infect"]):
        return "infectious"
    return "other"
