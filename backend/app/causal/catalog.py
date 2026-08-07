"""Harmonized AD resource catalog — unified, queryable schema.

Maps the newly available high-dimensional AD resources (Knight-ADRC/WashU,
ADSP R4, AMP-AD multi-ethnic, plasma multi-omics across ancestries) into a
single sample-level schema: cohort, accession, modality, ancestry, brain
region, biofluid, phenotype. A precomputed in-memory index (numpy/pandas)
answers complex multi-layer queries in milliseconds and powers the portal's
query builder. Real deployments swap the synthetic index for Parquet-backed
harmonized tables (see docs/causal-module-spec.md §Data).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ResourceEntry:
    accession: str
    name: str
    cohort: str
    modalities: list[str]
    ancestries: list[str]
    brain_regions: list[str]
    biofluids: list[str]
    phenotypes: list[str]
    n_samples: int
    citation: str
    publication_status: str = "published"
    mined_depth: str = "partial"  # partial | extensive | not-yet-mined
    notes: str = ""


# Real resources, grounded in the August-2026 literature scan.
RESOURCES: list[ResourceEntry] = [
    ResourceEntry("NG00083", "Circular RNAs in AD brains (Knight-ADRC)", "Knight-ADRC (WashU)",
                  ["transcriptomics"], ["EUR", "AA"], ["DLPFC", "STG"], ["brain"],
                  ["diagnosis", "Braak", "CERAD"], 320, "Knight ADRC / NIAGADS DSS",
                  mined_depth="not-yet-mined", notes="circRNA layer rarely integrated cross-modally"),
    ResourceEntry("NG00102", "Knight-ADRC brain/CSF/plasma multi-omics", "Knight-ADRC (WashU)",
                  ["transcriptomics", "proteomics", "metabolomics", "lipidomics", "methylation"],
                  ["EUR", "AA"], ["DLPFC", "STG", "PCC", "HC"], ["brain", "CSF", "plasma"],
                  ["diagnosis", "Braak", "CERAD", "age_at_onset", "CDR"], 950,
                  "Knight ADRC (sa000031; Deming et al. pQTL/mQTL)"),
    ResourceEntry("NG00113", "Knight-ADRC snRNA-seq (brain)", "Knight-ADRC (WashU)",
                  ["single_cell"], ["EUR"], ["DLPFC", "PCC"], ["brain"],
                  ["diagnosis", "Braak", "CERAD"], 210, "Knight ADRC (SEA-AD style)"),
    ResourceEntry("NG00114", "Knight-ADRC plasma multi-omics (EUR+AFR)", "Knight-ADRC (WashU)",
                  ["proteomics", "metabolomics", "lipidomics", "transcriptomics"], ["EUR", "AA"],
                  [], ["plasma"], ["diagnosis", "CDR", "age"], 1600,
                  "Knight ADRC (sa000074; plasma pQTL/mQTL EUR+AFR)"),
    ResourceEntry("NG00108", "Knight-ADRC longitudinal plasma/cognition", "Knight-ADRC (WashU)",
                  ["proteomics", "metabolomics", "clinical"], ["EUR", "AA"], [], ["plasma"],
                  ["diagnosis", "CDR", "MMSE", "rate_of_decline"], 1800,
                  "Knight ADRC (sa000052; cfRNA; MAP longitudinal)"),
    ResourceEntry("NG00067", "ADSP R4 whole-genome sequencing (36,361 WGS)", "ADSP (17 cohorts/14 countries)",
                  ["genomics"], ["EUR", "AA", "LA", "EAS", "AMR"], [], [],
                  ["diagnosis", "age_at_onset", "APOE"], 36361,
                  "Kunkle et al. 2025; Alz&Dementia 2025; GCAD pipeline",
                  mined_depth="extensive", notes="TWAS/PWAS integrated in 2025 (PMC12614089)"),
    ResourceEntry("AMP-AD-DIV", "AMP-AD multi-ethnic brain multi-omics (Diversity Initiative)", "AMP-AD Diversity WG",
                  ["genomics", "transcriptomics", "proteomics", "methylation"], ["AA", "LA", "EUR"],
                  ["DLPFC", "STG", "PCC"], ["brain"], ["diagnosis", "Braak", "CERAD", "race"], 908,
                  "Bridging the Gap, Alz&Dementia 2024 (n=306 AA, 326 LA, 252 NHW)"),
    ResourceEntry("PLASMA-XANC", "Plasma multi-omics across ancestries (EUR+AFR xQTL)", "Multi-cohort (Knight-ADRC + partners)",
                  ["proteomics", "metabolomics"], ["EUR", "AA"], [], ["plasma"],
                  ["diagnosis", "AD_risk"], 4100,
                  "Alzheimer's & Dementia 2026 (alz.71164): 61-83% of findings previously unreported",
                  mined_depth="partial", notes="21 shared proteins; IL-1 & lipid pathways"),
]

MODALITIES = sorted({m for r in RESOURCES for m in r.modalities})
ANCESTRIES = sorted({a for r in RESOURCES for a in r.ancestries})
REGIONS = sorted({rg for r in RESOURCES for rg in r.brain_regions})
BIOFLUIDS = sorted({b for r in RESOURCES for b in r.biofluids})
PHENOTYPES = sorted({p for r in RESOURCES for p in r.phenotypes})


class Catalog:
    """Queryable harmonized catalog with a precomputed sample-level index."""

    def __init__(self, resources: Optional[list[ResourceEntry]] = None) -> None:
        self.resources = resources or RESOURCES
        self._index = self._build_index()

    def _build_index(self) -> pd.DataFrame:
        rows = []
        for r in self.resources:
            n = r.n_samples
            for i in range(n):
                rows.append({
                    "sample_id": f"{r.accession}-{i:06d}",
                    "cohort": r.cohort,
                    "accession": r.accession,
                    "ancestry": r.ancestries[i % len(r.ancestries)],
                    "modality": r.modalities[i % len(r.modalities)],
                    "brain_region": r.brain_regions[i % len(r.brain_regions)] if r.brain_regions else "",
                    "biofluid": r.biofluids[i % len(r.biofluids)] if r.biofluids else "",
                    "diagnosis": np.random.default_rng(i).choice(["AD", "MCI", "CN"]),
                })
        return pd.DataFrame(rows)

    def query(
        self,
        cohorts: Optional[list[str]] = None,
        accessions: Optional[list[str]] = None,
        modalities: Optional[list[str]] = None,
        ancestries: Optional[list[str]] = None,
        brain_regions: Optional[list[str]] = None,
        biofluids: Optional[list[str]] = None,
        phenotypes: Optional[list[str]] = None,
        diagnosis: Optional[str] = None,
    ) -> dict:
        """Multi-layer filter query → sample counts + harmonized overview."""
        t0 = time.perf_counter()
        df = self._index
        if cohorts:
            df = df[df["cohort"].isin(cohorts)]
        if accessions:
            df = df[df["accession"].isin(accessions)]
        if modalities:
            df = df[df["modality"].isin(modalities)]
        if ancestries:
            df = df[df["ancestry"].isin(ancestries)]
        if brain_regions:
            df = df[df["brain_region"].isin(brain_regions)]
        if biofluids:
            df = df[df["biofluid"].isin(biofluids)]
        if phenotypes:
            # resource-level phenotype availability
            ok_acc = [r.accession for r in self.resources if set(phenotypes) & set(r.phenotypes)]
            df = df[df["accession"].isin(ok_acc)]
        if diagnosis:
            df = df[df["diagnosis"] == diagnosis]
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return {
            "n_samples": int(len(df)),
            "n_datasets": int(df["accession"].nunique()),
            "by_ancestry": df["ancestry"].value_counts().to_dict(),
            "by_modality": df["modality"].value_counts().to_dict(),
            "by_region": {k: v for k, v in df["brain_region"].value_counts().to_dict().items() if k},
            "by_biofluid": {k: v for k, v in df["biofluid"].value_counts().to_dict().items() if k},
            "query_time_ms": round(elapsed_ms, 2),
            "sample_head": df.head(10).to_dict(orient="records"),
        }

    def resource_table(self) -> list[dict]:
        return [r.__dict__ for r in self.resources]

    def stats(self) -> dict:
        return {
            "n_resources": len(self.resources),
            "n_indexed_samples": int(len(self._index)),
            "modalities": MODALITIES,
            "ancestries": ANCESTRIES,
            "regions": REGIONS,
            "biofluids": BIOFLUIDS,
            "phenotypes": PHENOTYPES,
        }


catalog = Catalog()
