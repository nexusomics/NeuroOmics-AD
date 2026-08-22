# External Data Sources (Associated Databases)

This page is the single registry of every **external database / data source**
NeuroOmics-AD integrates with, how each one is wired into the platform, and how
to enable & verify it.

> **Quick check** — `python scripts/verify_databases.py` probes every source
> below (reachability of live APIs + presence of local data files) and prints a
> status report. `--json` gives a machine-readable report.

## Overview

| Source | Category | Kind | Used for | Enabled by |
|---|---|---|---|---|
| ChEMBL | Drug–target | Live REST | Mechanism-of-action & target annotations | `DRUG_ENABLE_LIVE_API=true` |
| Open Targets Platform | Drug–target | Live GraphQL | Disease–target–drug associations | `DRUG_ENABLE_LIVE_API=true` |
| DGIdb | Drug–target | Live REST | Drug–gene interactions | `DRUG_ENABLE_LIVE_API=true` |
| DrugBank | Drug–target | Local XML | Drug→target relationships (licensed) | `DRUG_DATABANK_XML_PATH` |
| LINCS L1000 | Drug–target | Local CSV | Pathway-reversal signatures | `LINCS_SIGNATURES_PATH` |
| Connectivity Map | Drug–target | Local CSV | Pathway-reversal signatures | `CMAP_SIGNATURES_PATH` |
| Enrichr (GO/KEGG/Reactome) | Pathway | Live REST | Gene-set enrichment | automatic (gseapy) |
| KEGG REST | Pathway | Live REST | Pathway definitions/metadata | optional |
| STRING | PPI network | Live TSV API | PPI edges (full interactome) | optional (built-in skeleton default) |
| BioGRID | PPI network | Portal | Curated interactions (alternative) | optional |
| ClinicalTrials.gov | Clinical | Live REST v2 | Trial count / status evidence | optional (`CLINICALTRIALS_API_KEY`) |
| NIAGADS DSS | AD cohorts | Portal | Knight-ADRC & ADSP R4 accessions | catalog metadata |
| AD Knowledge Portal | AD cohorts | Portal | AMP-AD multi-ethnic cohorts | catalog metadata |
| AMP-AD Agora | AD cohorts | Live REST | AD target-gene nominations | catalog metadata |
| Alzheimer DataLENS | AD cohorts | Portal | Harmonized AD omics queries | frontend deep-link |
| ONTIME QTL browser | AD cohorts | Portal | Knight-ADRC pQTL/mQTL atlas | frontend deep-link |

## Drug–target & repurposing sources

Wired in `backend/app/drugs/sources.py` (adapters) and consumed by
`backend/app/drugs/pipeline.py`. All live calls are **best-effort** — when
`DRUG_ENABLE_LIVE_API=false` or the endpoint is unreachable, the adapters
return empty results and the curated knowledge base
(`backend/app/drugs/knowledge.py`, ~70 AD-relevant drugs) keeps the pipeline
fully functional offline. Results are cached in Redis for 24 h.

| Source | Endpoint | Notes |
|---|---|---|
| **ChEMBL** | `https://www.ebi.ac.uk/chembl/api/data/molecule/search.json?q=<drug>` | Open (CC BY-SA). Molecule search by name. |
| **Open Targets** | `https://platform-api.opentargets.org/v4/graphql` | GraphQL `target(ensemblId)` → `knownDrugs`. |
| **DGIdb** | `https://dgidb.org/api/v2/interactions.json?genes=<symbol>` | Prefer GET; POST accepted for large lists. |
| **DrugBank** | local XML (see below) | Licensed — academic/commercial, not redistributable. |
| **LINCS L1000** | local CSV (see below) | Level-5 signatures from CLUE.io / SigCom LINCS. |
| **Connectivity Map** | local CSV (see below) | Same schema as LINCS; Broad CMap / GEO. |

### Local data files

