# User Guide

This guide walks a researcher from first login to a full multi-omics +
drug-repurposing analysis and report.

## 1. Getting started

1. Start the platform: `docker compose up -d --build` (or the dev quick start in the README).
2. Open **http://localhost:3000** (Docker) or **http://localhost:5173** (dev).
3. Log in with the seeded demo account:

   | Role | Email | Password |
   |---|---|---|
   | Demo researcher | `demo@neuroomics.org` | `demo12345` |
   | Administrator | `admin@neuroomics.org` | `admin12345` |

   …or create your own account (researcher role).

> Demo data: run `python backend/scripts/seed_demo.py` to populate a demo
> project with synthetic transcriptomics / proteomics / metabolomics datasets
> and pre-computed analyses.

## 2. Projects

- **Create** a project (name, description, disease model).
- Projects are **private**: only you and invited members can see them
  (Owner → *Add member* by email).
- Every dataset, analysis, drug candidate and report belongs to a project.

## 3. Uploading data

Open the project → **Data upload**:

1. Pick an **omics type** — transcriptomics, proteomics, metabolomics,
   genomics/GWAS, epigenomics, single-cell, clinical.
2. Upload a CSV/TSV matrix — **rows = features (genes), columns = samples**
   (sample-first layout is auto-detected and transposed).
3. Upload **sample metadata** as a *clinical* dataset: first column = sample
   IDs, plus columns like `group` (AD/CN), `batch`, `age`, `sex`, `time`, `event`.
4. The system parses dimensions and marks the dataset `ready`.

> Tip: name the metadata file anything, but ensure its first column holds
> sample IDs — the platform promotes it to the row index automatically.

## 4. Analyses

**Project → Analyses → New analysis.** Choose a type:

| Type | What it does |
|---|---|
| Differential expression | AD vs CN (limma/DESeq2-style), volcano + heatmap + top table |
| Preprocessing / QC | normalize, batch-correct (ComBat), impute, remove outliers |
| Meta-analysis | combine ≥2 cohorts (fixed/random effects) |
| Deconvolution | cell-type fractions from bulk RNA |
| Enrichment | GO/KEGG/Reactome pathway enrichment |
| Network | PPI network, hub genes, modules |
| Integration | multi-omics fusion (weighted/MOFA-like) |
| ML | train RF/XGB/SVM/DNN/GNN on your data |
| Single-cell | QC, clustering, UMAP, markers |
| Genomics | GWAS summary QC (λ, significant loci) |
| Epigenomics | differential methylation (DMPs) |
| Clinical | Kaplan–Meier, stratification, subgroup tests |
| Drug repurposing | full repurposing pipeline on a gene list |

Analyses run **asynchronously** on Celery workers; the UI shows live progress.
Open an analysis to see its **result JSON, tables (CSV) and figures (PNG)**,
all downloadable.

## 5. Machine learning studio

**Project → ML Models.**

1. Select a dataset (needs a `group` label column in metadata).
2. Pick algorithms — Random Forest, XGBoost, SVM, Deep NN, GNN.
3. **Train** → compare ROC-AUC, accuracy, F1; inspect top biomarkers
   (permutation importance) and GNN-prioritized genes.

The GNN performs *gene prioritization* over the PPI graph — it predicts which
genes are disease-associated using network context, i.e. therapeutic-target
prediction.

## 6. Visualization studio

**Project → Visualization.**

- Enter a gene set → build an interactive **PPI network** (D3, hubs highlighted)
  and a **drug–target Sankey** flow.
- Run **volcano** on the first dataset.
- 300–600 dpi static versions of every figure are exported in Reports.

## 7. Drug repurposing

**Project → Drug repurposing.**

1. Enter prioritized disease genes (or accept the AD preset).
2. **Run pipeline** → ~70 drugs scored on six criteria:
   network proximity · pathway reversal · target overlap · BBB · ADMET · clinical.
3. Inspect the ranked list with per-criterion breakdowns, evidence bullets,
   **combination suggestions**, and the Sankey flow.
4. Candidates are saved to the project automatically.

> The knowledge base is curated for offline reproducibility. Enable
> `DRUG_ENABLE_LIVE_API=true` to enrich with live ChEMBL / DGIdb / Open Targets
> queries (cached for 24 h).

## 8. Reports

**Project → Reports.**

1. Select completed analyses.
2. Choose formats — **PDF, Word, PowerPoint, Excel, CSV, HTML**.
3. Set figure DPI (150 / 300 / 600).
4. **Generate** → download.

Every report contains: methods, results, statistical tables, figures,
biological interpretation, and references (methods-paper style).

## 9. AI assistant

**Project → AI assistant.**

Ask questions like:

- *"Which genes are most differentially expressed and what do they mean?"*
- *"Interpret the enriched pathways in AD biology."*
- *"What are the top drug candidates and why?"*
- *"Recommend a drug combination."*
- *"Draft the Results section."*

The assistant is context-aware: it uses your selected completed analyses.
**Manuscript assistant** button generates Results + Discussion + Methods.

Two modes (configurable in `.env`):
- `local` — built-in interpretation engine (offline, always works)
- `llm` — any OpenAI-compatible endpoint (`ASSISTANT_API_KEY`)

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| "label column 'group' not found" | metadata upload missing/not linked — re-upload clinical metadata with a `group` column |
| Analyses stay `queued` | Celery worker not running — start `celery -A app.workers.celery_app.celery_app worker` or set `TASK_ALWAYS_EAGER=true` in dev |
| "No samples overlap" | matrix columns and metadata sample IDs must match exactly |
| Reports missing a format | check backend logs; every format is independently generated |
| Redis connection refused | dev fallback is automatic; production requires Redis |
