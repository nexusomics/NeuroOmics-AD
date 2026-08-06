"""Pathway & gene-set enrichment analysis.

Strategy:
  1. Try `gseapy.enrichr` (live API) when network is available.
  2. Fall back to a built-in curated AD-relevant gene-set library with exact
     hypergeometric enrichment + Benjamini–Hochberg FDR, so the platform works
     fully offline.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in curated gene-set library (pathway id -> (description, gene set))
# Representative of GO/KEGG/Reactome; extendable via GMT upload.
# ---------------------------------------------------------------------------
GENE_SETS: dict[str, tuple[str, set[str]]] = {
    "GO_Amyloid_beta_metabolic_process": ("Amyloid-beta metabolic process (GO:0050435)", {
        "APP", "BACE1", "BACE2", "PSEN1", "PSEN2", "NCSTN", "APH1A", "APH1B", "IDE", "MME",
        "ADAM10", "ADAM17", "CTSB", "CTSD", "APOE", "APOC1", "CLU", "SORL1", "PICALM", "CD2AP",
    }),
    "GO_Tau_protein_binding": ("Tau protein binding (GO:0048156)", {
        "MAPT", "GSK3B", "CDK5", "PIN1", "PP2A", "BIN1", "APP", "APOE", "TUBB", "FKBP5",
        "HSP90AA1", "HSPA8", "DDR1", "MAPK8", "MARK2", "UBB", "UCHL1", "PINK1",
    }),
    "GO_Neuroinflammation": ("Neuroinflammatory response (GO:0150077)", {
        "IL1B", "IL6", "TNF", "TLR4", "TLR2", "TLR9", "NLRP3", "CASP1", "PTGS2", "CCL2",
        "CCL5", "CXCL10", "CD68", "TREM2", "TYROBP", "CSF1R", "AIF1", "GFAP", "STAT3", "NFKB1",
    }),
    "GO_Microglial_activation": ("Microglial cell activation (GO:0001774)", {
        "TREM2", "TYROBP", "CSF1R", "P2RY12", "CX3CR1", "AIF1", "CD68", "ITGAM", "ITGAX",
        "SPI1", "IRF8", "RUNX1", "SYK", "DAP12", "TLR4", "NLRP3", "IL1B", "TNF", "C1QA", "C1QB",
    }),
    "GO_Oxidative_stress_response": ("Response to oxidative stress (GO:0006979)", {
        "SOD1", "SOD2", "CAT", "GPX1", "GPX4", "GSR", "TXNRD1", "PRDX1", "PRDX2", "PRDX3",
        "HMOX1", "NQO1", "NFE2L2", "KEAP1", "GCLC", "GCLM", "NOS2", "NOX1", "NOX4", "CYBB",
    }),
    "GO_Mitochondrial_function": ("Mitochondrial function (GO:0005739)", {
        "NDUFS1", "NDUFV1", "NDUFA1", "SDHB", "SDHD", "UQCRC1", "UQCRB", "COX1", "COX2", "COX3",
        "ATP5A1", "ATP5B", "ATP5C1", "MFN1", "MFN2", "OPA1", "DRP1", "PINK1", "PARK7", "TFAM",
    }),
    "GO_Autophagy": ("Autophagy (GO:0006914)", {
        "ATG5", "ATG7", "ATG12", "ATG16L1", "BECN1", "LC3A", "LC3B", "SQSTM1", "ULK1", "ULK2",
        "MTOR", "AMPK", "TFEB", "LAMP1", "LAMP2", "CTSD", "OPTN", "PARK2", "VPS35", "WIPI1",
    }),
    "GO_Synaptic_transmission": ("Chemical synaptic transmission (GO:0007268)", {
        "SYT1", "SNAP25", "SYN1", "SYN2", "STX1A", "VAMP2", "DLG4", "GRIN1", "GRIN2B", "GRIA1",
        "GABRA1", "GAD1", "GAD2", "CHAT", "ACHE", "SLC17A6", "SLC6A1", "NRXN1", "NLGN1", "CAMK2A",
    }),
    "GO_Apoptotic_process": ("Apoptotic process (GO:0006915)", {
        "BAX", "BAK1", "BCL2", "BCL2L1", "MCL1", "CASP3", "CASP7", "CASP8", "CASP9", "CYCS",
        "APAF1", "FAS", "FASLG", "TNFRSF1A", "BID", "BAD", "P53", "MDM2", "XIAP", "DIABLO",
    }),
    "GO_Immune_response": ("Innate immune response (GO:0045087)", {
        "TLR1", "TLR2", "TLR4", "TLR7", "TLR9", "MYD88", "IRAK1", "IRAK4", "TRAF6", "NFKB1",
        "RELA", "IKBKB", "CASP1", "IL1B", "IL6", "TNF", "CXCL8", "CCL2", "DEFB1", "C3",
    }),
    "KEGG_Alzheimers_disease": ("KEGG: Alzheimer's disease (hsa05010)", {
        "APP", "BACE1", "PSEN1", "PSEN2", "MAPT", "APOE", "GSK3B", "CDK5", "IDE", "MME",
        "CASP3", "CASP8", "CASP9", "BAX", "BCL2", "CYCS", "ADAM10", "ADAM17", "NCSTN", "APH1A",
    }),
    "KEGG_Cholinergic_synapse": ("KEGG: Cholinergic synapse (hsa04725)", {
        "CHAT", "ACHE", "CHRM1", "CHRM2", "CHRM3", "CHRNA4", "CHRNB2", "GNAQ", "GNAI1", "PRKCA",
        "CAMK2A", "CREB1", "ADCY1", "PKA", "PLCB1", "ERK1", "ERK2", "AP1", "SNAP25", "VAMP2",
    }),
    "KEGG_Parkinsons_disease": ("KEGG: Parkinson's disease (hsa05012)", {
        "SNCA", "PARK2", "PINK1", "DJ1", "LRRK2", "ATP13A2", "UCHL1", "HTRA2", "UQCRC1", "NDUFS1",
        "COX1", "ATP5A1", "BAX", "CASP9", "CASP3", "GBA", "VPS35", "EIF4G1", "DNAJC13", "SYT11",
    }),
    "Reactome_Immune_System": ("Reactome: Immune System (R-HSA-168256)", {
        "TLR4", "MYD88", "IRAK4", "TRAF6", "NFKB1", "RELA", "IKBKB", "TNF", "IL6", "IL1B",
        "CASP1", "CASP8", "FADD", "TRADD", "RIPK1", "TAB1", "MAP3K7", "IKBKG", "CASP3", "CXCL8",
    }),
    "Reactome_Neuronal_System": ("Reactome: Neuronal System (R-HSA-112316)", {
        "SNAP25", "SYT1", "VAMP2", "STX1A", "GRIN1", "GRIN2B", "GRIA1", "GLRA1", "GABRA1",
        "CHRNA4", "CHRNB2", "SLC6A1", "DLG4", "CAMK2A", "NCAM1", "L1CAM", "NRXN1", "NLGN1", "KCNQ2", "SCN1A",
    }),
    "GO_Lipid_metabolism": ("Lipid metabolic process (GO:0006629)", {
        "APOE", "APOA1", "APOC1", "APOC3", "SREBF1", "SREBF2", "HMGCR", "LDLR", "SCARB1", "ABCA1",
        "ABCG1", "CETP", "LCAT", "PLA2G4A", "PLA2G7", "ACSL1", "FASN", "SCD", "ELOVL5", "PPARG",
    }),
    "GO_Cholesterol_efflux": ("Cholesterol efflux (GO:0033344)", {
        "ABCA1", "ABCG1", "APOA1", "APOE", "NR1H3", "NR1H2", "PPARG", "SCARB1", "PLTP", "CETP",
    }),
    "GO_Insulin_signaling": ("Insulin signaling pathway (GO:0008286)", {
        "INSR", "IRS1", "IRS2", "PIK3CA", "AKT1", "AKT2", "MTOR", "GSK3B", "PTPN1", "SLC2A4",
        "IDE", "FOXO1", "SIRT1", "PDE3B", "MAPK1", "MAPK3", "RPS6KB1", "TSC2", "RHEB", "GLUT4",
    }),
    "GO_Endoplasmic_reticulum_stress": ("Endoplasmic reticulum stress (GO:0034976)", {
        "HSPA5", "DDIT3", "ERN1", "ATF6", "EIF2AK3", "XBP1", "CALR", "CANX", "PDIA3", "SEL1L",
        "OS9", "EDEM1", "DERL1", "VCP", "HERPUD1", "MAPK8", "CASP12", "ATF4", "GADD34", "BIP",
    }),
    "GO_Angiogenesis": ("Angiogenesis (GO:0001525)", {
        "VEGFA", "VEGFB", "KDR", "FLT1", "PGF", "ANGPT1", "ANGPT2", "TEK", "PDGFB", "PDGFRB",
        "FGF2", "FGFR1", "NOTCH1", "DLL4", "EPHB4", "HIF1A", "MMP2", "MMP9", "TIMP1", "TIMP2",
    }),
    "GO_Blood_brain_barrier": ("Blood-brain barrier maintenance (GO:0035633)", {
        "CLDN5", "OCLN", "TJP1", "TJP2", "ABCG2", "ABCB1", "SLC2A1", "VEGF", "PECAM1", "ESM1",
        "TIE2", "ANGPT1", "F11R", "MARVELD2", "CAV1", "LRP1", "LRP2", "RAGE", "AGER", "AQUAPORIN4",
    }),
}


def _builtin_enrichment(gene_list: list[str], databases: list[str], background: Optional[int], min_size: int, max_size: int, fdr_threshold: float) -> list[dict]:
    """Hypergeometric enrichment against the built-in library."""
    genes = {g.upper() for g in gene_list}
    total = background or 20000  # approximate human protein-coding background
    results = []
    for db, (desc, gset) in GENE_SETS.items():
        if databases and not any(d.lower() in db.lower() or db.lower() in d.lower() for d in databases):
            continue
        k = len(gset & genes)
        if k < min_size:
            continue
        m = len(gset)
        if m > max_size:
            continue
        n = total - m
        p = stats.hypergeom.sf(k - 1, total, m, len(genes))
        overlap = sorted(gset & genes)
        results.append({
            "pathway": db,
            "description": desc,
            "overlap": overlap,
            "overlap_size": k,
            "set_size": m,
            "query_size": len(genes),
            "pvalue": float(p),
            "genes": overlap,
        })
    if not results:
        return []
    df = pd.DataFrame(results)
    pvals = df["pvalue"].values
    order = np.argsort(pvals)
    n = len(pvals)
    adj = pvals[order] * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    fdr = np.empty_like(adj)
    fdr[order] = np.minimum(adj, 1.0)
    df["fdr"] = fdr
    df["enrichment_score"] = -np.log10(df["fdr"].clip(lower=1e-300))
    df = df[df["fdr"] <= fdr_threshold].sort_values("fdr")
    return df.to_dict(orient="records")


def _enrichr_enrichment(gene_list: list[str], databases: list[str]) -> list[dict] | None:
    """Live Enrichr enrichment via gseapy (returns None on any failure)."""
    try:
        import gseapy as gp

        enr = gp.enrichr(gene_list=gene_list, gene_sets=databases, outdir=None, no_plot=True)
        df = enr.results
        df = df.rename(columns={
            "Term": "pathway", "Adjusted P-value": "fdr", "P-value": "pvalue",
            "Overlap": "overlap_str", "Genes": "genes",
        })
        if df.empty:
            return None
        df = df[df["fdr"] <= 0.05].sort_values("fdr")
        out = []
        for _, r in df.iterrows():
            out.append({
                "pathway": r["pathway"],
                "description": r.get("description", ""),
                "pvalue": float(r["pvalue"]),
                "fdr": float(r["fdr"]),
                "overlap_size": int(str(r.get("overlap_str", "0/0")).split("/")[0]),
                "set_size": int(str(r.get("overlap_str", "0/0")).split("/")[1]) if "/" in str(r.get("overlap_str", "")) else 0,
                "genes": [g.strip() for g in str(r.get("genes", "")).split(";") if g.strip()],
            })
        return out
    except Exception as exc:  # noqa: BLE001
        logger.info("Enrichr unavailable (%s); using built-in library.", exc)
        return None


def enrich(
    gene_list: list[str],
    background: Optional[list[str]] = None,
    databases: Optional[list[str]] = None,
    min_size: int = 5,
    max_size: int = 500,
    fdr_threshold: float = 0.05,
    prefer_live: bool = True,
) -> dict:
    """Run enrichment and return sorted table + summary."""
    db_list = databases or list(GENE_SETS)
    if prefer_live:
        live = _enrichr_enrichment(gene_list, db_list)
        if live is not None:
            return {"table": live, "summary": {"source": "Enrichr (live)", "genes_tested": len(gene_list), "significant": len(live)}}
    table = _builtin_enrichment(gene_list, db_list, len(background) if background else None, min_size, max_size, fdr_threshold)
    return {
        "table": table,
        "summary": {
            "source": "built-in curated library (hypergeometric + BH-FDR)",
            "genes_tested": len(gene_list),
            "gene_sets_tested": len(db_list),
            "significant": len(table),
        },
    }
