# ==========================================================================
# NeuroOmics-AD backend — multi-stage build
#   Stage 1: Python deps
#   Stage 2: R + Bioconductor analysis environment (DESeq2/limma/sva/WGCNA)
#   Stage 3: runtime image
# ==========================================================================

# ---------- Stage 1: Python dependencies ----------
FROM python:3.11-slim AS python-deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---------- Stage 2: R + Bioconductor ----------
FROM rocker/r-ver:4.4 AS r-env
RUN R -e 'install.packages(c("BiocManager"), repos="https://cloud.r-project.org", quiet=TRUE)' \
 && R -e 'BiocManager::install(c("limma","DESeq2","sva","WGCNA","clusterProfiler","BiocParallel"), ask=FALSE, update=FALSE)' \
 || true  # analysis falls back to the Python engines if R packages are unavailable

# ---------- Stage 3: runtime ----------
FROM python:3.11-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/mpl \
    DEBIAN_FRONTEND=noninteractive

# R runtime + minimal system libs for matplotlib/scipy/numpy wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        r-base r-base-dev libcurl4-openssl-dev libssl-dev libxml2-dev \
        libpq-dev gcc g++ libopenblas0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# copy R env from stage 2 (keeps R + Bioconductor available at runtime)
COPY --from=r-env /usr/local/lib/R /usr/local/lib/R
COPY --from=r-env /usr/local/bin/R /usr/local/bin/R
COPY --from=r-env /usr/local/lib/R/bin /usr/local/lib/R/bin
ENV R_HOME=/usr/local/lib/R

WORKDIR /app
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin
COPY . .

RUN useradd -m neuroomics
USER neuroomics

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
