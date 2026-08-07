# ==========================================================================
# NeuroOmics-AD — single-service production image (frontend + backend + SPA).
# Used by Render / Railway / any Docker host.
#
# IMPORTANT: the React frontend is PREBUILT (frontend/dist is committed to the
# repo) so no Node build happens here — that keeps the image small and avoids
# OOM on free-tier builders. Rebuild locally with: cd frontend && npm run build
#
# render.requirements.txt omits torch & rpy2 (they need huge/CUDA or R to
# build); the platform automatically uses its Python fallbacks for DNN/GNN and
# DE when they are absent.
# ==========================================================================

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/mpl \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc g++ libopenblas0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/render.requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend/ ./
COPY frontend/dist ./frontend/dist

RUN useradd -m neuroomics && chown -R neuroomics /app
USER neuroomics

EXPOSE 8000
# Wait for Postgres (up to 60s) before migrating, then serve API + SPA.
CMD ["sh", "-c", "for i in $(seq 1 30); do python -m alembic upgrade head && break || sleep 2; done; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}"]
