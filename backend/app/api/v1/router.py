"""Aggregated API v1 router."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

api_router = APIRouter(prefix=settings.API_V1_PREFIX)

from app.api.v1 import admin, analyses, assistant, auth, causal, datasets, drugs, health, ml, omics, projects, reports  # noqa: E402

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(datasets.router)
api_router.include_router(analyses.router)
api_router.include_router(omics.router)
api_router.include_router(ml.router)
api_router.include_router(drugs.router)
api_router.include_router(causal.router)
api_router.include_router(reports.router)
api_router.include_router(assistant.router)
api_router.include_router(admin.router)
