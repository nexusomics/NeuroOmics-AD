"""rpy2 bridge with automatic availability detection and graceful degradation.

The platform prefers R + Bioconductor (DESeq2 / limma / sva / WGCNA) when the
packages are installed (e.g. in the production Docker image). When they are not
available, equivalent pure-Python implementations in `app.services` are used so
the platform remains fully functional in constrained environments.
"""
from __future__ import annotations

import logging
import shutil
from functools import lru_cache
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def r_available() -> bool:
    """Whether R and rpy2 are importable."""
    if shutil.which("R") is None:
        return False
    try:
        import rpy2  # noqa: F401
        import rpy2.robjects as ro  # noqa: F401

        return True
    except Exception as exc:  # noqa: BLE001
        logger.info("rpy2 import failed: %s", exc)
        return False


def r_import_available() -> bool:
    if not r_available():
        return False
    try:
        import rpy2.robjects as ro
        from rpy2.robjects.packages import importr

        base = importr("base")
        return bool(base.require("limma", quietly=True)[0])
    except Exception:  # noqa: BLE001
        return False


@lru_cache(maxsize=1)
def available_r_packages() -> set[str]:
    if not r_available():
        return set()
    try:
        import rpy2.robjects as ro

        pkgs = ro.r("rownames(installed.packages())")
        return set(pkgs)
    except Exception:  # noqa: BLE001
        return set()


def has_package(name: str) -> bool:
    return name in available_r_packages()


def run_r_script(script: str, inputs: Optional[dict[str, Any]] = None) -> Any:
    """Execute an R script with optional named variables injected; returns last expression value."""
    import rpy2.robjects as ro

    env = ro.globalenv
    if inputs:
        for k, v in inputs.items():
            env[k] = v
    return ro.r(script)


def with_r_or_python(r_func: Callable[[], Any], py_func: Callable[[], Any]) -> Any:
    """Run the R implementation if available, else the Python fallback."""
    if r_available():
        try:
            return r_func()
        except Exception as exc:  # noqa: BLE001
            logger.warning("R execution failed (%s); falling back to Python pipeline.", exc)
    return py_func()
