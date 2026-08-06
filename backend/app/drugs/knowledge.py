"""Curated drug–target knowledge base.

This module encodes ~70 AD-relevant drugs (approved AD drugs + well-studied
repurposing candidates) with:
  * targets (gene symbols, mapped to the PPI interactome),
  * mechanism & indication,
  * FDA status, clinical trial counts,
  * physicochemical properties (for BBB/ADMET scoring),
  * expression-direction maps for pathway-reversal scoring.

Real deployments merge this with live DrugBank/ChEMBL/DGIdb/OpenTargets data
(see `sources.py`); this built-in set guarantees offline operation and
reproducible demos.
"""
from __future__ import annotations

from typing import Any

# drug id -> record
_DRUGS: dict[str, dict[str, Any]] = {
    # ---------------- approved AD therapies ----------------
    "donepezil": {
        "name": "Donepezil", "drugbank_id": "DB00843", "pubchem_cid": "3152", "chebi_id": "53289",
        "targets": ["ACHE"], "mechanism": "Acetylcholinesterase inhibitor",
        "indication": "Mild-to-moderate AD", "fda_status": "Approved", "clinical_phase": "approved",
        "trials": 420, "mw": 379.5, "logp": 4.3, "hbd": 1, "hba": 4, "tpsa": 38.8, "rot": 7, "bbb": 0.9,
        "direction": {"ACHE": -1},
    },
    "rivastigmine": {
        "name": "Rivastigmine", "drugbank_id": "DB00989", "pubchem_cid": "77991", "chebi_id": "8862",
        "targets": ["ACHE", "BCHE"], "mechanism": "Dual cholinesterase inhibitor",
        "indication": "Mild-to-moderate AD / Parkinson's dementia", "fda_status": "Approved", "clinical_phase": "approved",
        "trials": 210, "mw": 250.34, "logp": 2.3, "hbd": 0, "hba": 3, "tpsa": 32.8, "rot": 5, "bbb": 0.85,
        "direction": {"ACHE": -1, "BCHE": -1},
    },
    "galantamine": {
        "name": "Galantamine", "drugbank_id": "DB00674", "pubchem_cid": "9651", "chebi_id": "53278",
        "targets": ["ACHE"], "mechanism": "Acetylcholinesterase inhibitor, nAChR modulator",
        "indication": "Mild-to-moderate AD", "fda_status": "Approved", "clinical_phase": "approved",
        "trials": 150, "mw": 287.36, "logp": 1.6, "hbd": 2, "hba": 4, "tpsa": 41.9, "rot": 2, "bbb": 0.85,
        "direction": {"ACHE": -1},
    },
    "memantine": {
        "name": "Memantine", "drugbank_id": "DB01043", "pubchem_cid": "4054", "chebi_id": "64312",
        "targets": ["GRIN1", "GRIN2B"], "mechanism": "NMDA receptor antagonist",
        "indication": "Moderate-to-severe AD", "fda_status": "Approved", "clinical_phase": "approved",
        "trials": 190, "mw": 179.3, "logp": 3.28, "hbd": 1, "hba": 1, "tpsa": 26.0, "rot": 1, "bbb": 0.95,
        "direction": {"GRIN1": -1, "GRIN2B": -1},
    },
    "aducanumab": {
        "name": "Aducanumab", "drugbank_id": "DB12274", "pubchem_cid": "", "chebi_id": "",
        "targets": ["APP"], "mechanism": "Anti-amyloid monoclonal antibody",
        "indication": "Early AD", "fda_status": "Approved", "clinical_phase": "approved",
        "trials": 25, "mw": 145000, "logp": 0.0, "hbd": 0, "hba": 0, "tpsa": 0.0, "rot": 0, "bbb": 0.05,
        "direction": {"APP": -1},
    },
    "lecanemab": {
        "name": "Lecanemab", "drugbank_id": "DB16972", "pubchem_cid": "", "chebi_id": "",
        "targets": ["APP"], "mechanism": "Anti-amyloid protofibril antibody",
        "indication": "Early AD", "fda_status": "Approved", "clinical_phase": "approved",
        "trials": 12, "mw": 146000, "logp": 0.0, "hbd": 0, "hba": 0, "tpsa": 0.0, "rot": 0, "bbb": 0.05,
        "direction": {"APP": -1},
    },
    "donanemab": {
        "name": "Donanemab", "drugbank_id": "DB16490", "pubchem_cid": "", "chebi_id": "",
        "targets": ["APP"], "mechanism": "Anti-pyroglutamate-amyloid antibody",
        "indication": "Early symptomatic AD", "fda_status": "Approved", "clinical_phase": "approved",
        "trials": 8, "mw": 148000, "logp": 0.0, "hbd": 0, "hba": 0, "tpsa": 0.0, "rot": 0, "bbb": 0.05,
        "direction": {"APP": -1},
    },
    # ---------------- anti-inflammatory ----------------
    "minocycline": {
        "name": "Minocycline", "drugbank_id": "DB01017", "pubchem_cid": "54675783", "chebi_id": "50694",
        "targets": ["TLR4", "MMP9", "CASP1"], "mechanism": "Tetracycline antibiotic; microglial activation & neuroinflammation modulator",
        "indication": "Antibiotic; repurposing for AD/PD", "fda_status": "Approved", "clinical_phase": "phase3",
        "trials": 18, "mw": 457.5, "logp": 0.05, "hbd": 6, "hba": 8, "tpsa": 131.4, "rot": 1, "bbb": 0.7,
        "direction": {"TLR4": -1, "MMP9": -1, "CASP1": -1, "TNF": -1, "IL1B": -1},
    },
    "doxycycline": {
        "name": "Doxycycline", "drugbank_id": "DB00254", "pubchem_cid": "54671203", "chebi_id": "50845",
        "targets": ["MMP9", "MMP2"], "mechanism": "Tetracycline; MMP inhibitor, anti-inflammatory",
        "indication": "Antibiotic; AD repurposing candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 9, "mw": 444.4, "logp": 0.64, "hbd": 6, "hba": 9, "tpsa": 153.4, "rot": 2, "bbb": 0.6,
        "direction": {"MMP9": -1, "MMP2": -1, "TNF": -1},
    },
    "colchicine": {
        "name": "Colchicine", "drugbank_id": "DB01394", "pubchem_cid": "6167", "chebi_id": "27882",
        "targets": ["TUBB", "NLRP3"], "mechanism": "Microtubule inhibitor; NLRP3 inflammasome blockade",
        "indication": "Gout, pericarditis; AD inflammation candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 7, "mw": 399.4, "logp": 1.03, "hbd": 1, "hba": 6, "tpsa": 83.1, "rot": 4, "bbb": 0.5,
        "direction": {"NLRP3": -1, "CASP1": -1, "IL1B": -1},
    },
    "indomethacin": {
        "name": "Indomethacin", "drugbank_id": "DB00328", "pubchem_cid": "3715", "chebi_id": "49662",
        "targets": ["PTGS2", "PTGS1"], "mechanism": "NSAID; COX inhibition, anti-amyloid",
        "indication": "NSAID; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 11, "mw": 357.8, "logp": 4.14, "hbd": 1, "hba": 4, "tpsa": 68.5, "rot": 4, "bbb": 0.55,
        "direction": {"PTGS2": -1, "PTGS1": -1, "IL1B": -1},
    },
    "ibuprofen": {
        "name": "Ibuprofen", "drugbank_id": "DB01050", "pubchem_cid": "3672", "chebi_id": "5855",
        "targets": ["PTGS2", "PTGS1"], "mechanism": "NSAID; COX inhibitor",
        "indication": "NSAID; epidemiological AD risk reduction", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 6, "mw": 206.3, "logp": 3.72, "hbd": 1, "hba": 2, "tpsa": 37.3, "rot": 3, "bbb": 0.5,
        "direction": {"PTGS2": -1, "PTGS1": -1},
    },
    "celecoxib": {
        "name": "Celecoxib", "drugbank_id": "DB00482", "pubchem_cid": "2662", "chebi_id": "9142",
        "targets": ["PTGS2"], "mechanism": "COX-2 selective inhibitor",
        "indication": "Arthritis; AD candidate (mixed trials)", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 5, "mw": 381.4, "logp": 3.52, "hbd": 1, "hba": 5, "tpsa": 77.9, "rot": 3, "bbb": 0.45,
        "direction": {"PTGS2": -1},
    },
    "canakinumab": {
        "name": "Canakinumab", "drugbank_id": "DB06168", "pubchem_cid": "", "chebi_id": "",
        "targets": ["IL1B"], "mechanism": "Anti-IL-1β monoclonal antibody",
        "indication": "Autoinflammatory; AD inflammation candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 3, "mw": 145000, "logp": 0.0, "hbd": 0, "hba": 0, "tpsa": 0.0, "rot": 0, "bbb": 0.02,
        "direction": {"IL1B": -1, "IL6": -1},
    },
    "anakinra": {
        "name": "Anakinra", "drugbank_id": "DB00026", "pubchem_cid": "", "chebi_id": "",
        "targets": ["IL1R1"], "mechanism": "IL-1 receptor antagonist",
        "indication": "RA; AD neuroinflammation candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 2, "mw": 17300, "logp": 0.0, "hbd": 0, "hba": 0, "tpsa": 0.0, "rot": 0, "bbb": 0.03,
        "direction": {"IL1B": -1, "IL6": -1},
    },
    "baricitinib": {
        "name": "Baricitinib", "drugbank_id": "DB11817", "pubchem_cid": "44205240", "chebi_id": "",
        "targets": ["JAK1", "JAK2"], "mechanism": "JAK1/2 inhibitor; STAT3 pathway suppression",
        "indication": "RA, COVID-19; AD neuroinflammation candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 4, "mw": 371.4, "logp": 1.36, "hbd": 0, "hba": 7, "tpsa": 98.3, "rot": 4, "bbb": 0.45,
        "direction": {"JAK1": -1, "JAK2": -1, "STAT3": -1, "IL6": -1},
    },
    "tofacitinib": {
        "name": "Tofacitinib", "drugbank_id": "DB08895", "pubchem_cid": "9926791", "chebi_id": "71219",
        "targets": ["JAK3", "JAK1", "JAK2"], "mechanism": "JAK inhibitor",
        "indication": "RA; neuroinflammation candidate", "fda_status": "Approved", "clinical_phase": "preclinical",
        "trials": 2, "mw": 312.4, "logp": 1.73, "hbd": 0, "hba": 8, "tpsa": 91.0, "rot": 2, "bbb": 0.4,
        "direction": {"JAK3": -1, "JAK1": -1, "STAT3": -1},
    },
    # ---------------- metabolic / insulin ----------------
    "metformin": {
        "name": "Metformin", "drugbank_id": "DB00331", "pubchem_cid": "4091", "chebi_id": "6801",
        "targets": ["PRKAA1", "MTOR", "IRS1"], "mechanism": "AMPK activator; insulin sensitizer; autophagy enhancer",
        "indication": "Type 2 diabetes; leading AD repurposing candidate", "fda_status": "Approved", "clinical_phase": "phase3",
        "trials": 45, "mw": 129.16, "logp": -0.92, "hbd": 3, "hba": 3, "tpsa": 58.1, "rot": 1, "bbb": 0.65,
        "direction": {"PRKAA1": 1, "MTOR": -1, "IRS1": 1, "ULK1": 1, "SIRT1": 1},
    },
    "pioglitazone": {
        "name": "Pioglitazone", "drugbank_id": "DB01132", "pubchem_cid": "4829", "chebi_id": "7476",
        "targets": ["PPARG"], "mechanism": "PPARγ agonist; insulin sensitizer, anti-inflammatory",
        "indication": "Type 2 diabetes; AD candidate (TOMMORROW)", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 22, "mw": 356.4, "logp": 3.48, "hbd": 1, "hba": 5, "tpsa": 68.7, "rot": 6, "bbb": 0.6,
        "direction": {"PPARG": 1, "TNF": -1, "IL6": -1, "ABCA1": 1},
    },
    "rosiglitazone": {
        "name": "Rosiglitazone", "drugbank_id": "DB00412", "pubchem_cid": "77999", "chebi_id": "47324",
        "targets": ["PPARG"], "mechanism": "PPARγ agonist",
        "indication": "Type 2 diabetes; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 12, "mw": 357.4, "logp": 2.57, "hbd": 1, "hba": 4, "tpsa": 66.2, "rot": 6, "bbb": 0.6,
        "direction": {"PPARG": 1, "TNF": -1, "IL6": -1},
    },
    "exenatide": {
        "name": "Exenatide", "drugbank_id": "DB01276", "pubchem_cid": "", "chebi_id": "",
        "targets": ["GLP1R"], "mechanism": "GLP-1 receptor agonist",
        "indication": "Type 2 diabetes; neuroprotection candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 14, "mw": 4186, "logp": 0.0, "hbd": 0, "hba": 0, "tpsa": 0.0, "rot": 0, "bbb": 0.2,
        "direction": {"GLP1R": 1, "AKT1": 1, "GSK3B": -1},
    },
    "liraglutide": {
        "name": "Liraglutide", "drugbank_id": "DB06655", "pubchem_cid": "", "chebi_id": "",
        "targets": ["GLP1R"], "mechanism": "GLP-1 receptor agonist",
        "indication": "Type 2 diabetes, obesity; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 11, "mw": 3751, "logp": 0.0, "hbd": 0, "hba": 0, "tpsa": 0.0, "rot": 0, "bbb": 0.15,
        "direction": {"GLP1R": 1, "AKT1": 1, "GSK3B": -1},
    },
    "semaglutide": {
        "name": "Semaglutide", "drugbank_id": "DB13928", "pubchem_cid": "", "chebi_id": "",
        "targets": ["GLP1R"], "mechanism": "GLP-1 receptor agonist",
        "indication": "Type 2 diabetes; neuroinflammation & AD candidate", "fda_status": "Approved", "clinical_phase": "phase3",
        "trials": 9, "mw": 4113, "logp": 0.0, "hbd": 0, "hba": 0, "tpsa": 0.0, "rot": 0, "bbb": 0.15,
        "direction": {"GLP1R": 1, "AKT1": 1, "GSK3B": -1, "TNF": -1},
    },
    "insulin_glargine": {
        "name": "Insulin glargine", "drugbank_id": "DB00047", "pubchem_cid": "", "chebi_id": "",
        "targets": ["INSR"], "mechanism": "Long-acting insulin; brain insulin signaling (intranasal trials)",
        "indication": "Diabetes; intranasal insulin AD trials", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 16, "mw": 6063, "logp": 0.0, "hbd": 0, "hba": 0, "tpsa": 0.0, "rot": 0, "bbb": 0.1,
        "direction": {"INSR": 1, "IRS1": 1, "AKT1": 1, "GSK3B": -1},
    },
    "sitagliptin": {
        "name": "Sitagliptin", "drugbank_id": "DB01261", "pubchem_cid": "4369359", "chebi_id": "40237",
        "targets": ["DPP4"], "mechanism": "DPP-4 inhibitor; incretin pathway",
        "indication": "Type 2 diabetes; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 5, "mw": 407.3, "logp": 1.39, "hbd": 1, "hba": 5, "tpsa": 77.9, "rot": 5, "bbb": 0.5,
        "direction": {"DPP4": -1},
    },
    # ---------------- cardiovascular / lipid ----------------
    "atorvastatin": {
        "name": "Atorvastatin", "drugbank_id": "DB01076", "pubchem_cid": "60823", "chebi_id": "39548",
        "targets": ["HMGCR"], "mechanism": "HMG-CoA reductase inhibitor; cholesterol lowering",
        "indication": "Hyperlipidemia; AD risk-reduction candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 28, "mw": 558.6, "logp": 4.46, "hbd": 4, "hba": 5, "tpsa": 111.8, "rot": 11, "bbb": 0.35,
        "direction": {"HMGCR": -1, "APOE": -1, "LDLR": 1, "ABCA1": 1},
    },
    "simvastatin": {
        "name": "Simvastatin", "drugbank_id": "DB00641", "pubchem_cid": "54454", "chebi_id": "9150",
        "targets": ["HMGCR"], "mechanism": "HMG-CoA reductase inhibitor",
        "indication": "Hyperlipidemia; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 19, "mw": 418.6, "logp": 4.72, "hbd": 1, "hba": 5, "tpsa": 72.9, "rot": 6, "bbb": 0.4,
        "direction": {"HMGCR": -1, "APOE": -1},
    },
    "rosuvastatin": {
        "name": "Rosuvastatin", "drugbank_id": "DB01098", "pubchem_cid": "446157", "chebi_id": "38537",
        "targets": ["HMGCR"], "mechanism": "HMG-CoA reductase inhibitor",
        "indication": "Hyperlipidemia; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 8, "mw": 481.5, "logp": 2.55, "hbd": 4, "hba": 6, "tpsa": 130.5, "rot": 9, "bbb": 0.3,
        "direction": {"HMGCR": -1},
    },
    "fenofibrate": {
        "name": "Fenofibrate", "drugbank_id": "DB01039", "pubchem_cid": "3339", "chebi_id": "5000",
        "targets": ["PPARA"], "mechanism": "PPARα agonist; lipid metabolism, mitochondrial biogenesis",
        "indication": "Dyslipidemia; AD metabolism candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 6, "mw": 360.8, "logp": 5.25, "hbd": 0, "hba": 4, "tpsa": 57.7, "rot": 8, "bbb": 0.35,
        "direction": {"PPARA": 1, "CPT1A": 1, "HMGCR": -1},
    },
    "telmisartan": {
        "name": "Telmisartan", "drugbank_id": "DB00966", "pubchem_cid": "65999", "chebi_id": "43779",
        "targets": ["AGTR1", "PPARG"], "mechanism": "AT1 receptor blocker; partial PPARγ agonist",
        "indication": "Hypertension; AD candidate (neuroprotective)", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 14, "mw": 514.6, "logp": 5.54, "hbd": 2, "hba": 5, "tpsa": 99.1, "rot": 7, "bbb": 0.5,
        "direction": {"AGTR1": -1, "PPARG": 1, "TNF": -1},
    },
    "losartan": {
        "name": "Losartan", "drugbank_id": "DB00678", "pubchem_cid": "3961", "chebi_id": "65342",
        "targets": ["AGTR1"], "mechanism": "AT1 receptor blocker",
        "indication": "Hypertension; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 9, "mw": 422.9, "logp": 4.01, "hbd": 1, "hba": 6, "tpsa": 96.5, "rot": 6, "bbb": 0.4,
        "direction": {"AGTR1": -1},
    },
    "candesartan": {
        "name": "Candesartan", "drugbank_id": "DB00796", "pubchem_cid": "2541", "chebi_id": "3347",
        "targets": ["AGTR1"], "mechanism": "AT1 receptor blocker",
        "indication": "Hypertension; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 7, "mw": 440.5, "logp": 4.06, "hbd": 2, "hba": 7, "tpsa": 117.6, "rot": 5, "bbb": 0.35,
        "direction": {"AGTR1": -1},
    },
    "perindopril": {
        "name": "Perindopril", "drugbank_id": "DB00790", "pubchem_cid": "107807", "chebi_id": "8021",
        "targets": ["ACE"], "mechanism": "ACE inhibitor",
        "indication": "Hypertension; AD candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 4, "mw": 368.5, "logp": 1.58, "hbd": 2, "hba": 5, "tpsa": 86.7, "rot": 7, "bbb": 0.4,
        "direction": {"ACE": -1},
    },
    "sildenafil": {
        "name": "Sildenafil", "drugbank_id": "DB00203", "pubchem_cid": "5212", "chebi_id": "9139",
        "targets": ["PDE5A"], "mechanism": "PDE5 inhibitor; cGMP signaling, cerebral blood flow",
        "indication": "Erectile dysfunction/PAH; EHR-linked AD risk reduction", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 10, "mw": 474.6, "logp": 2.74, "hbd": 1, "hba": 8, "tpsa": 107.5, "rot": 7, "bbb": 0.5,
        "direction": {"PDE5A": -1, "VEGFA": 1, "AKT1": 1},
    },
    "nicardipine": {
        "name": "Nicardipine", "drugbank_id": "DB00622", "pubchem_cid": "4474", "chebi_id": "7558",
        "targets": ["CACNA1C"], "mechanism": "Dihydropyridine calcium-channel blocker",
        "indication": "Hypertension; AD candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 3, "mw": 479.5, "logp": 4.0, "hbd": 1, "hba": 6, "tpsa": 93.6, "rot": 10, "bbb": 0.45,
        "direction": {"CACNA1C": -1},
    },
    # ---------------- tau / kinase ----------------
    "lithium": {
        "name": "Lithium", "drugbank_id": "DB01356", "pubchem_cid": "28486", "chebi_id": "49713",
        "targets": ["GSK3B", "CDK5", "INPP1"], "mechanism": "GSK-3β inhibitor; autophagy & neuroprotection",
        "indication": "Bipolar disorder; AD tau candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 25, "mw": 6.94, "logp": -0.5, "hbd": 0, "hba": 0, "tpsa": 0.0, "rot": 0, "bbb": 0.8,
        "direction": {"GSK3B": -1, "CDK5": -1, "MTOR": -1, "BECN1": 1},
    },
    "valproic_acid": {
        "name": "Valproic acid", "drugbank_id": "DB00313", "pubchem_cid": "3121", "chebi_id": "39865",
        "targets": ["HDAC1", "HDAC2", "GSK3B"], "mechanism": "HDAC inhibitor; GSK-3β modulation",
        "indication": "Epilepsy/bipolar; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 13, "mw": 144.2, "logp": 2.72, "hbd": 1, "hba": 2, "tpsa": 37.3, "rot": 3, "bbb": 0.7,
        "direction": {"HDAC1": -1, "HDAC2": -1, "GSK3B": -1},
    },
    "tideglusib": {
        "name": "Tideglusib", "drugbank_id": "DB12395", "pubchem_cid": "16736865", "chebi_id": "",
        "targets": ["GSK3B"], "mechanism": "Irreversible GSK-3β inhibitor",
        "indication": "AD (phase II completed)", "fda_status": "Investigational", "clinical_phase": "phase2",
        "trials": 5, "mw": 334.4, "logp": 1.9, "hbd": 1, "hba": 4, "tpsa": 60.9, "rot": 4, "bbb": 0.7,
        "direction": {"GSK3B": -1, "MAPT": -1},
    },
    "saracatinib": {
        "name": "Saracatinib", "drugbank_id": "DB11949", "pubchem_cid": "10168963", "chebi_id": "",
        "targets": ["FYN", "SRC"], "mechanism": "Fyn kinase inhibitor; synaptic protection",
        "indication": "Cancer; AD (AZD0530) candidate", "fda_status": "Investigational", "clinical_phase": "phase2",
        "trials": 4, "mw": 542.1, "logp": 3.2, "hbd": 0, "hba": 7, "tpsa": 99.7, "rot": 6, "bbb": 0.6,
        "direction": {"FYN": -1, "SRC": -1, "MAPT": -1},
    },
    "bosutinib": {
        "name": "Bosutinib", "drugbank_id": "DB06616", "pubchem_cid": "5328940", "chebi_id": "71202",
        "targets": ["ABL1", "SRC"], "mechanism": "Src/Abl kinase inhibitor; tau clearance (microglia)",
        "indication": "CML; AD candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 3, "mw": 530.5, "logp": 4.9, "hbd": 0, "hba": 7, "tpsa": 87.6, "rot": 5, "bbb": 0.5,
        "direction": {"ABL1": -1, "SRC": -1, "TYROBP": -1},
    },
    "nilotinib": {
        "name": "Nilotinib", "drugbank_id": "DB06616", "pubchem_cid": "644241", "chebi_id": "65684",
        "targets": ["ABL1"], "mechanism": "Bcr-Abl inhibitor; autophagy stimulation in brain",
        "indication": "CML; AD/PD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 8, "mw": 529.5, "logp": 4.0, "hbd": 1, "hba": 7, "tpsa": 102.0, "rot": 6, "bbb": 0.55,
        "direction": {"ABL1": -1, "BECN1": 1, "SQSTM1": 1},
    },
    "dasatinib": {
        "name": "Dasatinib", "drugbank_id": "DB01254", "pubchem_cid": "3062316", "chebi_id": "41879",
        "targets": ["ABL1", "SRC"], "mechanism": "Multikinase inhibitor; senolytic combination partner",
        "indication": "CML/ALL; senolytic AD candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 6, "mw": 488.0, "logp": 1.8, "hbd": 2, "hba": 8, "tpsa": 101.9, "rot": 7, "bbb": 0.4,
        "direction": {"ABL1": -1, "SRC": -1, "BCL2": -1},
    },
    # ---------------- autophagy / mTOR ----------------
    "sirolimus": {
        "name": "Sirolimus (rapamycin)", "drugbank_id": "DB00877", "pubchem_cid": "5284616", "chebi_id": "9168",
        "targets": ["MTOR", "RPTOR"], "mechanism": "mTOR inhibitor; autophagy & proteostasis",
        "indication": "Immunosuppressant; longevity & AD candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 12, "mw": 914.2, "logp": 5.9, "hbd": 3, "hba": 13, "tpsa": 195.0, "rot": 6, "bbb": 0.35,
        "direction": {"MTOR": -1, "RPTOR": -1, "ULK1": 1, "BECN1": 1, "SQSTM1": -1},
    },
    "everolimus": {
        "name": "Everolimus", "drugbank_id": "DB01590", "pubchem_cid": "6442177", "chebi_id": "85990",
        "targets": ["MTOR", "RPTOR"], "mechanism": "mTOR inhibitor",
        "indication": "Cancer/transplant; AD candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 5, "mw": 958.2, "logp": 5.8, "hbd": 3, "hba": 14, "tpsa": 204.0, "rot": 7, "bbb": 0.3,
        "direction": {"MTOR": -1, "ULK1": 1, "BECN1": 1},
    },
    "nicotinamide_riboside": {
        "name": "Nicotinamide riboside", "drugbank_id": "DB11139", "pubchem_cid": "439924", "chebi_id": "",
        "targets": ["NAMPT", "SIRT1"], "mechanism": "NAD+ precursor; sirtuin activation, mitochondrial health",
        "indication": "Dietary supplement; AD metabolism candidate", "fda_status": "Approved (GRAS)", "clinical_phase": "phase1",
        "trials": 7, "mw": 255.2, "logp": -1.6, "hbd": 4, "hba": 7, "tpsa": 127.3, "rot": 4, "bbb": 0.4,
        "direction": {"NAMPT": 1, "SIRT1": 1, "PGC1A": 1},
    },
    "creatine": {
        "name": "Creatine", "drugbank_id": "DB00148", "pubchem_cid": "586", "chebi_id": "16919",
        "targets": ["CKM", "CKMT2"], "mechanism": "Energy metabolism support; mitochondrial function",
        "indication": "Nutritional supplement; AD candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 4, "mw": 131.1, "logp": -1.8, "hbd": 2, "hba": 3, "tpsa": 64.4, "rot": 2, "bbb": 0.3,
        "direction": {"CKM": 1, "CKMT2": 1},
    },
    "melatonin": {
        "name": "Melatonin", "drugbank_id": "DB01065", "pubchem_cid": "896", "chebi_id": "16796",
        "targets": ["MTNR1A", "MTNR1B"], "mechanism": "Circadian regulator; antioxidant",
        "indication": "Sleep disorders; AD sleep/cognition candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 15, "mw": 232.3, "logp": 1.5, "hbd": 2, "hba": 2, "tpsa": 41.1, "rot": 3, "bbb": 0.85,
        "direction": {"MTNR1A": 1, "MTNR1B": 1, "SOD1": 1},
    },
    # ---------------- antioxidant / nutraceutical ----------------
    "n_acetylcysteine": {
        "name": "N-acetylcysteine", "drugbank_id": "DB06151", "pubchem_cid": "12035", "chebi_id": "16389",
        "targets": ["GSR", "GCLC"], "mechanism": "Glutathione precursor; antioxidant",
        "indication": "Paracetamol overdose; AD oxidative-stress candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 6, "mw": 163.2, "logp": -0.3, "hbd": 2, "hba": 4, "tpsa": 91.0, "rot": 4, "bbb": 0.4,
        "direction": {"GSR": 1, "GCLC": 1, "GPX1": 1},
    },
    "curcumin": {
        "name": "Curcumin", "drugbank_id": "DB11672", "pubchem_cid": "969516", "chebi_id": "3962",
        "targets": ["NFE2L2", "KEAP1", "PTGS2"], "mechanism": "Nrf2 activator; antioxidant, anti-amyloid",
        "indication": "Nutraceutical; AD candidate", "fda_status": "Approved (supplement)", "clinical_phase": "phase2",
        "trials": 20, "mw": 368.4, "logp": 3.29, "hbd": 2, "hba": 6, "tpsa": 96.2, "rot": 8, "bbb": 0.45,
        "direction": {"NFE2L2": 1, "KEAP1": -1, "PTGS2": -1, "HMOX1": 1, "NQO1": 1},
    },
    "resveratrol": {
        "name": "Resveratrol", "drugbank_id": "DB02709", "pubchem_cid": "445154", "chebi_id": "45713",
        "targets": ["SIRT1", "NFE2L2"], "mechanism": "Sirtuin activator; antioxidant, SIRT1 signaling",
        "indication": "Nutraceutical; AD candidate", "fda_status": "Approved (supplement)", "clinical_phase": "phase2",
        "trials": 14, "mw": 228.2, "logp": 3.14, "hbd": 3, "hba": 3, "tpsa": 60.7, "rot": 2, "bbb": 0.5,
        "direction": {"SIRT1": 1, "NFE2L2": 1, "HMOX1": 1},
    },
    "sulforaphane": {
        "name": "Sulforaphane", "drugbank_id": "DB11746", "pubchem_cid": "5350", "chebi_id": "75414",
        "targets": ["NFE2L2", "KEAP1"], "mechanism": "Nrf2 pathway activator",
        "indication": "Nutraceutical; AD oxidative-stress candidate", "fda_status": "Approved (supplement)", "clinical_phase": "phase1",
        "trials": 3, "mw": 177.3, "logp": 0.23, "hbd": 1, "hba": 2, "tpsa": 62.7, "rot": 4, "bbb": 0.45,
        "direction": {"NFE2L2": 1, "KEAP1": -1, "HMOX1": 1},
    },
    # ---------------- antiviral / infectious ----------------
    "valacyclovir": {
        "name": "Valacyclovir", "drugbank_id": "DB00577", "pubchem_cid": "135398742", "chebi_id": "35854",
        "targets": ["POLR2A", "TK1"], "mechanism": "Anti-herpetic prodrug; HSV-1 hypothesis",
        "indication": "Herpes; AD infection-hypothesis candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 5, "mw": 324.3, "logp": 0.7, "hbd": 4, "hba": 7, "tpsa": 115.0, "rot": 7, "bbb": 0.35,
        "direction": {"TK1": -1, "APP": -1},
    },
    "acyclovir": {
        "name": "Acyclovir", "drugbank_id": "DB00787", "pubchem_cid": "135398513", "chebi_id": "2453",
        "targets": ["TK1"], "mechanism": "Anti-herpetic nucleoside analog",
        "indication": "Herpes; AD candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 3, "mw": 225.2, "logp": -0.9, "hbd": 3, "hba": 5, "tpsa": 106.0, "rot": 2, "bbb": 0.3,
        "direction": {"TK1": -1},
    },
    # ---------------- other repurposing ----------------
    "bexarotene": {
        "name": "Bexarotene", "drugbank_id": "DB00307", "pubchem_cid": "82146", "chebi_id": "34575",
        "targets": ["RXRA", "RXRB", "RXRG"], "mechanism": "RXR agonist; APOE/ABCA1-mediated Aβ clearance",
        "indication": "Cutaneous T-cell lymphoma; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 9, "mw": 348.5, "logp": 5.75, "hbd": 1, "hba": 2, "tpsa": 37.4, "rot": 4, "bbb": 0.5,
        "direction": {"RXRA": 1, "ABCA1": 1, "APOE": 1, "IDE": 1, "MME": 1},
    },
    "methylene_blue": {
        "name": "Methylene blue", "drugbank_id": "DB09291", "pubchem_cid": "6099", "chebi_id": "6872",
        "targets": ["MAPT"], "mechanism": "Tau aggregation inhibitor; mitochondrial enhancer",
        "indication": "Methemoglobinemia; AD tau candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 8, "mw": 319.9, "logp": 0.72, "hbd": 0, "hba": 4, "tpsa": 45.3, "rot": 0, "bbb": 0.7,
        "direction": {"MAPT": -1, "COX1": 1},
    },
    "clioquinol": {
        "name": "Clioquinol", "drugbank_id": "DB04815", "pubchem_cid": "2788", "chebi_id": "3691",
        "targets": ["APP", "BACE1"], "mechanism": "Metal ionophore; Aβ metal-chelation",
        "indication": "Formerly antiparasitic; AD candidate", "fda_status": "Withdrawn", "clinical_phase": "phase2",
        "trials": 4, "mw": 305.5, "logp": 3.9, "hbd": 1, "hba": 2, "tpsa": 33.1, "rot": 0, "bbb": 0.7,
        "direction": {"APP": -1, "BACE1": -1},
    },
    "deferiprone": {
        "name": "Deferiprone", "drugbank_id": "DB08826", "pubchem_cid": "2972", "chebi_id": "6858",
        "targets": ["TF", "FTL"], "mechanism": "Iron chelator; ferroptosis & metal homeostasis",
        "indication": "Iron overload; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 5, "mw": 139.2, "logp": 0.34, "hbd": 1, "hba": 2, "tpsa": 52.1, "rot": 0, "bbb": 0.6,
        "direction": {"FTL": -1, "TF": -1},
    },
    "deferoxamine": {
        "name": "Deferoxamine", "drugbank_id": "DB00746", "pubchem_cid": "2973", "chebi_id": "43568",
        "targets": ["TF", "FTL"], "mechanism": "Iron chelator",
        "indication": "Iron overload; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 3, "mw": 560.7, "logp": -5.2, "hbd": 10, "hba": 12, "tpsa": 210.0, "rot": 15, "bbb": 0.15,
        "direction": {"FTL": -1, "TF": -1},
    },
    "fingolimod": {
        "name": "Fingolimod", "drugbank_id": "DB08868", "pubchem_cid": "107969", "chebi_id": "68787",
        "targets": ["S1PR1"], "mechanism": "S1P receptor modulator; neuroprotection",
        "indication": "Multiple sclerosis; AD candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 4, "mw": 307.5, "logp": 4.33, "hbd": 2, "hba": 2, "tpsa": 54.8, "rot": 8, "bbb": 0.6,
        "direction": {"S1PR1": -1, "MAPT": -1},
    },
    "riluzole": {
        "name": "Riluzole", "drugbank_id": "DB00740", "pubchem_cid": "5070", "chebi_id": "8863",
        "targets": ["SLC1A2", "GRIN1"], "mechanism": "Glutamate modulator; neuroprotection",
        "indication": "ALS; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 6, "mw": 234.2, "logp": 3.05, "hbd": 1, "hba": 2, "tpsa": 72.6, "rot": 1, "bbb": 0.75,
        "direction": {"SLC1A2": 1, "GRIN1": -1},
    },
    "tamoxifen": {
        "name": "Tamoxifen", "drugbank_id": "DB00675", "pubchem_cid": "2733525", "chebi_id": "41774",
        "targets": ["ESR1", "ESR2"], "mechanism": "SERM; estrogen signaling",
        "indication": "Breast cancer; AD candidate (women)", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 3, "mw": 371.5, "logp": 6.31, "hbd": 0, "hba": 2, "tpsa": 12.5, "rot": 4, "bbb": 0.5,
        "direction": {"ESR1": 1, "ESR2": 1},
    },
    "raloxifene": {
        "name": "Raloxifene", "drugbank_id": "DB00481", "pubchem_cid": "5035", "chebi_id": "8772",
        "targets": ["ESR1", "ESR2"], "mechanism": "SERM; estrogen receptor modulation",
        "indication": "Osteoporosis; AD candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 4, "mw": 473.6, "logp": 5.07, "hbd": 2, "hba": 5, "tpsa": 66.3, "rot": 4, "bbb": 0.4,
        "direction": {"ESR1": 1, "ESR2": 1},
    },
    "minoxidil": {
        "name": "Minoxidil", "drugbank_id": "DB00350", "pubchem_cid": "4201", "chebi_id": "6942",
        "targets": ["KCNJ8", "ABCC9"], "mechanism": "K-ATP channel opener; vasodilation",
        "indication": "Hypertension/hair loss; candidate (blood flow)", "fda_status": "Approved", "clinical_phase": "preclinical",
        "trials": 1, "mw": 209.3, "logp": 0.63, "hbd": 2, "hba": 5, "tpsa": 90.9, "rot": 0, "bbb": 0.4,
        "direction": {"KCNJ8": 1},
    },
    "pirfenidone": {
        "name": "Pirfenidone", "drugbank_id": "DB04951", "pubchem_cid": "40632", "chebi_id": "32016",
        "targets": ["TGFB1", "TNF"], "mechanism": "Anti-fibrotic; TGF-β suppression, anti-inflammatory",
        "indication": "IPF; AD candidate", "fda_status": "Approved", "clinical_phase": "preclinical",
        "trials": 2, "mw": 185.2, "logp": 1.35, "hbd": 1, "hba": 2, "tpsa": 40.5, "rot": 1, "bbb": 0.55,
        "direction": {"TGFB1": -1, "TNF": -1, "IL6": -1},
    },
    "nicotine": {
        "name": "Nicotine", "drugbank_id": "DB00184", "pubchem_cid": "89594", "chebi_id": "17688",
        "targets": ["CHRNA4", "CHRNB2"], "mechanism": "nAChR agonist; cholinergic enhancement",
        "indication": "Smoking cessation; AD candidate (patch trials)", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 11, "mw": 162.2, "logp": 1.17, "hbd": 1, "hba": 2, "tpsa": 16.1, "rot": 1, "bbb": 0.9,
        "direction": {"CHRNA4": 1, "CHRNB2": 1, "ACHE": -1},
    },
    "fluoxetine": {
        "name": "Fluoxetine", "drugbank_id": "DB00472", "pubchem_cid": "3386", "chebi_id": "5118",
        "targets": ["SLC6A4"], "mechanism": "SSRI; serotonin transporter inhibition",
        "indication": "Depression; AD depression candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 9, "mw": 309.3, "logp": 4.17, "hbd": 1, "hba": 1, "tpsa": 21.3, "rot": 5, "bbb": 0.8,
        "direction": {"SLC6A4": -1, "BDNF": 1},
    },
    "escitalopram": {
        "name": "Escitalopram", "drugbank_id": "DB01175", "pubchem_cid": "146570", "chebi_id": "36790",
        "targets": ["SLC6A4"], "mechanism": "SSRI",
        "indication": "Depression; AD behavioral candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 7, "mw": 324.4, "logp": 3.53, "hbd": 1, "hba": 2, "tpsa": 36.4, "rot": 4, "bbb": 0.8,
        "direction": {"SLC6A4": -1},
    },
    "citalopram": {
        "name": "Citalopram", "drugbank_id": "DB00215", "pubchem_cid": "2771", "chebi_id": "3692",
        "targets": ["SLC6A4"], "mechanism": "SSRI; amyloid-suppression signal in CSF trials",
        "indication": "Depression; AD candidate (CSF Aβ42)", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 6, "mw": 324.4, "logp": 3.53, "hbd": 1, "hba": 2, "tpsa": 36.4, "rot": 4, "bbb": 0.8,
        "direction": {"SLC6A4": -1, "APP": -1},
    },
    "quetiapine": {
        "name": "Quetiapine", "drugbank_id": "DB01224", "pubchem_cid": "5002", "chebi_id": "8707",
        "targets": ["DRD2", "HTR2A", "ADRA1A"], "mechanism": "Atypical antipsychotic",
        "indication": "Schizophrenia/bipolar; AD psychosis", "fda_status": "Approved", "clinical_phase": "approved",
        "trials": 20, "mw": 383.5, "logp": 2.83, "hbd": 1, "hba": 4, "tpsa": 47.6, "rot": 4, "bbb": 0.85,
        "direction": {"DRD2": -1, "HTR2A": -1},
    },
    "mirtazapine": {
        "name": "Mirtazapine", "drugbank_id": "DB00370", "pubchem_cid": "4205", "chebi_id": "6950",
        "targets": ["HTR2A", "ADRA2A"], "mechanism": "Noradrenergic/specific serotonergic antidepressant",
        "indication": "Depression; AD agitation (SYMBAD trial)", "fda_status": "Approved", "clinical_phase": "approved",
        "trials": 6, "mw": 265.4, "logp": 3.49, "hbd": 0, "hba": 3, "tpsa": 19.4, "rot": 1, "bbb": 0.85,
        "direction": {"HTR2A": -1, "ADRA2A": -1},
    },
    "caffeine": {
        "name": "Caffeine", "drugbank_id": "DB00201", "pubchem_cid": "2519", "chebi_id": "27732",
        "targets": ["ADORA1", "ADORA2A"], "mechanism": "Adenosine receptor antagonist",
        "indication": "Stimulant; epidemiological AD protection", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 8, "mw": 194.2, "logp": -0.07, "hbd": 1, "hba": 3, "tpsa": 61.8, "rot": 0, "bbb": 0.85,
        "direction": {"ADORA1": -1, "ADORA2A": -1},
    },
    "levetiracetam": {
        "name": "Levetiracetam", "drugbank_id": "DB01202", "pubchem_cid": "5284583", "chebi_id": "64312",
        "targets": ["SV2A"], "mechanism": "SV2A modulator; synaptic vesicle protein",
        "indication": "Epilepsy; AD epileptiform candidate", "fda_status": "Approved", "clinical_phase": "phase2",
        "trials": 5, "mw": 170.2, "logp": -0.8, "hbd": 1, "hba": 3, "tpsa": 63.4, "rot": 2, "bbb": 0.75,
        "direction": {"SV2A": -1},
    },
    "progesterone": {
        "name": "Progesterone", "drugbank_id": "DB00396", "pubchem_cid": "5994", "chebi_id": "17026",
        "targets": ["PGR"], "mechanism": "Progestogen; neurosteroid modulation",
        "indication": "Hormone therapy; AD candidate", "fda_status": "Approved", "clinical_phase": "phase1",
        "trials": 3, "mw": 314.5, "logp": 3.87, "hbd": 1, "hba": 2, "tpsa": 37.3, "rot": 0, "bbb": 0.75,
        "direction": {"PGR": 1},
    },
}

