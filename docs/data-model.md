# Data Model

## 1. Relational schema (PostgreSQL / SQLite fallback)

```
users(id, email UQ, full_name, hashed_password, role, organization,
      is_active, is_verified, created_at, last_login_at)

projects(id, name, description, disease, species, owner_id → users,
         status, created_at, updated_at)

project_memberships(id, project_id → projects, user_id → users,
                    role[owner|member|viewer], added_at)   UQ(project,user)

datasets(id, project_id → projects, name, omics_type, platform, file_path,
         format, n_samples, n_features, metadata_json JSONB,
         status[uploaded|ready|qc_passed|qc_failed], uploaded_by → users,
         created_at)

dataset_samples(id, dataset_id → datasets, sample_id, group, covariates JSONB)

analyses(id, project_id → projects, name, analysis_type, config JSONB,
         status[queued|running|completed|failed|cancelled], progress,
         owner_id → users, error_message, created_at, started_at, finished_at)

analysis_steps(id, analysis_id → analyses, step_name, status, message,
               duration_seconds, started_at, finished_at)

result_artifacts(id, analysis_id → analyses, name, kind[table|figure|json|
               text|report], format[csv|json|png|svg|html|pdf|docx|pptx|xlsx],
               file_path, size_bytes, metadata_json, created_at)

drug_candidates(id, project_id → projects, drug_name, drugbank_id, chebi_id,
               pubchem_cid, mol_formula, mol_weight, mechanism, targets JSONB,
               indication, fda_status, evidence_sources JSONB,
               score_network, score_pathway_reversal, score_target_overlap,
               score_bbb, score_admet, score_clinical, composite_score, rank,
               details JSONB, created_at)

audit_logs(id, user_id, action, resource_type, resource_id, details JSONB,
           ip_address, created_at)
```

JSON columns (`metadata_json`, `config`, `details`) store flexible,
schema-versioned payloads — the platform schema stays stable while analysis
configurations evolve.

## 2. Analysis result envelope (JSON artifact)

Every analysis stores `<analysis_id>/<type>.json`:

```jsonc
{
  "table": [ { "gene": "APP", "log2fc": 2.1, "ave_expr": 8.3, "t": 12.4,
               "pvalue": 1e-9, "fdr": 1e-8, "sig": true, "direction": "up" } ],
  "summary": { "tested_genes": 20000, "significant": 342,
               "upregulated": 180, "downregulated": 162,
               "fdr_threshold": 0.05, "log2fc_threshold": 1.0,
               "method": "python:limma-style" }
}
```

Drug pipeline result adds `candidates[]` (each with the six criterion scores +
`composite_score` + `rank` + `evidence[]`), `combinations[]`, `sankey`, `weights`.

## 3. Storage layout

```
media/                        # STORAGE_ROOT
  uploads/<uuid>.<ext>        # raw uploaded datasets
  artifacts/<analysis_id>/
    differential_expression.json
    differential_expression_table.csv
    volcano.png               # 300 dpi (configurable 150–600)
    volcano.plotly.json       # interactive spec
    ...
    reports/<title>.pdf|.docx|.pptx|.xlsx|.html
  .mlcache/<model_key>/
    model.joblib  metadata.json
  demo/                       # seed_demo synthetic data
```

## 4. Sample metadata conventions

The first column of a metadata CSV is auto-promoted to the sample index.
Recommended columns: `group` (case/control labels), `batch` (batch correction),
`age`, `sex`, `time`, `event` (survival), and any covariates.
