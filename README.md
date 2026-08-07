<p align="center">
  <img src="docs/assets/logo.svg" width="160" alt="NeuroOmics-AD logo" />
</p>

<h1 align="center">🧠 NeuroOmics-AD</h1>
<p align="center">
  <b>Open-source, AI-driven multi-omics platform for biomarker discovery, therapeutic target prioritization
  and drug repurposing in Alzheimer's disease</b>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/React-18-teal" alt="React"></a>
  <a href="#"><img src="https://img.shields.io/badge/FastAPI-0.110%2B-green" alt="FastAPI"></a>
  <a href="#"><img src="https://img.shields.io/badge/R-4.3%2B-lightgrey" alt="R"></a>
  <a href="#"><img src="https://img.shields.io/badge/status-production%20ready-success" alt="Status"></a>
</p>

---

## 🎯 What is NeuroOmics-AD?

**NeuroOmics-AD** is a production-ready, modular, open-source platform that integrates **genomics, transcriptomics,
proteomics, metabolomics, epigenomics, single-cell omics, GWAS and clinical data** into a single reproducible
framework for Alzheimer's disease (AD) research. It unifies the entire discovery workflow — from raw data ingestion
and quality control to differential expression, cross-cohort meta-analysis, cell-type deconvolution, pathway
enrichment, protein–protein interaction (PPI) networks, hub-gene identification, explainable machine learning and
**AI-driven drug repurposing** — behind a secure web portal with automatic multi-format reporting.

Built on a **FastAPI + Celery + PostgreSQL + Redis** backend with a **React + TypeScript + Tailwind + Plotly + D3**
frontend, containerized with **Docker** and deployable on **Kubernetes**, the platform is designed to be **reproducible,
extensible (plugin architecture) and transferable to other complex diseases** (Parkinson's, ALS, Huntington's, cancer).

> **Suitable for publication in high-impact bioinformatics / translational medicine journals** — see
> [`docs/journal-manuscript-outline.md`](docs/journal-manuscript-outline.md) for a manuscript-ready narrative.

## ✨ Feature Overview

| Layer | Capabilities |
|-------|--------------|
| **Data & QC** | Secure multi-omics upload, automated preprocessing, normalization, batch correction (ComBat-style), MICE/KNN imputation, outlier detection, QC dashboards |
| **Analysis** | Differential expression (DESeq2/limma via R or Python fallback), cross-cohort meta-analysis, single-cell analysis, cell-type deconvolution (CIBERSORT/BayesPrism-style), pathway enrichment (GO/KEGG/Reactome), WGCNA-style co-expression, PPI networks, hub-gene & module detection, multi-omics integration |
| **Genomics** | GWAS association summaries, PRS scoring, heritability & colocalization helpers, variant annotation |
| **AI / ML** | Random Forest, XGBoost, SVM, Deep Neural Networks (MLP), Graph Neural Networks (GCN) — biomarker selection, disease-stage classification, SHAP-free explainability (permutation importance, GNN attention) |
| **Drug repurposing** | Integration of DrugBank, ChEMBL, DGIdb, Open Targets, LINCS & Connectivity Map concepts; ranking by **network proximity, pathway reversal, target overlap, BBB permeability, ADMET and clinical evidence**; combination therapy suggestions |
| **Visualization** | Volcano plots, heatmaps, PCA, UMAP, t-SNE, enrichment plots, PPI networks, drug–target maps, Sankey diagrams; interactive (Plotly/D3) + publication-quality static figures (300–600 dpi) |
| **Reporting** | Automatic reports in **PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx), CSV and HTML** with methods, results, statistics, figures, tables, interpretation and references |
| **AI Assistant** | Research assistant that interprets results, explains biological significance, recommends targets / drug combinations and drafts **manuscript-ready Results & Discussion** sections |
| **Causal multi-omics (new)** | Harmonized Knight-ADRC / ADSP R4 / AMP-AD multi-ethnic / plasma multi-ancestry catalog; SVA/ComBat/LMM QC; MOFA/PLS/VAE latent fusion; NOTEARS + DML + PC causal inference; ancestry-stratified trans-ethnic meta; consensus multi-omics subtyping with drug/pathway/progression enrichment (`docs/causal-module-spec.md`) |
| **Platform** | JWT authentication, RBAC, project management, Celery task pipeline, plugin architecture, OpenAPI/Swagger, CI/CD (GitHub Actions), Docker & Kubernetes, full test suite |

## 🧱 Architecture at a glance

```
┌──────────────────────────────────────────────────────────────────────┐
│  React + TypeScript + Tailwind + Plotly + D3  (frontend)             │
│  Auth · Dashboard · Projects · Analyses · Visualization · ML ·       │
│  Drugs · Reports · AI Assistant                                      │
└───────────────▲───────────────────────────────┬──────────────────────┘
                │ REST (OpenAPI/Swagger)         │ WebSocket (task progress)
┌───────────────┴───────────────────────────────▼──────────────────────┐
│  FastAPI application  (backend/app)                                  │
│  API v1 routers → services → ML / drugs / reports / assistant        │
│  ── Celery workers (backend/app/workers) ← Redis broker/result       │
│  ── rpy2 bridge (backend/R) → R 4.3+ (DESeq2, limma, sva, WGCNA)     │
│  ── SQLAlchemy ORM → PostgreSQL (dev fallback: SQLite)               │
└──────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick start (Docker)

```bash
git clone https://github.com/your-org/NeuroOmics-AD.git && cd NeuroOmics-AD
cp .env.example .env                          # set SECRET_KEY, DB passwords
docker compose up -d --build
# Backend API  -> http://localhost:8000/docs   (Swagger UI)
# Frontend     -> http://localhost:3000
# Flower (Celery monitor) -> http://localhost:5555
```

<details><summary><b>Quick start without Docker (development)</b></summary>

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example .env
uvicorn app.main:app --reload --port 8000

# 2. Worker (in another terminal)
cd backend && celery -A app.workers.celery_app.celery_app worker -l info

# 3. Frontend
cd frontend && npm install && npm run dev   # http://localhost:5173
```

