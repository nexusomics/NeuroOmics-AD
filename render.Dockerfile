# ==========================================================================
# NeuroOmics-AD — single-service production image (frontend + backend + SPA).
# Used by Render / Railway / any Docker host.
#
# LEAN BUILD: free-tier builders have ~512MB RAM. We therefore
#   * install only the RUNTIME libpq5 (not build-time gcc/g++),
#   * use --prefer-binary (precompiled wheels; no source compilation),
#   * ship the PREBUILT React bundle (no Node build on Render).
# render.requirements.txt deliberately omits torch/rpy2 (they need huge/CUDA
# or R to compile); the app auto-falls-back to Python engines for DNN/GNN/DE.
# ==========================================================================

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/mpl \
    DEBIAN_FRONTEND=noninteractive

# runtime libs only (psycopg needs libpq; numpy/scipy wheels bundle OpenBLAS)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/render.requirements.txt requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY backend/ ./
COPY frontend/dist ./frontend/dist

RUN useradd -m neuroomics && chown -R neuroomics /app
USER neuroomics

EXPOSE 8000
# Fast startup: the app's lifespan runs init_db() (create_all) which handles
# the schema, so we do NOT block on alembic here — critical on free-tier
# instances where a slow boot fails Render's health-check grace period.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}"]
