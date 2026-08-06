# Developer Guide

## 1. Local development setup

Requirements: Python ≥ 3.11, Node ≥ 20, (optional) R ≥ 4.3, Docker.

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example .env          # adjust as needed
uvicorn app.main:app --reload --port 8000

# celery worker (optional in dev; set TASK_ALWAYS_EAGER=true to skip)
celery -A app.workers.celery_app.celery_app worker -l info --pool=solo

# frontend
cd ../frontend
npm install
npm run dev                      # http://localhost:5173 (proxies /api → :8000)
```

R (optional): install Bioconductor packages for the native R path —

```r
install.packages("BiocManager")
BiocManager::install(c("limma", "DESeq2", "sva", "WGCNA", "clusterProfiler"))
```

The platform auto-detects these; without them the equivalent Python engines
run (identical output schema).

## 2. Repository map

```
backend/
  app/
    main.py            FastAPI app factory
    core/              config, security, database, redis, celery, logging
    models/            SQLAlchemy ORM (users, projects, datasets, analyses…)
    schemas/           Pydantic request/response models
    api/v1/            REST routers
    services/          omics analysis services (pure Python, R-bridge aware)
    ml/                model zoo + training + explainability
    drugs/             knowledge base, sources, scoring, ranking
    reports/           multi-format report writers
    assistant/         AI copilot (local + LLM)
    plugins/           plugin registry
    workers/           Celery tasks
    r_integration/     rpy2 bridge
    utils/             file/storage helpers
  R/                   standalone R pipelines (limma, DESeq2, WGCNA, metafor)
  tests/               pytest suite (40+ tests)
frontend/
  src/api/             typed API client + auth token store
  src/components/      layout, ui kit, charts (Plotly/D3)
  src/pages/           route pages (dashboard, analyses, drugs, assistant…)
k8s/                   Kubernetes manifests
.github/workflows/     CI/CD pipelines
docs/                  architecture, user guide, developer guide, API…
```

## 3. Coding standards

- **Python**: Python 3.11+, type hints everywhere, `ruff` (line length 110),
  `mypy` optional; docstrings explain *why* (methods cite references).
- **Tests**: every service gets unit tests; integration tests use FastAPI
  `TestClient` with eager Celery; fixtures generate reproducible synthetic data.
- **Frontend**: TypeScript strict; components colocated; API calls only via
  `src/api/client.ts` (single typed client); no `localhost` in browser code —
  use relative `/api` URLs (Vite/nginx proxy).
- **Git**: conventional commits; feature branches → PR → CI green → merge.

```bash
# lint + test before pushing
cd backend && ruff check app tests && pytest -q
cd frontend && npx tsc --noEmit && npm run test
```

## 4. Adding a new analysis type (without forking)

1. Implement a service function returning a JSON-serializable dict.
2. Add a router endpoint (or reuse the Celery dispatch):
   - In `app/services/analysis_dispatch.py` add a branch in `dispatch_analysis`
     plus artifact persistence helpers.
   - Add the label to `_TYPE_LABELS` in `app/services/report_builder.py`.
   - Add the type + config form to `frontend/src/pages/AnalysesPage.tsx`.
3. Write tests in `backend/tests/`.

## 5. Plugin system

See [plugins.md](plugins.md). Plugin packages can register new analysis types
that appear automatically in `dispatch_analysis` (via `registry.analyses`) and
in the API without code changes to the core.

## 6. Database migrations

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

In CI/CD the backend's init container runs `alembic upgrade head` before
starting workers (see `k8s/backend.yaml`).

## 7. Adding drug knowledge

`app/drugs/knowledge.py` is a data-driven dictionary. Add a drug with:

```python
"my_drug": {
    "name": "My drug", "drugbank_id": "DBxxxxx", "pubchem_cid": "", "chebi_id": "",
    "targets": ["GENE1", "GENE2"],
    "mechanism": "…", "indication": "…",
    "fda_status": "Approved", "clinical_phase": "phase2", "trials": 12,
    "mw": 300.0, "logp": 2.5, "hbd": 1, "hba": 4, "tpsa": 60.0, "rot": 5,
    "bbb": 0.7,
    "direction": {"GENE1": -1, "GENE2": 1},   # drug effect on expression
}
```

The six criteria then score it automatically. For live enrichment, extend the
adapters in `app/drugs/sources.py`.

## 8. Running the whole stack

```bash
docker compose up -d --build          # prod-like stack
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d   # dev overlay
```

## 9. Release process

1. Bump version in `backend/pyproject.toml` and `backend/app/__init__.py`.
2. Tag `vX.Y.Z` → GitHub Actions runs CI, builds images, drafts a release.
3. Publish the release → CD workflow deploys to the cluster (see
   `.github/workflows/deploy.yml`).
