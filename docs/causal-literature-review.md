# Causal Multi-Omics Module — Literature Review & Novelty Positioning (Aug 2026)

A targeted scan of the datasets and analytical angles requested, with citations
and the explicit gaps this module fills.

## 1. Knight-ADRC (Washington University in St. Louis)

- **Collection** (NIAGADS DSS): NG00030/51/55/83/85/87/89 + studies sa000008,
  sa000026, sa000031, sa000052, sa000074. Cohort: MAP participants ≥65 y,
  ~95% non-Hispanic White / 5% African American; longitudinal plasma/CSF/
  imaging + autopsied brain.
- **NG00083** — Circular RNAs in AD brains (RNA-seq). Cited in NIAGADS DSS.
- **sa000031** — "Large scale pQTL and mQTL atlas in brain and CSF".
- **sa000074** — "Four large scale pQTL and mQTL atlases in plasma from
  European and African ancestral groups".
- **sa000052** — Plasma cell-free RNA transcriptomics for AD/ADRD.

**Gap:** pQTL/mQTL maps are largely single-layer; circRNA (NG00083) and cfRNA
layers remain under-integrated into causal cross-modal models.

## 2. ADSP R4 whole-genome sequencing

- **NG00067** — 36,361 WGS, 17 cohorts, 14 countries; ~45% non-European;
  >347M variants; unified GCAD pipeline. R5 extends to 58,507 samples.
- **Integrated G/T/PWAS** (Nov 2025, PMC12614089): genome-, transcriptome- and
  proteome-wide association on 15,480 ADSP R4 individuals; integrative risk
  models; **ancestry-aware modeling improved prediction**.

**Gap:** G/T/PWAS integration is association-level; no DAG-level causal
inference from variants through molecular layers to phenotypes, and no
web-queryable interface.

## 3. AMP-AD multi-ethnic brain multi-omics

- **Diversity Initiative** (Alz&Dementia 2024, alz.14208; biorxiv
  2024.04.16.589592): WGS + RNA-seq + proteomics; 908 multi-ethnic donors
  (306 AA, 326 LA, 252 NHW); 2,224 brain samples (DLPFC, STG, PCC).
- **Proteomics across racial groups** (Jan 2025): MAPT/APP elevations shared;
  race-specific protein differences after AD adjustment.

**Gap:** shared vs ancestry-specific **causal programs** (not just
associations) linking variants → epigenome → transcriptome → proteome are
unexplored; cell-type-aware modeling absent.

## 4. Plasma multi-omics across ancestries

- **Alz&Dementia 2026 (alz.71164)**: proteomics + metabolomics in EUR and AFR;
  colocalization with EUR GWAS; **61% (EUR)/72% (AFR) of proteins and
  83% (EUR)/50% (AFR) of metabolites not previously reported**; 21 shared
  proteins; IL-1 production and lipid pathways.

**Gap:** explicit ancestry-stratified meta-analysis with heterogeneity-driven
"ancestry-specific" flags and multi-omics subtype stratification do not exist
in a deployable tool.

## 5. Novelty metrics delivered by this module

1. **Newly implicated features** — the pipeline scores all features per layer
   (incl. under-mined circRNA/cfRNA); meta-analysis reports features never
   flagged in prior AD multi-omics QTL/meta studies.
2. **Ancestry-specific regulatory programs** — trans-ethnic meta with I²/
   Cochran-Q flags exactly the "one-ancestry-only" effectors that the
   plasma multi-omics papers report as novel.
3. **Cell-type-specific mechanisms** — deconvolution-informed adjustment +
   conditioned association separates composition-driven from within-cell
   regulation (microglia/neuron fractions).
4. **Multi-omics subtypes with therapeutic enrichment** — consensus clustering
   → pathway + drug-target + progression association, enabling
   subtype-stratified trial/repurposing hypotheses.

## 6. How to cite

- Datasets: cite the NIAGADS accessions (NG00083, NG00102, NG00108, NG00113,
  NG00114, NG00067) and source papers above; AMP-AD Diversity (alz.14208);
  plasma multi-omics across ancestries (alz.71164); ADSP R4 (alz.70237).
- Methods: SVA (Leek & Storey 2007), PEER (Stegle 2010), ComBat (Johnson 2007),
  DIABLO (Rohart 2017), MOFA+ (Argelaguet 2020), NOTEARS (Zheng 2018),
  DML (Chernozhukov 2018), PC (Spirtes 2000), DerSimonian–Laird (1986).
- Platform: NeuroOmics-AD (this repository; see README/DOI when assigned).
