"""Local (offline) interpretation engine.

Deterministically synthesizes biological interpretation, Results and Discussion
prose directly from analysis outputs — no external LLM required. Used both as
the default assistant backend and as the fallback when no API key is set.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def summarize_context(project_name: str, disease: str, analysis_results: list[dict]) -> dict[str, Any]:
    """Aggregate analysis results into a structured, assistant-friendly context."""
    ctx: dict[str, Any] = {
        "project_name": project_name or "Unnamed project",
        "disease": disease or "Alzheimer's disease",
        "de": {}, "enrichment": [], "hubs": [], "ml": [], "drugs": [], "meta": {},
    }
    for res in analysis_results:
        rtype = res.get("type", res.get("analysis_type", ""))
        payload = res.get("result", res)
        if rtype in ("differential_expression", "de") or "table" in payload and isinstance(payload.get("table"), list) and payload["table"] and "log2fc" in payload["table"][0]:
            ctx["de"] = payload
        elif rtype in ("enrichment",) or "pathway" in payload.get("table", [{}])[0]:
            ctx["enrichment"] = payload.get("table", [])[:10]
        elif rtype in ("network",) or "hub_genes" in payload:
            ctx["hubs"] = payload.get("hub_genes", [])[:15]
            ctx["network_summary"] = payload.get("summary", {})
        elif rtype in ("ml", "ml_training") or "results" in payload and isinstance(payload.get("results"), list):
            ctx["ml"] = payload.get("results", [])
        elif rtype in ("drug_repurposing", "drugs") or "candidates" in payload:
            ctx["drugs"] = payload.get("candidates", [])[:10]
        elif rtype in ("meta_analysis", "meta"):
            ctx["meta"] = payload
    return ctx


def _format_de(de: dict) -> str:
    table = de.get("table", [])
    summary = de.get("summary", {})
    n_up = summary.get("upregulated", 0)
    n_down = summary.get("downregulated", 0)
    top = table[:10]
    lines = [
        f"DE analysis tested {summary.get('tested_genes', len(table))} genes; "
        f"{summary.get('significant', 0)} significant "
        f"({n_up} up-regulated, {n_down} down-regulated) at FDR {summary.get('fdr_threshold', 0.05)} "
        f"and |log2FC| ≥ {summary.get('log2fc_threshold', 1.0)} (method: {summary.get('method', 'limma-style')})."
    ]
    if top:
        lines.append("Top genes: " + ", ".join(
            f"{g['gene']} (log2FC={g['log2fc']:.2f}, FDR={g['fdr']:.2e})" for g in top[:8]))
    return "\n".join(lines)


def _format_enrichment(enr: list[dict]) -> str:
    if not enr:
        return "No significant pathway enrichment at the selected threshold."
    return "Enriched pathways: " + "; ".join(
        f"{e['pathway']} (FDR={e['fdr']:.2e})" for e in enr[:6])


def _format_ml(ml: list[dict]) -> str:
    if not ml:
        return "No ML results in context."
    parts = []
    for m in ml[:5]:
        met = m.get("metrics", {})
        parts.append(f"{m.get('algorithm')}: accuracy={met.get('accuracy', float('nan')):.3f}, "
                     f"ROC-AUC={met.get('roc_auc', float('nan')):.3f}")
    return "Model performance — " + " | ".join(parts)


def _format_drugs(drugs: list[dict]) -> str:
    if not drugs:
        return "No drug candidates in context."
    return "Top drug candidates: " + "; ".join(
        f"{d.get('drug_name')} (composite={d.get('composite_score', 0):.3f}, rank={d.get('rank', '?')})"
        for d in drugs[:6])


def interpret(project_name: str, disease: str, analysis_results: list[dict], question: str = "") -> dict[str, Any]:
    """Produce structured interpretation for a question (or general summary)."""
    ctx = summarize_context(project_name, disease, analysis_results)
    interpretation = []

    if ctx["de"]:
        de = ctx["de"]
        s = de.get("summary", {})
        up = s.get("upregulated", 0)
        down = s.get("downregulated", 0)
        if up + down > 0:
            direction = "predominantly up-regulated" if up >= down else "predominantly down-regulated"
            interpretation.append(
                f"Differential expression identified {s.get('significant', 0)} significant genes "
                f"({up} up, {down} down), {direction} in {disease} relative to control.")
            top = de.get("table", [])[:8]
            if top:
                genes = ", ".join(g["gene"] for g in top[:6])
                interpretation.append(f"Leading candidates include {genes}, warranting cross-cohort replication and functional follow-up.")

    if ctx["enrichment"]:
        top_pw = ctx["enrichment"][:3]
        names = ", ".join(p["pathway"] for p in top_pw)
        interpretation.append(
            f"Enrichment analysis highlights {names}, consistent with established {disease} pathobiology "
            "(amyloid/tau processing, neuroinflammation, mitochondrial and metabolic dysregulation).")

    if ctx["hubs"]:
        hubs = ", ".join(ctx["hubs"][:8])
        interpretation.append(
            f"Network analysis prioritizes hub genes {hubs} — high betweenness/degree nodes that bridge "
            "disease modules and represent promising (often druggable) intervention points.")

    if ctx["ml"]:
        best = max(ctx["ml"], key=lambda m: m.get("metrics", {}).get("roc_auc", 0)) if ctx["ml"] else None
        if best:
            met = best.get("metrics", {})
            interpretation.append(
                f"Machine-learning classification achieved ROC-AUC {met.get('roc_auc', 0):.3f} "
                f"(accuracy {met.get('accuracy', 0):.3f}) with {best.get('algorithm')}, "
                "supporting the discriminative value of the prioritized biomarker panel.")

    if ctx["drugs"]:
        top = ctx["drugs"][0] if ctx["drugs"] else None
        if top:
            interpretation.append(
                f"The top repurposing candidate is {top.get('drug_name')} "
                f"(composite score {top.get('composite_score', 0):.3f}); mechanism: {top.get('mechanism', 'n/a')}. "
                "This ranking integrates network proximity, pathway reversal, target overlap, BBB/ADMET and clinical evidence, "
                "and should be validated experimentally and in real-world EHR cohorts.")

    if not interpretation:
        interpretation.append("No analyzable results found in the provided context. Run an analysis first.")

    return {
        "context": ctx,
        "interpretation": interpretation,
        "formatted": {
            "de": _format_de(ctx["de"]) if ctx["de"] else "No DE results.",
            "enrichment": _format_enrichment(ctx["enrichment"]),
            "ml": _format_ml(ctx["ml"]),
            "drugs": _format_drugs(ctx["drugs"]),
        },
    }
