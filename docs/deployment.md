# Deployment Guide

## 1. Docker Compose (single node)

```bash
cp .env.example .env
# set SECRET_KEY (python -c "import secrets; print(secrets.token_urlsafe(64))")
docker compose up -d --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API + Swagger | http://localhost:8000/docs |
| Celery Flower | http://localhost:5555 |

Persistent volumes: `pgdata`, `redisdata`, `media`.

### Production checklist

- `SECRET_KEY` ≥ 64 random bytes; change `ADMIN_PASSWORD`.
- Set `ENVIRONMENT=production`, `DEBUG=false`.
- Point `DATABASE_URL` at Postgres (done by compose), disable eager tasks.
- Optional: `ASSISTANT_API_KEY` for LLM mode; `S3_*` for object storage.

## 2. Kubernetes

```bash
kubectl create namespace neuroomics || true
cp k8s/secrets.example.yaml k8s/secrets.yaml   # fill values (never commit)
kubectl apply -f k8s/                          # namespace → … → hpa
kubectl rollout status deployment/neuroomics-backend -n neuroomics
```

Manifest inventory:

| File | Purpose |
|---|---|
| namespace.yaml | `neuroomics` namespace |
| configmap.yaml | non-secret env |
| secrets.example.yaml | secrets template |
| postgres.yaml | StatefulSet + headless service + 20Gi PVC |
| redis.yaml | Deployment + service |
| backend.yaml | API Deployment (3 replicas, HPA-ready) + migration initContainer + service |
| worker.yaml | Celery worker + flower |
| frontend.yaml | nginx-served SPA |
| media-pvc.yaml | RWX storage for artifacts |
| ingress.yaml | TLS ingress (cert-manager annotation) |
| hpa.yaml | CPU/memory autoscaling |

Notes:
- `media-pvc.yaml` needs a RWX StorageClass (e.g. EFS, NFS, longhorn).
- Ingress host is a placeholder — replace `neuroomics.example.org`.
- Backend HPA 3–12 replicas; worker HPA 2–8.

## 3. GitHub Actions

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | push/PR to main, develop | backend lint+tests (Postgres+Redis services), frontend tsc+tests+build, Docker build check, OpenAPI contract check |
| `docker.yml` | tags `v*`, main | build & push `ghcr.io/<repo>-backend|-frontend` images |
| `deploy.yml` | release / manual | `kubectl apply -f k8s/` + rollout status |
| `docs.yml` | docs changes on main | build & publish MkDocs site to GitHub Pages |
| `release.yml` | tags `v*` | draft GitHub Release |

Secrets to configure: `KUBE_CONFIG` (base64 kubeconfig), `GH_TOKEN`/`GITHUB_TOKEN`.

## 4. Scaling & performance

- **CPU-bound stats** (DE, meta-analysis, ML): scale `worker` replicas.
- **API** (concurrent users): scale backend replicas; uvicorn `--workers N`.
- **Storage**: artifacts grow fast — use S3-compatible object storage
  (`STORAGE_BACKEND=s3`) for multi-node deployments.
- **R**: install Bioconductor packages in the image for native R pipelines;
  workers benefit from more memory (peak ~2–4 GB for DESeq2/WGCNA).

## 5. Observability

- Health endpoints: `/api/v1/health`, `/api/v1/info`.
- Celery Flower at :5555 (task queues, failures, retries).
- Postgres/Redis metrics via standard exporters; add `kubectl top` checks.
- Structured logs on stdout (JSON-ready format), audit table for security events.
