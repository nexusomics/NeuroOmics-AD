"""Ranking & ensemble aggregation for drug candidates."""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from app.drugs.scoring import criterion_metadata

logger = logging.getLogger(__name__)

CRITERIA = ["network", "pathway_reversal", "target_overlap", "bbb", "admet", "clinical"]
DEFAULT_WEIGHTS = {"network": 0.25, "pathway_reversal": 0.20, "target_overlap": 0.20, "bbb": 0.10, "admet": 0.10, "clinical": 0.15}


def _min_max_norm(values: list[float]) -> list[float]:
    clean = [0.0 if (v is None or not np.isfinite(v)) else v for v in values]
    lo, hi = min(clean), max(clean)
    if hi - lo < 1e-9:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in clean]


def rank_candidates(
    scored: list[dict],
    weights: Optional[dict[str, float]] = None,
    max_candidates: int = 50,
    require_bbb_positive: bool = False,
) -> dict:
    """Rank scored candidates by weighted composite score; produce Sankey-ready data."""
    weights = weights or DEFAULT_WEIGHTS
    # normalize weights to sum 1
    total = sum(weights.get(c, 0.0) for c in CRITERIA) or 1.0
    w = {c: weights.get(c, 0.0) / total for c in CRITERIA}

    if require_bbb_positive:
        scored = [s for s in scored if s["scores"]["bbb"] >= 0.5]

    # min-max normalize each criterion across the candidate set
    for c in CRITERIA:
        vals = [s["scores"][c] for s in scored]
        normed = _min_max_norm(vals)
        for s, nv in zip(scored, normed):
            s["scores_normalized"][c] = round(nv, 4)

    for s in scored:
        composite = sum(w[c] * s["scores_normalized"][c] for c in CRITERIA)
        s["composite_score"] = round(float(composite), 4)
        s["evidence"] = _rationale(s)

    ranked = sorted(scored, key=lambda s: -s["composite_score"])[:max_candidates]
    for i, s in enumerate(ranked, start=1):
        s["rank"] = i

    sankey = build_sankey(ranked[:15])
    return {
        "candidates": ranked,
        "weights": w,
        "criterion_metadata": criterion_metadata(),
        "sankey": sankey,
        "n_candidates_evaluated": len(scored),
        "n_ranked": len(ranked),
    }


def _rationale(s: dict) -> list[str]:
    """Human-readable evidence bullets per candidate."""
    r = []
    sc = s["scores"]
    if sc["network"] >= 0.6:
        r.append(f"Strong network proximity to the disease module (network score {sc['network']:.2f})")
    if sc["target_overlap"] > 0:
        overlap = [g for g in s["targets"] if g.upper() in {x.upper() for x in s.get("disease_genes", [])}]
        if overlap:
            r.append(f"Directly targets disease genes: {', '.join(sorted(set(overlap))[:5])}")
    if sc["pathway_reversal"] >= 0.4:
        r.append(f"Reverses the disease expression signature (reversal score {sc['pathway_reversal']:.2f})")
    if sc["bbb"] >= 0.7:
        r.append("High predicted blood–brain barrier permeability")
    if s.get("fda_status") == "Approved" and s.get("clinical_phase") != "approved":
        r.append("Already FDA-approved for another indication — fastest repurposing path")
    if s.get("trials", 0) >= 5:
        r.append(f"{int(s['trials'])} clinical trial(s) on record")
    if not r:
        r.append("Moderate multi-criteria evidence; consider further validation")
    return r


def build_sankey(top: list[dict]) -> dict:
    """Sankey flow: disease module → drug target categories → drugs."""
    nodes: list[str] = ["Disease module"]
    links: list[dict] = []
    node_index: dict[str, int] = {"Disease module": 0}
    for s in top:
        for t in s.get("targets", []):
            label = f"target:{t}"
            if label not in node_index:
                node_index[label] = len(nodes)
                nodes.append(label)
            links.append({"source": "Disease module", "target": label, "value": 1})
        dname = s["drug_name"]
        if dname not in node_index:
            node_index[dname] = len(nodes)
            nodes.append(dname)
        for t in s.get("targets", []):
            links.append({"source": f"target:{t}", "target": dname, "value": max(1, int(round(s["composite_score"] * 10)))})
    return {
        "nodes": nodes,
        "links": [{"source": node_index[l["source"]], "target": node_index[l["target"]], "value": l["value"]} for l in links],
        "node_labels": nodes,
    }