# Renamed/canonical keys
_ALIASES = {"rapamycin": "sirolimus", "n-acetylcysteine": "n_acetylcysteine", "nac": "n_acetylcysteine"}

CURATED_AD_RISK_GENES = [
    "APOE", "APP", "PSEN1", "PSEN2", "BIN1", "CLU", "ABCA7", "CR1", "PICALM", "MS4A6A",
    "CD33", "CD2AP", "EPHA1", "TREM2", "SORL1", "INPP5D", "MEF2C", "HLA-DRB1", "PTK2B",
    "FERMT2", "CELF1", "BZRAP1", "AP2A1", "SPI1", "ABI3", "PLCG2", "ALPK2", "ADAM10",
    "ACE", "AQN", "APH1B", "HESX1", "CDK5", "GSK3B", "MAPT", "IL1B", "IL6", "TNF",
]


def all_drugs() -> dict[str, dict]:
    """All curated drugs keyed by canonical id."""
    return _DRUGS


def get_drug(key: str) -> dict | None:
    key = _ALIASES.get(key.lower(), key.lower())
    return _DRUGS.get(key)


def search_drugs(query: str) -> list[dict]:
    q = query.lower()
    out = []
    for rec in _DRUGS.values():
        if q in rec["name"].lower() or q in rec["drugbank_id"].lower():
            out.append(rec)
    return out


def drug_targets_graph() -> list[tuple[str, str]]:
    """(drug, gene) edges across the knowledge base."""
    edges = []
    for key, rec in _DRUGS.items():
        for t in rec["targets"]:
            edges.append((key, t))
    return edges
