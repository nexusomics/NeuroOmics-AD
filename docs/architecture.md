# NeuroOmics-AD — System Architecture

> Version 1.0 · Status: stable

## 1. Overview

NeuroOmics-AD is a cloud-native, modular platform for **multi-omics analysis and
AI-driven drug repurposing in Alzheimer's disease (AD)**, designed for
reproducibility, extensibility, and generalization to other complex diseases.

```
┌────────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                    │
│  React 18 + TypeScript + Tailwind CSS + Plotly + D3 (frontend/)         │
│  JWT auth · project workspace · analysis studio · ML studio ·           │
│  drug studio · visualization studio · AI assistant · reports            │
└───────────────▲────────────────────────────────────┬───────────────────┘
                │ REST (JSON, OpenAPI 3.1)           │ File downloads
┌───────────────┴────────────────────────────────────▼───────────────────┐
│                          API LAYER (FastAPI)                           │
│  app/api/v1: auth · projects · datasets · analyses · omics · ml ·      │
│  drugs · reports · assistant · admin · health                          │
│  auth: JWT (access+refresh) · RBAC (researcher/reviewer/admin)         │
├────────────────────────────────────────────────────────────────────────┤
│                          SERVICE LAYER                                 │
│  preprocessing (QC · normalization · ComBat · imputation)              │
│  differential_expression (limma-style EB + R/DESeq2 bridge)            │
│  meta_analysis · deconvolution · enrichment · network · integration    │
│  single_cell · genomics · epigenomics · clinical                       │
│  visualization (matplotlib 300–600 dpi + plotly JSON)                  │
├────────────────────────────────────────────────────────────────────────┤
│                          AI LAYER                                      │
│  ml/    : Random Forest · XGBoost · SVM · DNN(MLP) · GNN(GCN)          │
│  drugs/ : knowledge base + source adapters (DrugBank/ChEMBL/DGIdb/     │
│           Open Targets/LINCS/CMap) → scoring → ranking → combinations  │
│  assistant/ : LLM-agnostic copilot + local interpretation engine,      │
│           manuscript (Results/Discussion/Methods) drafting             │
│  reports/  : PDF · DOCX · PPTX · XLSX · CSV · HTML                     │
├────────────────────────────────────────────────────────────────────────┤
│                        INFRASTRUCTURE                                  │
│  Celery workers (Redis broker/backend) · PostgreSQL (SQLAlchemy 2.0)   │
│  Redis cache (in-memory fallback) · local/S3 storage · Docker · K8s    │
└────────────────────────────────────────────────────────────────────────┘
```

## 2. Technology decisions

| Concern | Choice | Rationale |
|---|---|---|
| API | FastAPI + Pydantic v2 | async, OpenAPI-first, typed, fast |
| Orchestration | Celery + Redis | durable async analysis with progress tracking |
| RDBMS | PostgreSQL 16 (SQLite fallback in dev) | relational integrity + JSONB for flexible metadata |
| R integration | rpy2 bridge (`app/r_integration`) | DESeq2/limma/sva/WGCNA when installed; automatic Python fallback |
| ML | scikit-learn · XGBoost · PyTorch | model zoo with explainability (permutation importance, GCN) |
| Viz | matplotlib/seaborn + Plotly + D3 | publication static + interactive web figures |
| Reports | ReportLab · python-docx · python-pptx · openpyxl · jinja2 | six export formats from one data model |
| Frontend | React + Vite + TS + Tailwind + Plotly.js + D3 | fast, typed, modern UI |
| Deploy | Docker · Compose · Kubernetes · GH Actions | single-node → cluster scale-out |

## 3. Core modules

### 3.1 Data harmonization & QC (`services/preprocessing.py`)
Quantile / TMM / VST normalization · KNN / MICE-style imputation ·
ComBat-style empirical-Bayes batch correction · MAD-based outlier detection ·
QC metrics (sample correlations, library stats, within/between-batch corr).

### 3.2 Differential expression (`services/differential_expression.py`)
Linear modelling with **empirical-Bayes moderated t-statistics** (Smyth 2004)
with optional voom-like mean-variance weighting. When Bioconductor `limma` /
`DESeq2` are present, analysis delegates to R via rpy2 (identical outputs
format); otherwise a faithful Python implementation runs. BH-FDR correction.

### 3.3 Cross-cohort meta-analysis (`services/meta_analysis.py`)
Per-gene effect sizes (Cohen's d / Hedges' g / log2FC) combined with
**inverse-variance fixed effects** or **DerSimonian–Laird random effects**;
I² heterogeneity and BH-FDR.

