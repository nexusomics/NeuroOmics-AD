"""Shared fixtures for the NeuroOmics-AD test suite."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_neuroomics.db")
os.environ.setdefault("TASK_ALWAYS_EAGER", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("STORAGE_ROOT", str(Path(tempfile.mkdtemp()) / "media"))
os.environ.setdefault("ASSISTANT_MODE", "local")

from app.core.database import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    init_db()
    yield
    engine.dispose()


@pytest.fixture()
def client():
    from app.core.database import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        for u in db.query(User).all():
            db.delete(u)
        db.commit()
    finally:
        db.close()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client) -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "email": "researcher@test.org", "password": "password123",
        "full_name": "Test Researcher", "organization": "Test Lab"})
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/auth/login", json={"email": "researcher@test.org", "password": "password123"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(client) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"email": "admin@neuroomics.org", "password": "admin12345"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def project_id(client, auth_headers) -> str:
    r = client.post("/api/v1/projects", headers=auth_headers, json={
        "name": "Test AD Project", "description": "integration test",
        "disease": "Alzheimer's disease"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def make_synthetic_expression(n_genes: int = 120, n_ad: int = 24, n_cn: int = 24, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Synthetic gene×sample matrix with a real disease signal + metadata."""
    rng = np.random.default_rng(seed)
    curated = ["APP", "BACE1", "PSEN1", "APOE", "TREM2", "TYROBP", "MAPT", "GSK3B",
               "IL1B", "TNF", "IL6", "CLU", "SORL1", "PICALM", "HMOX1", "MTOR",
               "BECN1", "GFAP", "AQP4", "CSF1R"]
    genes = [f"G{i}" for i in range(n_genes)] + curated
    ad = [f"AD_{i}" for i in range(n_ad)]
    cn = [f"CN_{i}" for i in range(n_cn)]
    X = rng.lognormal(0, 1.4, size=(len(genes), n_ad + n_cn))
    df = pd.DataFrame(X, index=genes, columns=ad + cn)
    for g in ["APP", "BACE1", "IL1B", "TNF", "IL6", "TYROBP", "TREM2", "APOE", "HMOX1", "GFAP", "CSF1R"]:
        df.loc[g, ad] *= 4.0
    for g in ["MTOR", "BECN1"]:
        df.loc[g, ad] *= 0.4
    meta = pd.DataFrame({"group": ["AD"] * n_ad + ["CN"] * n_cn,
                         "batch": ["B1"] * (n_ad // 2) + ["B2"] * (n_ad // 2) + ["B1"] * (n_cn // 2) + ["B2"] * (n_cn // 2)},
                        index=df.columns)
    return df, meta


@pytest.fixture()
def synthetic_omics(tmp_path) -> tuple[Path, Path]:
    df, meta = make_synthetic_expression()
    mat_path = tmp_path / "expression.csv"
    meta_path = tmp_path / "metadata.csv"
    df.to_csv(mat_path)
    meta.to_csv(meta_path)
    return mat_path, meta_path
