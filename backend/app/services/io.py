"""Data I/O helpers: load omics matrices and sample metadata from dataset records."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_SEP_BY_EXT = {".csv": ",", ".tsv": "\t", ".txt": "\t", ".gct": "\t", ".bed": "\t"}


def resolve_dataset_path(file_path: str) -> Path:
    """Resolve stored dataset path (relative to storage root when necessary)."""
    p = Path(file_path)
    if not p.exists():
        from app.core.config import settings

        alt = settings.storage_path / file_path
        if alt.exists():
            return alt
    return p


def load_expression_matrix(file_path: str, index_col: int = 0) -> pd.DataFrame:
    """Load a gene × sample (or sample × gene) expression matrix, auto-detecting layout."""
    path = resolve_dataset_path(file_path)
    sep = next((s for ext, s in _SEP_BY_EXT.items() if str(path).endswith(ext)), ",")
    df = pd.read_csv(path, sep=sep, index_col=index_col)
    # sample-first layout detection: if first data column contains floats and there
    # are more rows than columns, treat as gene × sample already; otherwise transpose.
    if df.shape[0] < df.shape[1] and not _is_gene_index(df):
        df = df.T
    df.index = df.index.astype(str)
    df.columns = df.columns.astype(str)
    return df


def _is_gene_index(df: pd.DataFrame) -> bool:
    """Heuristic: gene-symbol-like index (letters present, not all numeric)."""
    sample = [str(x) for x in df.index[: min(20, len(df.index))]]
    return any(any(c.isalpha() for c in s) for s in sample)


def load_metadata(file_path: str) -> pd.DataFrame:
    path = resolve_dataset_path(file_path)
    sep = next((s for ext, s in _SEP_BY_EXT.items() if str(path).endswith(ext)), ",")
    df = pd.read_csv(path, sep=sep)
    # auto-promote an identifier column (index/sample/sample_id/barcode/Unnamed) to the index
    id_cols = [c for c in df.columns if str(c).strip().lower() in ("", "index", "sample", "sample_id", "sampleid", "barcode", "id", "cell") or str(c).lower().startswith("unnamed")]
    if id_cols and df.shape[1] > 1:
        df = df.set_index(id_cols[0])
    df.index = df.index.astype(str)
    return df


def save_matrix(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path)
    return path


def ensure_gene_symbols(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the most variable row when gene symbols collide (first-come wins by variance)."""
    if df.index.is_unique:
        return df
    var = df.var(axis=1)
    keep = var.groupby(df.index).idxmax()
    return df.loc[keep].loc[df.index.drop_duplicates()]
