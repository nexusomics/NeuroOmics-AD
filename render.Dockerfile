# ==========================================================================
# NeuroOmics-AD — single-service production image (frontend + backend + SPA).
# Used by Render / Railway / any Docker host. The compiled React app is served
# by FastAPI itself, so only ONE service + one Postgres are required.
# ==========================================================================

# ---- Stage 1: build the React frontend ----
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ARG VITE_API_BASE=/api/v1
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

# ---- Stage 2: Python backend ----
FROM python:3.11-slim AS backend-base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/mpl \
    DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc g++ libopenblas0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY backend/ ./
RUN useradd -m neuroomics && chown -R neuroomics /app
USER neuroomics

# ---- Stage 3: combine ----
FROM backend-base AS runtime
COPY --from=frontend-build /build/dist /app/frontend/dist
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic upgrade head 2>/dev/null || true; uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2"]