### 3.4 Deconvolution (`services/deconvolution.py`)
CIBERSORT-style NNLS decomposition with built-in immune + CNS cell-type
signatures (B, T, NK, microglia, astrocyte, oligodendrocyte, neuron…).

### 3.5 Enrichment (`services/enrichment.py`)
Hypergeometric enrichment against a curated GO/KEGG/Reactome library (works
offline) with live Enrichr/gseapy upgrade path.

### 3.6 Network medicine (`services/network.py`)
Weighted PPI construction (STRING-like), degree/betweenness/closeness/
eigenvector centrality, **bottleneck score**, hub-gene consensus, modularity
community detection, and **network proximity z-scores** (Menche et al. 2015).

### 3.7 Multi-omics integration (`services/integration.py`)
Weighted feature fusion · MOFA-like shared-factor factorization ·
Similarity Network Fusion (SNF) for sample-level integration.

### 3.8 ML engine (`ml/`)
- `prepare_data`: ANOVA-F feature selection, stratified split, scaling
- **Random Forest**, **XGBoost**, **SVM (RBF)**, **DNN (MLP / PyTorch)**
- **GNN**: graph-convolutional gene-prioritization over the PPI graph
  (predict disease-associated genes from network context + expression)
- evaluation: accuracy, macro-F1/precision/recall, MCC, ROC-AUC, 5-fold CV
- explainability: permutation importance (SHAP-compatible interface)

### 3.9 Drug repurposing (`drugs/`)
- **Knowledge base**: ~70 curated AD-relevant drugs (targets, mechanisms,
  FDA status, trials, physico-chemical properties, direction maps)
- **Adapters**: ChEMBL REST · DGIdb REST · Open Targets GraphQL · DrugBank XML ·
  LINCS/CMap signature files (live mode optional, cache-backed)
- **Scoring** (6 criteria): network proximity · pathway reversal (CMap-style) ·
  target overlap · BBB permeability (curated + CNS-MPO heuristics) · ADMET
  (Lipinski/Veber/hERG/hepatotoxicity) · clinical evidence
- **Ranking**: transparent weighted ensemble → ranked candidates, evidence
  bullets, Sankey flows, mechanism-complementary combination suggestions

### 3.10 AI research assistant (`assistant/`)
Provider-agnostic (`local` | `llm` modes):
- `local`: deterministic interpretation engine synthesizing DE/enrichment/
  network/ML/drug narratives + manuscript-ready Results/Discussion/Methods
- `llm`: any OpenAI-compatible chat-completions endpoint, fed with a
  structured workspace context (context-grounded, no hallucination)

### 3.11 Reports (`reports/`)
Single `ReportData` model → **PDF (ReportLab), Word (docx), PowerPoint (pptx),
Excel (xlsx), CSV, HTML** with methods/results/tables/figures/interpretation/
references.

## 4. Data flow (analysis run)

```
POST /projects/{id}/analyses  →  Analysis(queued)
        │ run_analysis_task.delay(id)
        ▼
Celery worker → dispatch_analysis(analysis)      (progress 5→100)
        │
        ├─ load dataset matrix + metadata
        ├─ run service (DE/meta/enrich/…)
        ├─ save artifacts: tables (csv), figures (png @300dpi), JSON result
        └─ update Analysis status/steps in PostgreSQL
        ▼
Frontend polls GET /analyses/{id}  →  status & artifacts
        ▼
Reports: POST /reports/generate  →  PDF/DOCX/PPTX/XLSX/CSV/HTML
Assistant: POST /assistant/chat (analysis-aware context)
```

## 5. Security

- Passwords: bcrypt (12 rounds), 72-byte truncation guard
- Auth: JWT access (2 h) + refresh (30 d), HS256
- RBAC: `researcher` (own projects), `reviewer`, `admin` (platform)
- Project-level membership enforcement on every dataset/analysis/drug route
- Audit log for register/login/role changes; CORS allow-list; rate-limit-ready

## 6. Reproducibility

- Fixed seeds everywhere (`RANDOM_SEED=42`)
- Pinned Python/R dependencies, Docker images with hash-pinned base images
- Parameterized pipelines (JSON config per analysis) — re-runnable
- Artifact store keeps every table/figure/JSON per analysis run
- Alembic migrations for schema evolution

## 7. Extensibility (other diseases)

1. Create a project with a different `disease` label.
2. Swap the gene list / knowledge base (e.g. `SNCA/LRRK2/PINK1` for PD).
3. Plug new data sources or analysis types via the plugin registry
   (`app/plugins`, see [plugins.md](plugins.md)).
4. The drug knowledge base, gene sets, and signatures are all data, not code.
