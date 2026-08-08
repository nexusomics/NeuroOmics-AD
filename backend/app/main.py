"""NeuroOmics-AD — FastAPI application factory."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    configure_logging()
    init_db()
    _load_plugins()
    _ensure_admin_user()
    _seed_demo_content()
    logger.info("NeuroOmics-AD %s started (env=%s)", __version__, settings.ENVIRONMENT)
    yield


def _seed_demo_content() -> None:
    """Create the demo project + synthetic datasets on ANY database, once.

    On hosts with ephemeral storage (Render free tier uses SQLite on a
    container disk that resets on redeploy), this guarantees the dashboard
    always shows the demo project with data immediately after login, instead
    of an empty workspace.
    """
    try:
        import numpy as np
        import pandas as pd

        from app.core.database import SessionLocal
        from app.core.security import hash_password
        from app.models.dataset import Dataset
        from app.models.project import Project
        from app.models.user import User

        db = SessionLocal()
        try:
            demo_user = db.query(User).filter(User.email == "demo@neuroomics.org").first()
            if demo_user is None:
                demo_user = User(email="demo@neuroomics.org", full_name="Demo Researcher",
                                 hashed_password=hash_password("demo12345"), role="researcher",
                                 organization="NeuroOmics Demo Lab", is_verified=True)
                db.add(demo_user)
                db.commit()
                db.refresh(demo_user)
            project = db.query(Project).filter(Project.owner_id == demo_user.id).first()
            if project is not None:
                return  # already seeded
            project = Project(name="ROSMAP-style AD multi-omics demo",
                              description="Synthetic multi-omics dataset emulating an AD vs CN cohort for end-to-end platform demos.",
                              disease="Alzheimer's disease", owner_id=demo_user.id)
            db.add(project)
            db.commit()
            db.refresh(project)

            rng = np.random.default_rng(2026)
            curated = ["APP", "BACE1", "PSEN1", "APOE", "TREM2", "TYROBP", "MAPT", "GSK3B",
                       "IL1B", "TNF", "IL6", "CLU", "SORL1", "HMOX1", "MTOR", "BECN1", "GFAP", "CSF1R"]
            genes = [f"GENE{i:04d}" for i in range(1, 220)] + curated
            ad = [f"AD_{i:03d}" for i in range(20)]
            cn = [f"CN_{i:03d}" for i in range(20)]
            X = rng.lognormal(0, 1.3, size=(len(genes), 40))
            expr = pd.DataFrame(X, index=genes, columns=ad + cn)
            for g in ["APP", "BACE1", "IL1B", "TNF", "IL6", "TYROBP", "TREM2", "APOE", "HMOX1", "GFAP"]:
                expr.loc[g, ad] *= 4.0
            for g in ["MTOR", "BECN1"]:
                expr.loc[g, ad] *= 0.4
            meta = pd.DataFrame({"group": ["AD"] * 20 + ["CN"] * 20,
                                 "batch": ["B1", "B2"] * 10 + ["B1", "B2"] * 10}, index=expr.columns)

            from app.utils.files import save_upload

            import io

            def _write_df(df, name):
                buf = io.StringIO()
                df.to_csv(buf)
                path, _ = save_upload(buf.getvalue().encode(), name, subdir="demo")
                return str(path)

            expr_path = _write_df(expr, "transcriptomics_expression.csv")
            meta_path = _write_df(meta, "transcriptomics_metadata.csv")
            db.add(Dataset(project_id=project.id, name="RNA-seq expression (bulk)", omics_type="transcriptomics",
                           platform="Illumina HiSeq", file_path=expr_path, format="csv",
                           n_samples=expr.shape[1], n_features=expr.shape[0], status="ready", uploaded_by=demo_user.id,
                           metadata_json={"metadata_file": meta_path, "source": "synthetic"}))
            prot = pd.DataFrame(rng.lognormal(0, 0.8, size=(80, 40)), index=[f"P{i:04d}" for i in range(80)], columns=expr.columns)
            for g in ["GFAP", "NEFL", "CLU", "CFH", "B2M", "APOD", "TREM2", "IL6"]:
                if g not in prot.index:
                    continue
                prot.loc[g, ad] *= 2.0
            prot_path = _write_df(prot, "proteomics.csv")
            db.add(Dataset(project_id=project.id, name="Plasma proteomics (SomaScan-like)", omics_type="proteomics",
                           platform="SomaScan 7K", file_path=prot_path, format="csv",
                           n_samples=prot.shape[1], n_features=prot.shape[0], status="ready", uploaded_by=demo_user.id,
                           metadata_json={"metadata_file": meta_path, "source": "synthetic"}))
            met = pd.DataFrame(rng.lognormal(0, 0.7, size=(60, 40)), index=[f"M{i:04d}" for i in range(60)], columns=expr.columns)
            met_path = _write_df(met, "metabolomics.csv")
            db.add(Dataset(project_id=project.id, name="Serum metabolomics (NMR)", omics_type="metabolomics",
                           platform="NMR", file_path=met_path, format="csv",
                           n_samples=met.shape[1], n_features=met.shape[0], status="ready", uploaded_by=demo_user.id,
                           metadata_json={"metadata_file": meta_path, "source": "synthetic"}))
            db.commit()
            logger.info("seeded demo project '%s' with 3 synthetic datasets", project.name)
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("demo-content seeding skipped: %s", exc)


def _load_plugins() -> None:
    from app.plugins.base import registry

    if settings.PLUGINS:
        registry.load(settings.PLUGINS)
        logger.info("loaded %d plugin(s)", len(registry.plugins))


def _ensure_admin_user() -> None:
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.role == "admin").first():
            admin = User(
                email=settings.ADMIN_EMAIL,
                full_name="Platform Administrator",
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
                is_verified=True,
            )
            db.add(admin)
            db.commit()
            logger.info("created default admin user")
        # Demo researcher account — created on ANY database (local + Render) so
        # the documented demo login works everywhere.
        if settings.ENVIRONMENT != "production" or os.environ.get("SEED_DEMO_USER", "true").lower() == "true":
            if not db.query(User).filter(User.email == "demo@neuroomics.org").first():
                db.add(User(
                    email="demo@neuroomics.org",
                    full_name="Demo Researcher",
                    hashed_password=hash_password("demo12345"),
                    role="researcher",
                    organization="NeuroOmics Demo Lab",
                    is_verified=True,
                ))
                db.commit()
                logger.info("created demo user (demo@neuroomics.org / demo12345)")
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not ensure admin/demo users: %s", exc)
    finally:
        db.close()


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="NeuroOmics-AD API",
        description=(
            "AI-driven multi-omics platform for Alzheimer's disease research: data harmonization, "
            "differential expression, meta-analysis, deconvolution, enrichment, network medicine, "
            "machine learning (RF/XGBoost/SVM/DNN/GNN), drug repurposing and automated reporting. "
            "See docs/architecture.md for details."
        ),
        version=__version__,
        openapi_tags=[
            {"name": "authentication", "description": "Register, login, tokens, profile"},
            {"name": "projects", "description": "Project management & membership"},
            {"name": "datasets", "description": "Multi-omics dataset upload & inspection"},
            {"name": "analyses", "description": "Analysis runs (Celery-backed), artifacts, results"},
            {"name": "omics", "description": "Direct omics analysis endpoints"},
            {"name": "machine-learning", "description": "RF / XGBoost / SVM / DNN / GNN training"},
            {"name": "drug-repurposing", "description": "Drug pipeline, candidates, combinations, knowledge base"},
            {"name": "reports", "description": "PDF / DOCX / PPTX / XLSX / CSV / HTML reports"},
            {"name": "ai-assistant", "description": "AI research assistant & manuscript drafting"},
            {"name": "admin", "description": "Platform administration"},
            {"name": "system", "description": "Health & info"},
        ],
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # routers
    from app.api.v1.router import api_router

    app.include_router(api_router)

    # --- static frontend (single-service deployment) ---
    # When `frontend/dist` exists (production build), serve the SPA from the
    # same process — enables one-service deploys (Render/Railway/VPS).
    _mount_frontend(app)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "type": type(exc).__name__})

    @app.get("/", include_in_schema=False)
    def root() -> Any:
        # In production the compiled SPA is served at "/" (login page);
        # in dev (no dist) we return a small JSON pointer instead.
        from fastapi.responses import FileResponse

        dist = _find_frontend_dist()
        if dist is not None:
            return FileResponse(dist / "index.html")
        return {"app": settings.APP_NAME, "version": __version__, "docs": "/docs", "health": "/api/v1/health"}

    return app


def _find_frontend_dist() -> Optional[Path]:
    """Locate the compiled SPA across supported layouts.

    Local repo layout:   <repo>/backend/app/main.py -> <repo>/frontend/dist
    Container layout:    /app/app/main.py          -> /app/frontend/dist
    Override:            FRONTEND_DIST_PATH env var
    """
    import os
    from pathlib import Path

    override = os.environ.get("FRONTEND_DIST_PATH")
    if override:
        p = Path(override)
        if (p / "index.html").exists():
            return p
    base = Path(__file__).resolve().parent.parent
    for candidate in (base / "frontend" / "dist", base.parent / "frontend" / "dist"):
        if (candidate / "index.html").exists():
            return candidate
    return None


def _mount_frontend(app: FastAPI) -> None:
    """Serve the compiled React app from `frontend/dist` when present (SPA fallback)."""
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    dist = _find_frontend_dist()
    if dist is None:
        return

    assets = dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):  # noqa: ANN001
        # API routes are matched first (registered earlier); anything left is SPA.
        candidate = (dist / full_path).resolve()
        try:
            candidate.relative_to(dist.resolve())
        except ValueError:
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})
        if candidate.is_file():
            headers = {"Cache-Control": "no-cache"}
            name = candidate.name
            if name.startswith("index.") and len(name.split(".")) >= 3:
                headers = {"Cache-Control": "public, max-age=31536000, immutable"}
            return FileResponse(candidate, headers=headers)
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})


app = create_app()


def run() -> None:  # pragma: no cover - CLI entrypoint
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)


if __name__ == "__main__":
    run()
