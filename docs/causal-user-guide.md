# Causal Multi-Omics Module — User Guide

This module turns the AD resources into an interactive **causal discovery
engine**: instead of asking "which proteins differ?", you can ask **"which
ancestry-specific causal paths lead from variants to metabolites to cognitive
decline?"** — and get an answer in seconds.

## What it does (plain language)

1. **Harmonizes the resources** — Knight-ADRC (brain/CSF/plasma), ADSP R4 WGS,
   AMP-AD multi-ethnic brain, and plasma multi-omics across ancestries are
   exposed through ONE queryable index: filter by cohort, omics modality,
   ancestry, brain region, biofluid, or phenotype — no raw downloads.
2. **Builds a shared molecular "state"** — a multi-omics latent representation
   (MOFA-style / sparse multi-block PLS / VAE) that fuses all layers even when
   some samples lack some modalities.
3. **Learns causal structure** — NOTEARS + PC + double-ML infer directed
   relationships (genotype → methylation → expression → protein → metabolite →
   cognitive score) rather than mere correlations.
4. **Tests across ancestries** — ancestry-stratified association + trans-ethnic
   meta-analysis flag signals that are shared vs **specific to one ancestry**
   (the same logic that uncovered mostly-novel findings in EUR/AFR plasma data).
5. **Finds multi-omics subtypes** — consensus clustering → each subtype gets
   pathway, drug-target, and progression associations.

## Using the API

```
# Explore the harmonized catalog
GET  /api/v1/causal/resources
GET  /api/v1/causal/query?ancestries=AA,LA&modalities=proteomics,metabolomics&biofluids=plasma

# Run the full causal pipeline (synthetic demo w/ ground truth)
POST /api/v1/causal/pipeline
{ "mode": "synthetic", "options": { "latent_method": "mofa", "n_factors": 6, "n_subtypes": 3 } }

# Run against the harmonized catalog subset
POST /api/v1/causal/pipeline
{ "mode": "catalog", "ancestries": ["AA"], "modalities": ["proteomics", "transcriptomics"],
  "options": { "latent_method": "pls" } }
```

## Interpreting the outputs

| Output | What to look for |
|---|---|
| **Catalog query** | counts by ancestry/modality/region; `query_time_ms` (should be ~1–5 ms) |
| **QC** | number of surrogate variables (transcriptomics), genotype variants after QC, ancestry clusters |
| **Latent** | sample factors — check per-block variance explained |
| **Causal graph (NOTEARS)** | directed edges between layers; `h` ≈ 0 means a valid DAG; PC skeleton gives undirected corroboration |
| **DML** | causal effect of an exposure on outcome with CI — *not* just correlation |
| **Meta-analysis** | `i2_percent` (heterogeneity), `q_pvalue`, and **`ancestry_specific`** flags = signals present in only one ancestry |
| **Subtypes** | silhouette, per-subtype top features, enriched pathways, drug-target overlap, outcome association |

## Example questions the module answers

- *"Show me ancestry-specific causal paths from variants in microglia-related
  loci to plasma metabolites and cognitive scores."* → meta-analysis flags
  ancestry-specific features; causal graph links SNP→protein/metabolite→COG;
  cell-type conditioning isolates microglial contribution.
- *"Identify multi-omics subtypes enriched for vascular–metabolic pathways and
  test their association with rate of decline."* → consensus subtypes →
  pathway enrichment → `subtype_outcome_assoc` on rate_of_decline.

## Caveats (read before interpreting)

- **In-silico predictions**: causal edges from observational data are
  hypotheses, not proof — especially with unobserved confounders. Validate
  top findings experimentally and in independent cohorts.
- **Synthetic demo**: `mode:"synthetic"` uses a simulator with a KNOWN causal
  ground truth (chain + AFR-specific branch) so you can verify the pipeline
  recovers it; the catalog mode applies the same machinery to harmonized index
  subsets.
- **Power**: ancestry-specific signals in underrepresented groups are limited
  by sample size — exactly why the meta-analysis reports heterogeneity.

## External resources for navigation

From results, jump to: AD Knowledge Portal, Alzheimer DataLENS, NIAGADS DSS
(accessions NG00083/NG00102/NG00108/NG00113/NG00114/NG00067), and the ONTIME
QTL browser for Knight-ADRC. Citations for every dataset are in the
`/causal/resources` response.