```
backend/
└── data/                 # git-ignored by design (never commit omics data)
    ├── drugbank/
    │   └── full_database.xml              # DRUG_DATABANK_XML_PATH
    ├── lincs/
    │   └── compound_signatures.csv        # LINCS_SIGNATURES_PATH
    └── cmap/
        └── cmap_signatures.csv            # CMAP_SIGNATURES_PATH
```

Signature CSV schema (long format, one row per perturbagen×gene):

```
perturbagen,gene,logfoldchange
trichostatin-a,APP,-0.42
trichostatin-a,BACE1,-0.31
```

Each directory contains a `README.md` with download instructions. Relative
paths are resolved against the `backend/` directory; absolute paths also work.

Enable the live adapters in `backend/.env` (created from `.env.example`):

```ini
DRUG_ENABLE_LIVE_API=true
DRUG_API_TIMEOUT=15
DRUG_DATABANK_XML_PATH=data/drugbank/full_database.xml
LINCS_SIGNATURES_PATH=data/lincs/compound_signatures.csv
CMAP_SIGNATURES_PATH=data/cmap/cmap_signatures.csv
```

## Pathway & gene-set enrichment

Wired in `backend/app/services/enrichment.py`.

1. **Live path** — `gseapy.enrichr` queries the Enrichr API
   (`https://maayanlab.cloud/Enrichr/`) with library names such as
   `GO_Biological_Process_2023`, `KEGG_2021_Human`, `Reactome_2022`,
   `MSigDB_Hallmark_2020`.
2. **Offline fallback** — a built-in curated AD gene-set library
   (`GO/KEGG/Reactome` terms) with exact hypergeometric enrichment + BH-FDR,
   used automatically when Enrichr is unreachable.

- **KEGG REST** (`https://rest.kegg.jp/`) is available for pathway metadata
  (e.g. `list/hsa05010` = Alzheimer's disease pathway).

## Protein–protein interaction networks

Wired in `backend/app/services/network.py`. The platform ships a compact
STRING-style AD PPI skeleton so analysis works offline; production deployments
can load full **STRING** (`https://string-db.org/`) or **BioGRID**
(`https://thebiogrid.org/`) edge-list exports into the same graph builder.

## Clinical evidence

**ClinicalTrials.gov API v2** (`https://clinicaltrials.gov/api/v2/studies`) is
used for trial-count / status evidence in drug ranking. No key is required for
the public API; set `CLINICALTRIALS_API_KEY` if you have one.

## AD genomics / cohort portals

These are the harmonized data resources mapped in the causal multi-omics module
(`backend/app/causal/catalog.py`, see
[`causal-module-spec.md`](causal-module-spec.md)). The platform ships real
resource metadata (accessions, sample counts, citations) and links out to the
portals for data access:

| Portal | URL | Cohorts / accessions referenced |
|---|---|---|
| **NIAGADS DSS** | `https://dss.niagads.org/` | Knight-ADRC (NG00083, NG00102, NG00108, NG00113, NG00114); ADSP R4 (NG00067) |
| **AD Knowledge Portal** | `https://adknowledgeportal.synapse.org/` | AMP-AD Diversity (multi-ethnic brain multi-omics) |
| **AMP-AD Agora** | `https://agora.ampadportal.org/` | AD target-gene nominations |
| **Alzheimer DataLENS** | `https://alzdatalens.partners.org/` | Harmonized AMP-AD / IGAP omics queries |
| **ONTIME QTL browser** | `https://ontime.wustl.edu/` | Knight-ADRC plasma pQTL/mQTL atlas |

> Raw multi-omics data behind these portals is typically gated by data-use
> agreements (DUAs); NeuroOmics-AD does **not** bundle or redistribute it.

## Verification

```bash
python scripts/verify_databases.py            # human-readable report
python scripts/verify_databases.py --json     # machine-readable report
python scripts/verify_databases.py --timeout 20
```

Exit code is `0` when every source is reachable/present and `1` otherwise.
`TLS/EGRESS` / `DNS` failures indicate the runtime's network allowlist is
blocking the host (common in sandboxes/CI), not that the database is down.
