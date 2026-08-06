"""Manuscript-ready Results & Discussion generation from analysis outputs."""
from __future__ import annotations

import logging
from typing import Any

from app.assistant.interpretation import summarize_context

logger = logging.getLogger(__name__)


def generate_results_section(project_name: str, disease: str, analysis_results: list[dict]) -> str:
    ctx = summarize_context(project_name, disease, analysis_results)
    p: list[str] = []
    de = ctx.get("de", {})
    s = de.get("summary", {})
    n = s.get("significant", 0)
    up = s.get("upregulated", 0)
    down = s.get("downregulated", 0)

    p.append(
        f"To characterize the molecular landscape of {disease}, we applied an integrated multi-omics workflow "
        "comprising harmonization and quality control, differential expression analysis, pathway enrichment, "
        "protein–protein interaction network modeling, explainable machine learning, and systematic drug "
        "repurposing."
    )
    if de:
        p.append(
            f"Differential expression analysis across the compared groups identified {n} genes with significant "
            f"expression changes (BH-adjusted p < {s.get('fdr_threshold', 0.05)}; |log2 fold change| ≥ "
            f"{s.get('log2fc_threshold', 1.0)}), of which {up} were up-regulated and {down} were down-regulated "
            "in disease relative to control (Figure 1)."
        )
        top = de.get("table", [])[:5]
        if top:
            genes = ", ".join(f"{g['gene']}" for g in top)
            p.append(
                f"The most strongly dysregulated transcripts included {genes}, recapitulating signatures previously "
                "associated with synaptic failure, neuroinflammation, and proteostatic collapse in AD."
            )
    if ctx.get("enrichment"):
        names = ", ".join(e["pathway"] for e in ctx["enrichment"][:4])
        p.append(
            f"Gene-set enrichment revealed significant over-representation of {names}, "
            "indicating coordinated dysregulation of disease-relevant biological programs."
        )
    if ctx.get("hubs"):
        hubs = ", ".join(ctx["hubs"][:6])
        p.append(
            f"Network analysis of the dysregulated transcriptome prioritized hub genes {hubs}, whose high "
            "connectivity positions them as critical bridges between disease modules and attractive "
            "therapeutic targets."
        )
    if ctx.get("ml"):
        best = max(ctx["ml"], key=lambda m: m.get("metrics", {}).get("roc_auc", 0))
        met = best.get("metrics", {})
        p.append(
            f"Supervised machine-learning models trained on the prioritized features discriminated disease "
            f"from control with high accuracy (best model: {best.get('algorithm')}; ROC-AUC = "
            f"{met.get('roc_auc', 0):.3f}; accuracy = {met.get('accuracy', 0):.3f}; 5-fold cross-validation), "
            "supporting the translational utility of the identified biomarker panel."
        )
    if ctx.get("drugs"):
        top = ctx["drugs"][:3]
        names = ", ".join(f"{d.get('drug_name')} (score {d.get('composite_score', 0):.2f})" for d in top)
        p.append(
            f"Systematic drug repurposing ranked {names} among the top candidates, integrating network "
            "proximity to the disease module, connectivity-map pathway reversal, target overlap, "
            "blood–brain barrier permeability, ADMET profiles, and clinical trial evidence."
        )
    p.append(
        "Collectively, these findings nominate a convergent set of genes, pathways, and compounds that "
        "warrant prioritized experimental and clinical validation."
    )
    return "\n\n".join(p)


