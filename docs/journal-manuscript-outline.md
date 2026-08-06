# Journal Manuscript Outline — NeuroOmics-AD

A ready-to-write methods paper narrative for submission to journals such as
*Nature Methods*, *Nucleic Acids Research* (Web Server/software track),
*Bioinformatics*, *Alzheimer's & Dementia*, or *Briefings in Bioinformatics*.

---

## Title (suggested)

**NeuroOmics-AD: an open, reproducible, AI-driven multi-omics platform for
biomarker discovery, therapeutic target prioritization and drug repurposing in
Alzheimer's disease**

## Abstract (suggested structure)

Alzheimer's disease (AD) is a multifactorial disorder whose molecular
architecture spans the genome, transcriptome, proteome, metabolome, epigenome
and single-cell transcriptome — yet these layers are rarely analyzed within a
single reproducible framework. We present **NeuroOmics-AD**, an open-source,
containerized platform that integrates data harmonization and quality control,
differential expression, cross-cohort meta-analysis, cell-type deconvolution,
pathway enrichment, network medicine, explainable machine learning (random
forest, XGBoost, SVM, deep neural networks and graph convolutional networks),
and systematic drug repurposing into one auditable pipeline. Drug candidates
are ranked by a transparent weighted ensemble of network proximity, pathway
reversal, target overlap, blood-brain barrier permeability, ADMET and clinical
evidence, with a web portal, interactive visualizations, multi-format
publication reports and an AI research assistant that drafts manuscript-ready
Results and Discussion sections. We demonstrate end-to-end operation on
simulated multi-cohort AD data and describe how the modular architecture
generalizes to Parkinson's disease, ALS, Huntington's disease and cancer.

## 1. Introduction
- Clinical challenge: >90% AD trial failure rate; multifactorial biology;
  fragmented data resources (ADNI, AMP-AD/ROSMAP, UK Biobank, GEO, NIAGADS).
- Gap: existing tools cover 1–2 modalities; few expose reproducible,
  containerized, secure end-to-end workflows with explainable AI and
  network-based drug repurposing.
- Contribution summary (5–7 bullet points).

## 2. Results (platform)
- **2.1 Architecture & reproducibility** — layered design, Celery task graph,
  artifact store, Alembic migrations, fixed seeds.
- **2.2 Data harmonization** — normalization, ComBat-style batch correction,
  MICE/KNN imputation, QC metrics (within/between-batch correlations).
- **2.3 Differential expression & meta-analysis** — empirical-Bayes moderated
  t-statistics with DESeq2/limma parity; fixed/random-effects pooling; I².
- **2.4 Deconvolution & single-cell** — NNLS (CIBERSORT-style) fractions;
  clustering, UMAP, markers, cell-type annotation.
- **2.5 Enrichment & network medicine** — curated GO/KEGG/Reactome library
  with hypergeometric + BH-FDR; hub/bottleneck identification; modules.
- **2.6 Machine learning** — model zoo performance table; feature-importance
  biomarkers; GNN gene-prioritization over the PPI interactome.
- **2.7 Drug repurposing** — six-criterion scoring; benchmark of ranked
  candidates against known AD drugs; combination suggestions.
- **2.8 Reports & assistant** — six output formats; local interpretation
  engine and LLM mode.

## 3. Discussion
- Biological convergence across omics layers.
- Translational value: repurposing candidates with established safety.
- Limitations: in silico predictions, cohort heterogeneity, validation needs.
- Generalization to other neurodegenerative diseases and cancer.

## 4. Methods
- Data generation/simulation, statistical models (with citations), ML
  hyperparameters, drug scoring formulas, BBB/ADMET rule definitions,
  reproducibility details (Docker/K8s, seeds, versions).

## 5. Data & code availability
- Code: GitHub (MIT), Docker images, CI badges, DOI via Zenodo.
- Data: synthetic demo datasets; real-cohort ingestion instructions (ADNI
  agreements, AMP-AD terms).

## Suggested key references
Love 2014 (DESeq2) · Ritchie 2015 (limma) · Johnson 2007 (ComBat) · Smyth 2004
(empirical Bayes) · Subramanian 2017 (CMap/L1000) · Menche 2015 (network
proximity) · Newman 2015 (CIBERSORT) · Wang 2014 (SNF) · Benjamini & Hochberg
1995 · Szklarczyk 2023 (STRING) · + platform-benchmark citations for
AlzGPS/DRIAD/Open Targets.

## Figures for the paper
1. Platform architecture diagram
2. QC before/after (PCA + batch correlations)
3. Volcano + DE summary (multi-cohort)
4. Meta-analysis forest plot + I²
5. Deconvolution stack plot
6. Enrichment dot plot
7. PPI network with hubs/modules
8. ML ROC curves + feature importance
9. Drug ranking bar chart + Sankey + BBB/ADMET radar
10. Report/assistant screenshots
