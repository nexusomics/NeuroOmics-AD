# Causal Multi-Omics Module — Technical Specification (v1.0)

> Living, queryable analysis module added to NeuroOmics-AD. Turns static
> multi-omics AD resources into an interactive, causal-aware discovery engine.

## 1. Scientific positioning & novelty (as of Aug 2026)

**Grounding scan** (see `causal-literature-review.md` for full review):
- **Knight-ADRC/WashU** (NIAGADS: NG00083, NG00102, NG00108, NG00113, NG00114;
  studies sa000031, sa000052, sa000074): brain/CSF/plasma multi-omics
  (transcriptomics incl. circRNA & cfRNA, proteomics, metabolomics, lipidomics,
  methylation, snRNA-seq) with pQTL/mQTL atlases EUR+AFR.
- **ADSP R4** (NG00067): 36,361 WGS, 45% non-European; integrated G/T/PWAS
  published 2025 (PMC12614089).
- **AMP-AD Diversity**: WGS+RNA-seq+proteomics on 908 multi-ethnic donors
  (306 AA, 326 LA, 252 NHW; 2,224 brain samples).
- **Plasma multi-omics across ancestries** (Alz&Dementia 2026, alz.71164):
  61–83% of protein/metabolite findings **not previously reported**; 21 shared
  proteins; IL-1 & lipid pathways.

**Gaps addressed (novelty claims):**
1. No unified, web-accessible, **causal-aware cross-ancestry/cross-modal**
   framework exists that jointly explores genotype→epigenome→transcriptome→
   proteome→metabolome/lipidome→clinical data.
2. No pipeline layers **snRNA-seq-informed cell-type composition** into bulk
   causal modeling across ancestries.
3. No tool answers seconds-scale natural-language queries like *"ancestry-specific
   causal paths from microglia-related variants to plasma metabolites and
   cognitive decline"* without raw downloads.
4. **Novelty metrics produced**: (a) number of newly implicated features in
   under-mined layers (e.g., Knight-ADRC circRNA layer), (b) ancestry-specific
   regulatory programs (heterogeneity-significant signals), (c) multi-omics
   subtypes with distinct drug/pathway enrichment and progression association.

## 2. Data schema (harmonized catalog)

```
Resource (accession, name, cohort, modalities[], ancestries[], brain_regions[],
          biofluids[], phenotypes[], n_samples, citation, mined_depth)
   └─ Sample (sample_id, cohort, accession, ancestry, modality,
              brain_region, biofluid, diagnosis)   ← precomputed index
```

- Storage: Parquet/HDF5 for real matrices; Zarr for large arrays; VCF/BCF for
  genotypes; **precomputed in-memory index** for ms-scale subsetting.
- The index currently ships with the real resource metadata (accessions,
  sample counts, citations) + synthetic sample-level harmonization; real
  deployments replace the index with harmonized Parquet blocks.
- Query language: filters on any of cohort/accession/modality/ancestry/region/
  biofluid/phenotype/diagnosis → counts + sample head + **query_time_ms**.

## 3. Pipeline DAG

```
 S0 harmonize/index
 ├─ S1 QC: SVA (transcriptomics) · PEER factors · ComBat/LMM (protein/metab)
 │          · ancestry-aware genotype QC (MAF/missing/HWE/LD-prune) + PCA
 ├─ S2 cell-type-aware adjustment (NNLS deconv → composition regression)
 ├─ S3 latent: sparse multi-block PLS · MOFA-like shared factors (missing-
 │          modality aware) · VAE (torch) w/ PCA fallback
 ├─ S4 causal: NOTEARS (linear SEM, DAG) · PC skeleton (Fisher-z)
 │          · DML (cross-fitted Lasso) for effect sizes
 ├─ S5 ancestry-stratified association + trans-ethnic meta (IV fixed /
 │          DerSimonian-Laird random; I², Cochran Q) → ancestry-specific flags
 └─ S6 consensus subtyping → pathway / drug-target / progression enrichment
 S7 artifacts (CSV/JSON) + timing/QC log
```

Implemented in `backend/app/causal/{qc,latent,causal,celltype,ancestry,
subtyping,catalog,pipeline}.py` — every stage is unit-tested and persists
intermediates for re-query.

## 4. API contracts (`/api/v1/causal`, JWT-protected)

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/causal/resources` | — | resource table + index stats |
| GET | `/causal/query` | `?cohorts=&accessions=&modalities=&ancestries=&brain_regions=&biofluids=&phenotypes=&diagnosis=` | counts, by_ancestry/modality/region/biofluid, query_time_ms |
| POST | `/causal/pipeline` | `{mode: synthetic\|catalog, options:{latent_method, n_factors, n_subtypes, lambda1, …}}` | summary, qc, latent, causal{notears,pc,dml}, meta_analysis, subtypes, artifacts |

OpenAPI: all routes auto-documented in Swagger (`/docs`).

## 5. Resource estimates

| Stage | Compute (typical 500-sample, 4-layer cohort) | Storage |
|---|---|---|
| S1 QC | ~2–4 min CPU | small |
| S3 latent | <1 min | latent CSV (KBs) |
| S4 NOTEARS (≤12 vars) | <10 s | adjacency CSV |
| S5 trans-ethnic meta (10⁴ features × 3 ancestries) | ~2 min | CSV |
| S6 subtyping (n_boot=50) | ~1 min | labels + profiles |
| Catalog query | **1–5 ms** (precomputed index) | index in RAM |
| Full pipeline | **~8 s** (synthetic 240 samples, measured) | <2 MB |

Scaling: worker replicas for S1/S5; index sharded per cohort in production.

## 6. Validation

- **Unit**: SVA recovers hidden confounders; ComBat removes batch variance;
  NOTEARS converges to near-DAG (h<0.1) and recovers chain edges; PC finds
  downstream pairs; DML CI covers ATE; MOFA handles 15% missing modalities;
  trans-ethnic meta flags AFR-specific branch; consensus subtypes + outcome
  association work; catalog queries <250 ms.
- **Integration**: full pipeline on a synthetic dataset with **known ground
  truth** recovers ≥2 causal edges; REST endpoint end-to-end.
- **Benchmarks** (measured): catalog query 1–5 ms; full pipeline 7.9 s.

## 7. Integration & external links

API exposes resource citations; frontend links to AD Knowledge Portal,
Alzheimer DataLENS, NIAGADS DSS accessions, and the ONTIME QTL browser for
one-click navigation from novel findings to external annotations.
