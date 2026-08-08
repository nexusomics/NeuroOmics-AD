"""Causal multi-omics module package.

NOTE: `run_causal_pipeline` is imported lazily (inside the endpoint) so that
importing this package at app startup does NOT pull in scikit-learn/scipy/
networkx — keeping first-boot fast enough for free-tier hosts (e.g. Render's
0.1-CPU instances) to pass the health check within the grace period.
"""
from app.causal.catalog import Catalog, RESOURCES, catalog

__all__ = ["Catalog", "RESOURCES", "catalog"]


def run_causal_pipeline(*args, **kwargs):
    from app.causal.pipeline import run_causal_pipeline as _run

    return _run(*args, **kwargs)
