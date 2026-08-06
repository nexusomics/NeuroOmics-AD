"""Blood–brain barrier (BBB) permeability & ADMET scoring.

BBB: combines curated evidence (B3DB-style annotations in the knowledge base),
physicochemical heuristics (logBB model: logP, MW, PSA, HBD) and an optional
external classifier. Returns a 0–1 permeability score.

ADMET: Lipinski/Veber rule assessment, oral-absorption heuristic, hERG &
hepatotoxicity alerts, CNS-MPO-like score. Returns 0–1 drug-likeness score.
"""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


def bbb_score(rec: dict) -> dict:
    """Composite BBB permeability score in [0, 1]."""
    curated = float(rec.get("bbb", 0.5))
    mw = float(rec.get("mw", 400) or 0)
    logp = float(rec.get("logp", 2) or 0)
    tpsa = float(rec.get("tpsa", 60) or 0)
    hbd = float(rec.get("hbd", 2) or 0)

    # Central nervous system multiparameter optimization (CNS-MPO)-style heuristics
    heuristic = 0.0
    if 150 <= mw <= 450:
        heuristic += 0.25
    if 0.0 <= logp <= 4.0:
        heuristic += 0.25
    if tpsa <= 90:
        heuristic += 0.25
    if hbd <= 3:
        heuristic += 0.25
    heuristic = min(1.0, heuristic)

    # small molecules dominate CNS drugs; biologics score low
    size_penalty = 1.0 if mw < 1000 else 0.15
    score = 0.65 * curated + 0.35 * heuristic
    score *= size_penalty
    return {
        "score": round(min(1.0, max(0.0, score)), 4),
        "curated": curated,
        "heuristic": round(heuristic, 4),
        "cns_mpo_like": round((heuristic * 4), 2),
        "bbb_positive": score >= 0.5,
    }


def admet_score(rec: dict) -> dict:
    """Rule-based ADMET score in [0, 1] with per-rule detail."""
    mw = float(rec.get("mw", 400) or 0)
    logp = float(rec.get("logp", 2) or 0)
    hbd = float(rec.get("hbd", 2) or 0)
    hba = float(rec.get("hba", 4) or 0)
    tpsa = float(rec.get("tpsa", 60) or 0)
    rot = float(rec.get("rot", 5) or 0)

    lipinski = sum([
        mw <= 500, logp <= 5.0, hbd <= 5, hba <= 10,
    ])
    veber = (rot <= 10) and (tpsa <= 140)
    rules_passed = lipinski + (1 if veber else 0)

    # alerts (simple heuristics)
    herg_alert = logp > 4.5 and mw > 300
    hepatotoxic_alert = mw > 350 and logp > 3.5

    base = rules_passed / 5.0
    if herg_alert:
        base -= 0.2
    if hepatotoxic_alert:
        base -= 0.15
    score = max(0.0, min(1.0, base))

    # biologics (huge MW) get a separate, lower pipeline-specific score
    if mw > 2000:
        score = min(score, 0.3)

    return {
        "score": round(score, 4),
        "lipinski_violations": 4 - lipinski,
        "veber_ok": bool(veber),
        "herg_alert": herg_alert,
        "hepatotoxic_alert": hepatotoxic_alert,
        "caco2_heuristic": round(min(1.0, max(0.0, (logp + 2) / 6)), 4),
    }


def summarize(rec: dict) -> dict:
    bbb = bbb_score(rec)
    admet = admet_score(rec)
    return {"bbb": bbb, "admet": admet}
