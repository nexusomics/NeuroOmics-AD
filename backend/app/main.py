"""NeuroOmics-AD — FastAPI application factory."""
from __future__ import annotations

import logging
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
    logger.info("NeuroOmics-AD %s started (env=%s)", __version__, settings.ENVIRONMENT)
    yield


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
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not ensure admin user: %s", exc)
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
            return FileResponse(dist / "index.html")
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")


app = create_app()


def run() -> None:  # pragma: no cover - CLI entrypoint
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)


if __name__ == "__main__":
    run()
