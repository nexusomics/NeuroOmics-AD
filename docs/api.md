# API Reference

Base URL: `/api/v1` · Interactive docs (Swagger UI): `/docs` · OpenAPI JSON: `/openapi.json`

**Auth**: all endpoints except `auth/*` and `system` require
`Authorization: Bearer <access_token>`. Get a token via `POST /auth/login`.

## System

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness |
| GET | `/info` | App/version/db/redis info |

## Authentication

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create researcher account `{email,password,full_name,organization?}` |
| POST | `/auth/login` | `{email,password}` → `{access_token, refresh_token}` |
| POST | `/auth/refresh` | `{refresh_token}` → new token pair |
| GET | `/auth/me` | Current user profile |
| PATCH | `/auth/me` | Update profile |
| POST | `/auth/me/change-password` | `{old_password,new_password}` |

## Projects

| Method | Path | Description |
|---|---|---|
| GET/POST | `/projects` | List / create |
| GET/PATCH/DELETE | `/projects/{id}` | Read / update / delete (owner) |
| GET/POST | `/projects/{id}/members` | List / add members |
| GET | `/projects/{id}/summary` | Dataset/analysis/drug counts |

## Datasets

| Method | Path | Description |
|---|---|---|
| GET | `/datasets?project_id=` | List project datasets |
| POST | `/datasets` | Multipart upload: `project_id,name,omics_type,platform?,file` |
| GET/DELETE | `/datasets/{id}` | Inspect / delete |
| POST | `/datasets/{id}/preview` | Head of matrix + shape |

## Analyses (Celery-backed)

| Method | Path | Description |
|---|---|---|
| GET | `/analyses?project_id=` | List |
| POST | `/analyses/{project_id}/create` | Launch analysis `{name,analysis_type,dataset_ids?,config}` |
| GET | `/analyses/{id}` | Status/progress |
| GET | `/analyses/{id}/result` | JSON result payload |
| GET | `/analyses/{id}/artifacts` | Tables/figures/JSON artifacts |
| GET | `/analyses/{id}/artifacts/{aid}/download` | Download artifact file |

`analysis_type` ∈ `differential_expression | preprocessing | meta_analysis |
deconvolution | enrichment | network | integration | ml | single_cell |
genomics | epigenomics | clinical | drug_repurposing` (+ plugins).

## Omics (synchronous convenience)

| Method | Path | Payload highlights |
|---|---|---|
| POST | `/omics/differential-expression` | `dataset_id, case_group, control_group, method, thresholds` |
| POST | `/omics/preprocessing` | `dataset_id, normalize_method, batch_correct, …` |
| POST | `/omics/enrichment` | `gene_list, databases, fdr_threshold` |
| POST | `/omics/network` | `gene_list, confidence_threshold` |
| POST | `/omics/meta-analysis` | `dataset_ids (≥2), effect_size_method, fixed_effects` |
| POST | `/omics/deconvolution` | `dataset_id, signature_source, method` |
| POST | `/omics/integration` | `dataset_ids (≥2), method, rank` |

## Machine learning

| Method | Path | Description |
|---|---|---|
| GET | `/ml/algorithms` | Supported algorithms & descriptions |
| POST | `/ml/train` | `dataset_id, label_column, algorithms[], cv_folds, top_features, gnn` |
| GET | `/ml/trained` | Models in the cache |

## Drug repurposing

| Method | Path | Description |
|---|---|---|
| POST | `/drugs/pipeline` | `gene_list, weights?, max_candidates, sources?` → ranked list + sankey + combinations |
| POST | `/drugs/pipeline/{project_id}/save` | Run & persist candidates |
| GET | `/drugs/candidates?project_id=` | Saved candidates |
| POST | `/drugs/drug-target-map` | `gene_list` → drug-target Sankey |
| POST | `/drugs/combinations` | `gene_list, top_n` → combination suggestions |
| GET | `/drugs/search?query=` | Knowledge-base search |
| GET | `/drugs/knowledge-base` | Curated drug list |

## Reports

| Method | Path | Description |
|---|---|---|
| POST | `/reports/generate` | `analysis_ids, formats[pdf,docx,pptx,xlsx,csv,html], dpi` |
| GET | `/reports/download/{analysis_id}/{filename}` | Download generated file |
| GET | `/reports/formats` | Available formats |

## AI Assistant

| Method | Path | Description |
|---|---|---|
| POST | `/assistant/chat` | `message, project_id?, analysis_ids[], history?` → `{reply, mode, context}` |
| POST | `/assistant/manuscript` | `analysis_ids, include_discussion, include_methods` → Results/Discussion/Methods |
| GET | `/assistant/mode` | Current mode (local/llm) + model |

## Admin (role: admin)

| Method | Path | Description |
|---|---|---|
| GET | `/admin/users` | List users |
| PATCH | `/admin/users/{id}` | Change role (`?role=`) |
| GET | `/admin/stats` | Platform counts |
| GET | `/admin/audit` | Audit log |

## Error format

All errors use `{"detail": "…"}`; validation errors include `detail[]` entries.
HTTP status codes: 400 (bad request), 401 (unauthorized), 403 (forbidden),
404 (not found), 409 (conflict), 422 (validation), 500 (internal).
