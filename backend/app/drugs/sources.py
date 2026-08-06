"""Drug data-source adapters.

Adapters for DrugBank, ChEMBL, DGIdb, Open Targets, LINCS and Connectivity Map.
Live API calls are best-effort and controlled by `DRUG_ENABLE_LIVE_API`; when
disabled or unreachable, adapters return empty results and the curated
knowledge base (`knowledge.py`) is used instead. All results are cached.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.redis import cache

logger = logging.getLogger(__name__)


class BaseSource:
    name = "base"

    def fetch(self, genes: list[str], drugs: list[dict]) -> list[dict]:
        raise NotImplementedError


class ChEMBLSource(BaseSource):
    """ChEMBL REST API: mechanism-of-action & target annotations per drug."""

    name = "chembl"
    base = "https://www.ebi.ac.uk/chembl/api/data"

    def fetch(self, genes: list[str], drugs: list[dict]) -> list[dict]:
        if not settings.DRUG_ENABLE_LIVE_API:
            return []
        out = []
        try:
            with httpx.Client(timeout=settings.DRUG_API_TIMEOUT) as client:
                for drug in drugs:
                    key = f"chembl:{drug['name'].lower()}"
                    cached = cache.get(key)
                    if cached is not None:
                        out.extend(cached)
                        continue
                    r = client.get(f"{self.base}/molecule/search.json", params={"q": drug["name"]})
                    if r.status_code != 200:
                        continue
                    hits = r.json().get("molecules", [])
                    if hits:
                        out.append({"source": self.name, "drug": drug["name"], "chembl_id": hits[0].get("molecule_chembl_id", "")})
                    cache.set(key, out[-1:] if out else [], ttl=86400)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ChEMBL unavailable: %s", exc)
        return out


class DGIdbSource(BaseSource):
    """DGIdb (Drug Gene Interaction Database) REST API."""

    name = "dgidb"
    base = "https://dgidb.org/api/v2"

    def fetch(self, genes: list[str], drugs: list[dict]) -> list[dict]:
        if not settings.DRUG_ENABLE_LIVE_API:
            return []
        out = []
        try:
            with httpx.Client(timeout=settings.DRUG_API_TIMEOUT) as client:
                for gene in genes[:20]:
                    key = f"dgidb:{gene}"
                    cached = cache.get(key)
                    if cached is not None:
                        out.extend(cached)
                        continue
                    r = client.post(f"{self.base}/interactions.json", json={"genes": [gene]})
                    if r.status_code != 200:
                        continue
                    rows = []
                    for match in r.json().get("matchedTerms", []):
                        for interaction in match.get("interactions", []):
                            rows.append({
                                "source": self.name, "gene": gene,
                                "drug": interaction.get("drugName", ""),
                                "interaction_type": interaction.get("interactionTypes", []),
                            })
                    out.extend(rows)
                    cache.set(key, rows, ttl=86400)
        except Exception as exc:  # noqa: BLE001
            logger.warning("DGIdb unavailable: %s", exc)
        return out


class OpenTargetsSource(BaseSource):
    """Open Targets Platform GraphQL API: disease–target–drug associations."""

    name = "open_targets"
    endpoint = "https://platform-api.opentargets.org/v4/graphql"

    def fetch(self, genes: list[str], drugs: list[dict]) -> list[dict]:
        if not settings.DRUG_ENABLE_LIVE_API:
            return []
        out = []
        try:
            with httpx.Client(timeout=settings.DRUG_API_TIMEOUT) as client:
                for gene in genes[:10]:
                    query = """
                    query($gene: String!) {
                      target(ensemblId: $gene) {
                        approvedSymbol
                        knownDrugs(size: 10) { rows { drug { name } mechanismOfAction } }
                      }
                    }
                    """
                    r = client.post(self.endpoint, json={"query": query, "variables": {"gene": gene}})
                    if r.status_code != 200:
                        continue
                    data = r.json().get("data", {}).get("target")
                    if not data:
                        continue
                    for row in data.get("knownDrugs", {}).get("rows", []):
                        out.append({"source": self.name, "gene": gene,
                                    "drug": row.get("drug", {}).get("name", ""),
                                    "mechanism": row.get("mechanismOfAction", "")})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Open Targets unavailable: %s", exc)
        return out


class DrugBankSource(BaseSource):
    """DrugBank full-database XML (requires `DRUG_DATABANK_XML_PATH`)."""

    name = "drugbank"

    def fetch(self, genes: list[str], drugs: list[dict]) -> list[dict]:
        path = settings.DRUG_DATABANK_XML_PATH
        if not path:
            return []
        try:
            import xml.etree.ElementTree as ET

            ns = {"db": "http://www.drugbank.ca"}
            tree = ET.parse(path)
            out = []
            for drug_el in tree.getroot().findall("db:drug", ns):
                name_el = drug_el.find("db:name", ns)
                name = name_el.text if name_el is not None else ""
                targets = []
                for target in drug_el.findall("db:targets/db:target/db:polypeptide", ns):
                    gene_el = target.find("db:gene-name", ns)
                    if gene_el is not None and gene_el.text:
                        targets.append(gene_el.text.upper())
                if targets:
                    out.append({"source": self.name, "drug": name, "targets": targets})
            return out
        except Exception as exc:  # noqa: BLE001
            logger.warning("DrugBank XML parse failed: %s", exc)
            return []


class LINCSSource(BaseSource):
    """LINCS L1000 / Connectivity Map signature files (CSV of gene→LFC per compound).

    Expects a directory `data/lincs` with `compound_signatures.csv`:
    columns: perturbagen, gene, logfoldchange
    """

    name = "lincs"

    def fetch(self, genes: list[str], drugs: list[dict]) -> list[dict]:
        import pandas as pd
        from pathlib import Path

        p = Path("data/lincs/compound_signatures.csv")
        if not p.exists():
            return []
        try:
            df = pd.read_csv(p)
            out = []
            for _, row in df.iterrows():
                out.append({"source": self.name, "perturbagen": row["perturbagen"],
                            "gene": row["gene"], "logfoldchange": float(row["logfoldchange"])})
            return out
        except Exception as exc:  # noqa: BLE001
            logger.warning("LINCS data unavailable: %s", exc)
            return []


class CMapSource(BaseSource):
    """Connectivity Map style signatures (same format as LINCS adapter)."""

    name = "cmap"

    def fetch(self, genes: list[str], drugs: list[dict]) -> list[dict]:
        from pathlib import Path

        p = Path("data/cmap/cmap_signatures.csv")
        if not p.exists():
            return []
        try:
            import pandas as pd

            df = pd.read_csv(p)
            out = []
            for _, row in df.iterrows():
                out.append({"source": self.name, "perturbagen": row["perturbagen"],
                            "gene": row["gene"], "logfoldchange": float(row["logfoldchange"])})
            return out
        except Exception as exc:  # noqa: BLE001
            logger.warning("CMap data unavailable: %s", exc)
            return []


ALL_SOURCES: dict[str, BaseSource] = {
    "chembl": ChEMBLSource(),
    "dgidb": DGIdbSource(),
    "open_targets": OpenTargetsSource(),
    "drugbank": DrugBankSource(),
    "lincs": LINCSSource(),
    "cmap": CMapSource(),
}


def fetch_sources(genes: list[str], drugs: list[dict], sources: Optional[list[str]] = None) -> list[dict]:
    """Fetch annotations from the requested sources (empty list when offline)."""
    if not sources:
        sources = list(ALL_SOURCES)
    out = []
    for name in sources:
        src = ALL_SOURCES.get(name)
        if not src:
            continue
        try:
            out.extend(src.fetch(genes, drugs))
        except Exception as exc:  # noqa: BLE001
            logger.warning("source %s failed: %s", name, exc)
    return out
