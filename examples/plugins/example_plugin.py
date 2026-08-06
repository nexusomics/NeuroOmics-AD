"""Example NeuroOmics-AD plugin: adds a trivial 'gene_summary' analysis type.

Enable with:  PLUGINS=examples.plugins.example_plugin
"""
from __future__ import annotations

from app.plugins.base import AnalysisPlugin


class GeneSummaryPlugin(AnalysisPlugin):
    analysis_type = "gene_summary"

    def run(self, config: dict, artifacts: dict) -> dict:
        genes = [g.upper() for g in config.get("gene_list", [])]
        # count how many curated AD risk genes are present
        from app.drugs.knowledge import CURATED_AD_RISK_GENES

        hits = sorted(set(genes) & set(CURATED_AD_RISK_GENES))
        return {
            "table": [{"gene": g, "curated_ad_risk": g in CURATED_AD_RISK_GENES} for g in genes],
            "summary": {
                "n_genes": len(genes),
                "n_curated_ad_risk_genes": len(hits),
                "curated_hits": hits,
                "plugin": self.manifest.name,
            },
        }