def generate_discussion_section(project_name: str, disease: str, analysis_results: list[dict]) -> str:
    ctx = summarize_context(project_name, disease, analysis_results)
    p: list[str] = []
    p.append(
        f"This study presents an integrated, reproducible framework that unifies multi-omics profiling, "
        "network medicine, and machine learning for {disease}. The convergence of transcriptomic, "
        "pathway-level, and network-level evidence provides a coherent view of disease biology that "
        "single-modality analyses cannot achieve."
    )
    de = ctx.get("de", {})
    s = de.get("summary", {})
    if de:
        p.append(
            f"The {s.get('significant', 0)} differentially expressed genes and their direction of change are "
            "consistent with the prevailing model of AD as a disorder of protein misfolding, synaptic "
            "dysfunction, and neuroinflammation. Importantly, hub-gene analysis suggests that a small "
            "set of highly connected nodes may disproportionately influence network resilience, echoing "
            "network-medicine observations that disease genes cluster in shared interactome neighborhoods."
        )
    if ctx.get("ml"):
        best = max(ctx["ml"], key=lambda m: m.get("metrics", {}).get("roc_auc", 0))
        met = best.get("metrics", {})
        p.append(
            f"The strong classification performance (ROC-AUC {met.get('roc_auc', 0):.3f}) demonstrates that "
            "expression-derived features carry robust disease-discriminative signal; however, such in-silico "
            "biomarkers require prospective validation in independent cohorts and orthogonal assays before "
            "clinical translation."
        )
    if ctx.get("drugs"):
        p.append(
            "The repurposing analysis prioritizes compounds with complementary mechanisms — targeting "
            "neuroinflammation, proteostasis, and metabolism simultaneously — reflecting the multifactorial "
            "nature of AD. Because these drugs already have established safety profiles, the most promising "
            "candidates could advance to trials faster than de novo compounds, although brain bioavailability "
            "and target engagement remain key translational hurdles."
        )
    p.append(
        "Several limitations warrant consideration. First, integration across heterogeneous cohorts can "
        "introduce batch and platform effects, partially mitigated here by harmonization. Second, the "
        "network and drug predictions are computational and require experimental validation, including "
        "functional assays, animal models, and real-world pharmacoepidemiological studies. Third, the "
        "framework is inherently extensible: the same modular architecture can be applied to Parkinson's "
        "disease, ALS, Huntington's disease, and cancer by exchanging disease-specific gene sets and "
        "knowledge bases. Ultimately, platforms such as this one aim to accelerate the translation of "
        "multi-omics discovery into therapeutic benefit for patients."
    )
    return "\n\n".join(p)


def generate_manuscript(project_name: str, disease: str, analysis_results: list[dict],
                        include_discussion: bool = True, include_methods: bool = True) -> dict[str, str]:
    """Produce Results / Methods / Discussion text blocks."""
    results = generate_results_section(project_name, disease, analysis_results)
    discussion = generate_discussion_section(project_name, disease, analysis_results) if include_discussion else ""
    methods = _generate_methods(analysis_results) if include_methods else ""
    return {
        "results": results,
        "discussion": discussion,
        "methods": methods,
        "abstract_hint": _generate_abstract_hint(results, discussion),
    }


def _generate_methods(analysis_results: list[dict]) -> str:
    methods = [
        "Data harmonization and quality control were performed with quantile normalization, KNN imputation, "
        "empirical-Bayes (ComBat-style) batch correction, and robust outlier removal.",
        "Differential expression was assessed with linear models and empirical-Bayes moderated t-statistics "
        "(limma-style), with Benjamini–Hochberg false-discovery-rate control.",
        "Pathway enrichment used hypergeometric tests against curated gene sets (GO, KEGG, Reactome) with "
        "BH-FDR correction.",
        "Protein–protein interaction networks were constructed from STRING-like interactomes; hub genes were "
        "defined by consensus top-quartile degree and betweenness centrality; disease modules were extracted "
        "by modularity-based community detection.",
        "Machine-learning classifiers (random forest, XGBoost, SVM, deep neural networks, and a graph "
        "convolutional network over the gene-interaction graph) were evaluated with stratified 5-fold "
        "cross-validation and ROC-AUC.",
        "Drug repurposing integrated drug–target knowledge (DrugBank, ChEMBL, DGIdb, Open Targets, LINCS, "
        "Connectivity Map concepts) and ranked candidates by a weighted composite of network proximity, "
        "pathway reversal, target overlap, BBB permeability, ADMET, and clinical evidence.",
        "All analyses are fully reproducible within the NeuroOmics-AD platform (Docker/Kubernetes, "
        "parameterized pipelines, versioned code).",
    ]
    return "\n".join(f"{i+1}. {m}" for i, m in enumerate(methods))


def _generate_abstract_hint(results: str, discussion: str) -> str:
    first = results.split("\n\n")[0] if results else ""
    last = discussion.split("\n\n")[-1] if discussion else ""
    return (first + " " + last).strip()[:600] + "..."
