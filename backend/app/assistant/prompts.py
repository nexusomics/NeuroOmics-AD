"""Prompt templates for the AI research assistant (LLM mode)."""

SYSTEM_PROMPT = """You are NeuroOmics-AD Assistant, a knowledgeable computational-biology copilot
embedded in an open-source multi-omics platform for Alzheimer's disease (AD) research.
You help researchers interpret omics analyses, prioritize therapeutic targets,
evaluate drug-repurposing candidates, and draft manuscript sections.

Rules:
- Be precise and quantitative: cite actual p-values, fold changes, scores from the provided context.
- Distinguish statistical evidence from biological plausibility.
- Never fabricate results that are not in the provided context.
- State limitations (e.g., "in silico prediction", "requires experimental validation").
- Use plain language with concise biological explanations.
"""

ANALYSIS_CONTEXT_TEMPLATE = """## Analysis context (from the NeuroOmics-AD workspace)
Project: {project_name} | Disease: {disease}

### Differential expression summary
{de_summary}

### Top differentially expressed genes
{de_top}

### Pathway enrichment
{enrichment}

### Network / hub genes
{hubs}

### Machine-learning performance
{ml}

### Drug repurposing candidates
{drugs}

"""

RESULTS_TEMPLATE = """Write a manuscript-ready "Results" section (4-6 paragraphs, no headings,
~500 words) for a study using the provided analysis context. Include:
- cohort/analysis overview,
- number of significant genes and their direction,
- key enriched pathways and hub genes,
- ML model performance,
- top drug repurposing candidates and rationale.
Use third person, past tense, precise statistics, and journal tone.
"""

DISCUSSION_TEMPLATE = """Write a manuscript-ready "Discussion" section (5-7 paragraphs, no headings,
~600 words) interpreting the provided results. Include:
- biological interpretation of key findings,
- integration across omics layers,
- therapeutic implications and prioritized targets/drugs,
- limitations and need for experimental validation,
- outlook for precision medicine and cross-disease generalization.
"""

ANSWER_TEMPLATE = """Answer the user's question using ONLY the provided analysis context.
If the question asks for interpretation, explain the biological significance.
If it asks for recommendations, justify with scores from the context.
If the context lacks information, say so and suggest what analysis would help.
"""