When PostgreSQL/Redis are not running, the app falls back to **SQLite + synchronous task execution**
(`TASK_ALWAYS_EAGER=true`) so the full workflow runs on a laptop.
</details>

## 🧪 Quick test run

```bash
cd backend
pip install -e ".[dev]"
pytest -q                          # ~60+ unit tests across all modules
python scripts/seed_demo.py        # optional: demo project + synthetic multi-omics data
```

## 📚 Documentation

| Document | Contents |
|----------|----------|
| [`docs/architecture.md`](docs/architecture.md) | System architecture, modules, data flow, tech decisions |
| [`docs/user-guide.md`](docs/user-guide.md) | End-user tutorial: projects → upload → analysis → drugs → reports |
| [`docs/developer-guide.md`](docs/developer-guide.md) | Setup, coding standards, contributing, extending with plugins |
| [`docs/api.md`](docs/api.md) | API overview & endpoint catalogue |
| [`docs/data-model.md`](docs/data-model.md) | Database schema & result data structures |
| [`docs/deployment.md`](docs/deployment.md) | Docker, Docker Compose, Kubernetes (Helm-less manifests), CI/CD |
| [`docs/plugins.md`](docs/plugins.md) | Plugin architecture & how to add an omics module |
| [`docs/journal-manuscript-outline.md`](docs/journal-manuscript-outline.md) | Manuscript-ready outline for a methods paper |

## 🗂 Repository layout

```
NeuroOmics-AD/
├── backend/            # FastAPI application, Celery workers, R bridge, tests
│   ├── app/
│   │   ├── api/        # REST routers (v1)
│   │   ├── core/       # config, security, db, redis, celery, logging
│   │   ├── models/     # SQLAlchemy ORM models
│   │   ├── schemas/    # Pydantic schemas
│   │   ├── services/   # omics analysis services
│   │   ├── ml/         # machine-learning & GNN engines
│   │   ├── drugs/      # drug repurposing pipeline
│   │   ├── reports/    # multi-format report generation
│   │   ├── assistant/  # AI research assistant
│   │   ├── plugins/    # plugin registry
│   │   └── workers/    # Celery tasks
│   ├── R/              # R analysis scripts (DESeq2, limma, WGCNA, meta)
│   └── tests/          # pytest suite
├── frontend/           # React + TypeScript + Tailwind + Plotly + D3
├── k8s/                # Kubernetes manifests
├── .github/workflows/  # CI/CD pipelines
├── docs/               # documentation
├── examples/           # demo notebooks & sample data
└── scripts/            # development & demo tooling
```

## 🤖 AI Research Assistant

The built-in assistant (`backend/app/assistant`) is **provider-agnostic**:

- **LLM mode** — connect any OpenAI-compatible endpoint (`ASSISTANT_API_BASE`, `ASSISTANT_API_KEY`), e.g. OpenAI, Azure, Ollama.
- **Local (offline) mode** — a deterministic *interpretation engine* that synthesizes Results & Discussion sections,
  biological interpretation and target/drug recommendations directly from analysis outputs, with zero external calls.

Example prompt handled by the assistant:
> *"Which genes are most differentially expressed in the AD vs CN comparison, and what pathways do they enrich?"*
> → returns ranked DE genes, enriched pathways, hub-gene links, and a manuscript-ready paragraph.

## 🧬 Drug repurposing pipeline

1. **Input** — prioritized genes / disease module from your analysis (or curated AD risk genes).
2. **Evidence assembly** — drug–target interactions from DrugBank, ChEMBL, DGIdb, Open Targets; expression signatures from LINCS/CMap (pathway-reversal scoring).
3. **Scoring** — network proximity (PPI shortest paths), pathway-reversal score, target overlap (Jaccard), **BBB permeability**, **ADMET** (lipinski-like + absorption + toxicity rules), **clinical evidence** (trial count, FDA status).
4. **Ranking** — transparent weighted ensemble → ranked candidate list with per-criterion breakdown (Sankey + radar visualizations).
5. **Output** — candidate table, mechanism cards, combination suggestions, report export.

## ✅ Testing, CI/CD & Deployment

- **Backend**: `pytest` (~60+ tests: auth, RBAC, DE, enrichment, meta-analysis, ML, drugs, reports, assistant, viz).
- **Frontend**: Vitest smoke tests + `tsc --noEmit` + ESLint.
- **CI (GitHub Actions)**: lint → unit tests → coverage → Docker build → publish images.
- **CD**: staging deploy on tag push; production on release (kubectl apply / Helm-ready).
- **Deployment**: `docker compose up` for single node; `k8s/*.yaml` for clusters (HPA, probes, secrets, ingress).

## 📄 License

Released under the **MIT License** — free for academic and commercial use. See [LICENSE](LICENSE).

## 🙏 Acknowledgements

Built on open standards and tools from the community: FastAPI, Celery, SQLAlchemy, scikit-learn, XGBoost, PyTorch,
NetworkX, gseapy, statsmodels, matplotlib, Plotly, D3.js, React, Tailwind CSS, and the Bioconductor ecosystem
(DESeq2, limma, sva, WGCNA, clusterProfiler).

---

<p align="center"><i>NeuroOmics-AD — accelerating translation from multi-omics data to therapeutic insight.</i></p>
