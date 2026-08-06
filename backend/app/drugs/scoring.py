"""Drug repurposing scoring engine.

Computes six evidence criteria per candidate drug:
  1. network proximity   — shortest-path proximity between disease module and drug targets
  2. pathway reversal    — connectivity-map-style signature reversal against disease expression
  3. target overlap      — direct overlap of drug targets with disease genes
  4. BBB permeability    — blood-brain barrier score
  5. ADMET               — absorption, distribution, metabolism, excretion, toxicity rules
  6. clinical evidence   — FDA status, trial count, phase
"""
from __future__ import annotations

import logging
import math
from typing import Optional

import networkx as nx
import numpy as np

from app.drugs.bbb_admet import summarize
from app.services.network import build_network, network_proximity

logger = logging.getLogger(__name__)

_PHASE_RANK = {"preclinical": 0, "phase1": 1, "phase2": 2, "phase3": 3, "approved": 4}
_FDA_RANK = {"": 0, "Investigational": 1, "Experimental": 1, "Withdrawn": 1, "Approved (supplement)": 2,
             "Approved (GRAS)": 2, "Approved": 3}


def _sigmoid(x: float, k: float = 1.0, x0: float = 0.0) -> float:
    return 1.0 / (1.0 + math.exp(-k * (x - x0)))


def score_network_proximity(disease_genes: set[str], drug_targets: list[str], G: nx.Graph) -> float:
    """Z-score proximity → [0,1] (higher = closer)."""
    z = network_proximity(G, disease_genes, set(drug_targets))
    # negative z = closer than expected; map with sigmoid
    return round(float(_sigmoid(-z, k=0.8)), 4)


def score_pathway_reversal(disease_direction: dict[str, int], drug_direction: dict[str, int]) -> float:
    """CMap-style reversal: fraction of disease genes reversed by the drug.

    disease_direction: gene → +1 (up in disease) / -1 (down in disease)
    drug_direction:    gene → +1 (upregulated by drug) / -1 (downregulated)
    """
    if not disease_direction or not drug_direction:
        return 0.0
    hits = 0
    total = 0
    for gene, ddir in disease_direction.items():
        if gene in drug_direction:
            total += 1
            if drug_direction[gene] == -ddir:  # drug opposes disease direction
                hits += 1
    if total == 0:
        # fall back: treat drug targets themselves as reversal evidence when
        # the drug inhibits a disease-upregulated target
        return 0.0
    return round(hits / total, 4)


def score_target_overlap(disease_genes: set[str], drug_targets: list[str]) -> float:
    """Normalized Jaccard overlap between disease genes and drug targets."""
    if not drug_targets:
        return 0.0
    t = set(drug_targets)
    inter = len(disease_genes & t)
    union = len(disease_genes | t)
    return round(inter / max(union, 1), 4)


def score_bbb(rec: dict) -> float:
    return summarize(rec)["bbb"]["score"]


def score_admet(rec: dict) -> float:
    return summarize(rec)["admet"]["score"]


def score_clinical(rec: dict) -> float:
    """Clinical evidence: phase + FDA status + trial volume."""
    phase = _PHASE_RANK.get(rec.get("clinical_phase", "preclinical"), 0)
    fda = _FDA_RANK.get(rec.get("fda_status", ""), 0)
    trials = min(float(rec.get("trials", 0)) / 50.0, 1.0)
    score = 0.45 * (phase / 4) + 0.35 * (fda / 3) + 0.2 * trials
    return round(min(1.0, score), 4)


def score_drug(rec: dict, disease_genes: set[str], disease_direction: Optional[dict[str, int]], G: nx.Graph) -> dict:
    """Score a single drug record across all six criteria."""
    targets = [t.upper() for t in rec.get("targets", [])]
    scores = {
        "network": score_network_proximity(disease_genes, targets, G),
        "pathway_reversal": score_pathway_reversal(disease_direction or {}, rec.get("direction", {})),
        "target_overlap": score_target_overlap(disease_genes, targets),
        "bbb": score_bbb(rec),
        "admet": score_admet(rec),
        "clinical": score_clinical(rec),
    }
    return scores


def criterion_metadata() -> dict:
    return {
        "network": "Network proximity (z-score) between disease module and drug targets in the PPI interactome",
        "pathway_reversal": "Connectivity-Map-style expression signature reversal",
        "target_overlap": "Normalized Jaccard overlap of drug targets with prioritized disease genes",
        "bbb": "Blood–brain barrier permeability (curated + CNS-MPO heuristic)",
        "admet": "Rule-based ADMET profile (Lipinski, Veber, hERG, hepatotoxicity)",
        "clinical": "Clinical evidence (FDA status, trial phase, trial volume)",
    }
