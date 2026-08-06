"""Celery application factory for background analysis tasks."""
from __future__ import annotations

from celery import Celery
from celery.signals import worker_process_init

from app.core.config import settings

celery_app = Celery(
    "neuroomics",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 60 * 4,  # 4 h hard limit
    task_soft_time_limit=60 * 60 * 3,
    broker_connection_retry_on_startup=True,
    result_expires=60 * 60 * 24 * 7,
    task_default_queue="analysis",
    task_routes={
        "app.workers.tasks.run_analysis_task": {"queue": "analysis"},
        "app.workers.tasks.run_drug_pipeline_task": {"queue": "drugs"},
        "app.workers.tasks.generate_report_task": {"queue": "reports"},
    },
    worker_hijack_root_logger=False,
    worker_log_format="%(asctime)s | %(levelname)-8s | %(message)s",
)

# Eager mode: execute tasks synchronously in-process (dev without a broker).
if settings.TASK_ALWAYS_EAGER:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


@worker_process_init.connect
def _seed_random(**_):  # noqa: ANN001
    import random

    import numpy as np

    random.seed(settings.RANDOM_SEED)
    np.random.seed(settings.RANDOM_SEED)
