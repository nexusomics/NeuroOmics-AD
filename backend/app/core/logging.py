"""Structured logging configuration."""
from __future__ import annotations

import logging
import sys

from app.core.config import settings

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO), handlers=handlers)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("rpy2").setLevel(logging.CRITICAL)  # R lifecycle noise
    logging.getLogger("rpy2.rinterface_lib.embedded").disabled = True
    logging.getLogger("rpy2.situation").disabled = True
