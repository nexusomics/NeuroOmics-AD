"""AI research assistant orchestration (provider-agnostic).

Mode `llm`  — calls any OpenAI-compatible chat-completions endpoint.
Mode `local` — deterministic interpretation engine (works offline, always).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.assistant.interpretation import interpret
from app.assistant.manuscript import generate_manuscript
from app.assistant.prompts import ANALYSIS_CONTEXT_TEMPLATE, SYSTEM_PROMPT
from app.core.config import settings

logger = logging.getLogger(__name__)


def build_context(project_name: str, disease: str, analysis_results: list[dict]) -> str:
    """Render structured analysis context into an LLM-friendly text block."""
    ctx = interpret(project_name, disease, analysis_results)
    f = ctx["formatted"]
    de_summary = ""
    if ctx["context"]["de"]:
        s = ctx["context"]["de"].get("summary", {})
        de_summary = (f"{s.get('significant', 0)} significant genes "
                      f"({s.get('upregulated', 0)} up / {s.get('downregulated', 0)} down); "
                      f"method: {s.get('method', 'limma-style')}")
    hubs = ", ".join(ctx["context"]["hubs"][:12]) or "none detected"
    top_de = "\n".join(
        f"  {g['gene']}: log2FC={g['log2fc']:.2f}, FDR={g['fdr']:.2e}" for g in ctx["context"]["de"].get("table", [])[:15])
    return ANALYSIS_CONTEXT_TEMPLATE.format(
        project_name=project_name or "n/a",
        disease=disease or "Alzheimer's disease",
        de_summary=de_summary or "n/a",
        de_top=top_de or "n/a",
        enrichment=f.get("enrichment", "n/a"),
        hubs=hubs,
        ml=f.get("ml", "n/a"),
        drugs=f.get("drugs", "n/a"),
    )


def _llm_complete(messages: list[dict], temperature: Optional[float] = None) -> str:
    """Call an OpenAI-compatible chat completions endpoint."""
    url = settings.ASSISTANT_API_BASE.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.ASSISTANT_API_KEY}"}
    body = {
        "model": settings.ASSISTANT_MODEL,
        "messages": messages,
        "temperature": temperature or settings.ASSISTANT_TEMPERATURE,
    }
    with httpx.Client(timeout=120) as client:
        r = client.post(url, json=body, headers=headers)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def ask(
    message: str,
    project_name: str = "",
    disease: str = "",
    analysis_results: Optional[list[dict]] = None,
    history: Optional[list[dict]] = None,
    temperature: Optional[float] = None,
) -> dict:
    """Main entry point: answer a user question with context-aware intelligence."""
    analysis_results = analysis_results or []
    context_text = build_context(project_name, disease, analysis_results)
    ctx = interpret(project_name, disease, analysis_results)

    if settings.ASSISTANT_MODE == "llm" and settings.ASSISTANT_API_KEY:
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            if context_text.strip():
                messages.append({"role": "system", "content": f"## Workspace context\n{context_text}"})
            for h in (history or [])[-8:]:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            messages.append({"role": "user", "content": message})
            reply = _llm_complete(messages, temperature)
            return {"reply": reply, "mode": "llm", "context": ctx, "model": settings.ASSISTANT_MODEL}
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM call failed (%s); falling back to local engine.", exc)

    reply = _local_answer(message, ctx, context_text)
    return {"reply": reply, "mode": "local", "context": ctx, "model": "NeuroOmics-AD interpretation engine"}


def _local_answer(message: str, ctx: dict, context_text: str) -> str:
    q = message.lower()
    parts: list[str] = []

    if any(k in q for k in ["hub", "network", "target"]):
        hubs = ctx["context"].get("hubs", [])
        if hubs:
            parts.append(
                "**Prioritized targets (hub genes):** " + ", ".join(hubs[:10]) +
                " — high-connectivity nodes bridging disease modules; strong candidates for functional and druggability follow-up.")
        else:
            parts.append("No hub genes were identified in the current analysis context.")
    if any(k in q for k in ["drug", "compound", "repurpos", "medication", "therap"]):
        drugs = ctx["context"].get("drugs", [])
        if drugs:
            lines = []
            for d in drugs[:8]:
                lines.append(f"- **{d.get('drug_name')}** (rank {d.get('rank')}, composite {d.get('composite_score', 0):.2f}) — {d.get('mechanism', '')}")
            parts.append("**Top repurposing candidates:**\n" + "\n".join(lines))
        else:
            parts.append("Run the drug-repurposing pipeline to obtain candidates.")
    if any(k in q for k in ["pathway", "enrich", "go ", "kegg", "reactome"]):
        enr = ctx["context"].get("enrichment", [])
        if enr:
            parts.append("**Enriched pathways:**\n" + "\n".join(f"- {e['pathway']} (FDR {e['fdr']:.2e})" for e in enr[:6]))
        else:
            parts.append("No significant enrichments in the current context.")
    if any(k in q for k in ["gene", "differ", "deg", "expression"]):
        de = ctx["context"].get("de", {})
        top = de.get("table", [])[:10]
        if top:
            parts.append("**Top differentially expressed genes:**\n" + "\n".join(
                f"- {g['gene']}: log2FC {g['log2fc']:.2f}, FDR {g['fdr']:.2e}" for g in top))
        else:
            parts.append("No DE results in the current context.")
    if any(k in q for k in ["model", "machine", "auc", "accuracy", "classif"]):
        ml = ctx["context"].get("ml", [])
        if ml:
            parts.append("**Model performance:**\n" + "\n".join(
                f"- {m.get('algorithm')}: AUC {m.get('metrics', {}).get('roc_auc', 0):.3f}, "
                f"accuracy {m.get('metrics', {}).get('accuracy', 0):.3f}" for m in ml[:6]))
        else:
            parts.append("No ML results in the current context.")
    if any(k in q for k in ["combination", "combo"]):
        # combination suggestions come from the pipeline; synthesize from top candidates
        drugs = ctx["context"].get("drugs", [])
        if len(drugs) >= 2:
            a, b = drugs[0], drugs[1]
            parts.append(f"**Suggested combination:** {a.get('drug_name')} (mechanism: {a.get('mechanism')}) + "
                         f"{b.get('drug_name')} (mechanism: {b.get('mechanism')}) — complementary mechanisms "
                         "targeting distinct disease axes; combination rationale requires experimental validation.")
        else:
            parts.append("Not enough candidates for combination inference; run the pipeline with more inputs.")
    if any(k in q for k in ["interpret", "explain", "significance", "biology", "meaning", "what does"]):
        for line in ctx.get("interpretation", []):
            parts.append("- " + line)

    if not parts:
        # general fallback: present the full interpretation summary
        parts.append("Here is a summary of the current analysis context:")
        for line in ctx.get("interpretation", []):
            parts.append("- " + line)
        parts.append(
            "\nYou can ask about **genes**, **pathways**, **hub targets**, **drug candidates**, "
            "**model performance**, or ask me to **draft Results/Discussion** for your project.")

    reply = "\n\n".join(parts)
    if ctx["context"]["de"] or ctx["context"]["drugs"]:
        reply += (
            "\n\n---\n*Generated by the NeuroOmics-AD local interpretation engine. "
            "All predictions are in-silico and require experimental validation.*")
    return reply


def draft_manuscript(project_name: str, disease: str, analysis_results: list[dict],
                     include_discussion: bool = True, include_methods: bool = True) -> dict[str, str]:
    """Manuscript drafting via LLM when configured, else local generation."""
    if settings.ASSISTANT_MODE == "llm" and settings.ASSISTANT_API_KEY:
        try:
            from app.assistant.prompts import DISCUSSION_TEMPLATE, RESULTS_TEMPLATE

            context_text = build_context(project_name, disease, analysis_results)
            messages = [{"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "system", "content": f"## Workspace context\n{context_text}"}]
            results = _llm_complete(messages + [{"role": "user", "content": RESULTS_TEMPLATE}])
            discussion = ""
            if include_discussion:
                discussion = _llm_complete(messages + [{"role": "user", "content": DISCUSSION_TEMPLATE}])
            methods = _llm_complete(messages + [{"role": "user", "content": "Write a concise Methods summary for the analyses in the context."}]) if include_methods else ""
            return {"results": results, "discussion": discussion, "methods": methods, "mode": "llm"}
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM manuscript generation failed (%s); using local engine.", exc)
    local = generate_manuscript(project_name, disease, analysis_results, include_discussion, include_methods)
    local["mode"] = "local"
    return local
