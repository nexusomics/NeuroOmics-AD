"""Demo seed: creates a demo user, project, synthetic multi-omics datasets and a
few pre-computed analyses so the UI has content on first login.

Usage:  cd backend && python scripts/seed_demo.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.analysis import Analysis  # noqa: E402
from app.models.dataset import Dataset  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.user import User  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")


def make_expression(seed: int = 2026) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    curated = ["APP", "BACE1", "PSEN1", "PSEN2", "APOE", "TREM2", "TYROBP", "MAPT", "GSK3B", "CDK5",
               "IL1B", "IL6", "TNF", "CLU", "SORL1", "PICALM", "CD2AP", "ABCA7", "HMOX1", "NFE2L2",
               "MTOR", "BECN1", "ULK1", "SQSTM1", "GFAP", "AQP4", "CSF1R", "SPI1", "BIN1", "CR1",
               "SOD1", "SOD2", "CAT", "GPX1", "SNAP25", "SYT1", "DLG4", "GRIN1", "CASP3", "BAX"]
    genes = [f"GENE{i:04d}" for i in range(1, 900)] + curated
    n_ad, n_cn = 40, 40
    ad = [f"AD_{i:03d}" for i in range(n_ad)]
    cn = [f"CN_{i:03d}" for i in range(n_cn)]
    X = rng.lognormal(0, 1.3, size=(len(genes), n_ad + n_cn))
    df = pd.DataFrame(X, index=genes, columns=ad + cn)
    up = ["APP", "BACE1", "IL1B", "IL6", "TNF", "TYROBP", "TREM2", "APOE", "HMOX1", "GFAP", "CSF1R",
          "SPI1", "CASP3", "SOD1", "SOD2", "CAT"]
    down = ["MTOR", "BECN1", "ULK1", "SNAP25", "SYT1", "DLG4", "GRIN1", "GPX1", "SQSTM1"]
    for g in up:
        df.loc[g, ad] *= rng.uniform(2.5, 5.0)
    for g in down:
        df.loc[g, ad] *= rng.uniform(0.25, 0.5)
    meta = pd.DataFrame({
        "group": ["AD"] * n_ad + ["CN"] * n_cn,
        "batch": ["B1", "B2"] * (n_ad // 2) + ["B1", "B2"] * (n_cn // 2),
        "age": np.round(rng.normal(74, 6, n_ad + n_cn), 1),
        "sex": np.random.default_rng(seed + 1).choice(["M", "F"], size=n_ad + n_cn),
    }, index=df.columns)
    return df, meta


def seed(admin_email: str = "admin@neuroomics.org") -> None:
    init_db()
    db = SessionLocal()
    try:
        # demo user
        user = db.query(User).filter(User.email == "demo@neuroomics.org").first()
        if not user:
            user = User(email="demo@neuroomics.org", full_name="Demo Researcher",
                        hashed_password=hash_password("demo12345"), role="researcher",
                        organization="NeuroOmics Demo Lab", is_verified=True)
            db.add(user)
            db.commit()
            db.refresh(user)
        # demo project
        project = Project(name="ROSMAP-style AD multi-omics demo", description=(
            "Synthetic multi-omics dataset emulating an AD vs CN cohort (n=80) across "
            "transcriptomics, proteomics, and metabolomics for end-to-end platform demos."),
            disease="Alzheimer's disease", owner_id=user.id)
        db.add(project)
        db.commit()
        db.refresh(project)

        media = Path(__file__).resolve().parent.parent.parent / "media" / "demo"
        media.mkdir(parents=True, exist_ok=True)

        # --- transcriptomics ---
        expr, meta = make_expression()
        expr_path = media / "transcriptomics_expression.csv"
        meta_path = media / "transcriptomics_metadata.csv"
        expr.to_csv(expr_path)
        meta.to_csv(meta_path)
        ds_rna = Dataset(project_id=project.id, name="RNA-seq expression (bulk)", omics_type="transcriptomics",
                         platform="Illumina HiSeq", file_path=str(expr_path), format="csv",
                         n_samples=expr.shape[1], n_features=expr.shape[0], status="ready", uploaded_by=user.id,
                         metadata_json={"metadata_file": str(meta_path), "source": "synthetic (ROSMAP-like)"})
        db.add(ds_rna)

        # --- proteomics ---
        rng = np.random.default_rng(99)
        prot_genes = ["APOE", "CLU", "CFH", "B2M", "APOD", "C3", "GFAP", "NEFL", "TREM2", "APP",
                      "MAPT", "IL6", "TNF", "SERPINA3", "SERPING1", "CRP", "C1QA", "C1QB", "CSF1R", "TYROBP",
                      "HMOX1", "SOD1", "SOD2", "CAT", "GPX1", "ALB", "A2M", "IGHG1", "APOA1", "APOC1"] + [f"P{i:04d}" for i in range(1, 300)]
        prot = pd.DataFrame(rng.lognormal(0, 0.8, size=(len(prot_genes), 80)), index=prot_genes, columns=list(expr.columns))
        for g in ["GFAP", "NEFL", "CLU", "CFH", "B2M", "APOD", "C3", "TREM2", "IL6", "CRP", "C1QA", "TYROBP"]:
            prot.loc[g, [c for c in prot.columns if c.startswith("AD")]] *= rng.uniform(1.6, 2.8)
        prot_path = media / "proteomics_soma.csv"
        prot.to_csv(prot_path)
        db.add(Dataset(project_id=project.id, name="Plasma proteomics (SomaScan-like)", omics_type="proteomics",
                       platform="SomaScan 7K", file_path=str(prot_path), format="csv",
                       n_samples=prot.shape[1], n_features=prot.shape[0], status="ready", uploaded_by=user.id,
                       metadata_json={"metadata_file": str(meta_path), "source": "synthetic"}))

        # --- metabolomics ---
        met_genes = ["GLUCOSE", "LACTATE", "PYRUVATE", "CITRATE", "SUCCINATE", "FUMARATE", "MALATE",
                     "CHOLINE", "BETAINE", "DMG", "CREATINE", "CREATININE", "SERINE", "GLYCINE", "TAURINE",
                     "MYOINOSITOL", "ScylloINOSITOL", "NACETYLASPARTATE", "GLUTAMATE", "GABA",
                     "CARNITINE", "ACETYLCARNITINE", "TMAO", "TRYPTOPHAN", "KYNURENINE", "SEROTONIN"] + [f"M{i:04d}" for i in range(1, 200)]
        met = pd.DataFrame(rng.lognormal(0, 0.7, size=(len(met_genes), 80)), index=met_genes, columns=list(expr.columns))
        for g in ["GLUCOSE", "LACTATE", "SUCCINATE", "FUMARATE", "KYNURENINE", "ACETYLCARNITINE", "TMAO"]:
            met.loc[g, [c for c in met.columns if c.startswith("AD")]] *= rng.uniform(1.4, 2.2)
        for g in ["NACETYLASPARTATE", "CHOLINE", "SEROTONIN", "CARNITINE"]:
            met.loc[g, [c for c in met.columns if c.startswith("AD")]] *= rng.uniform(0.5, 0.75)
        met_path = media / "metabolomics.csv"
        met.to_csv(met_path)
        db.add(Dataset(project_id=project.id, name="Serum metabolomics (NMR)", omics_type="metabolomics",
                       platform="NMR", file_path=str(met_path), format="csv",
                       n_samples=met.shape[1], n_features=met.shape[0], status="ready", uploaded_by=user.id,
                       metadata_json={"metadata_file": str(meta_path), "source": "synthetic"}))
        db.commit()
        logger.info("seeded demo project %s (%s) with 3 datasets", project.name, project.id)

        # --- pre-run a couple of analyses so dashboards are populated ---
        from app.workers.tasks import run_analysis_task

        analysis = Analysis(project_id=project.id, name="DE: AD vs CN (transcriptomics)",
                            analysis_type="differential_expression", owner_id=user.id, status="queued",
                            config={"dataset_id": ds_rna.id, "case_group": "AD", "control_group": "CN"})
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        try:
            run_analysis_task.run(analysis.id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed analysis failed: %s", exc)

        drug_result = run_drug_pipeline_for_seed()
        if drug_result:
            from app.models.drug import DrugCandidate

            for i, c in enumerate(drug_result["candidates"][:12], start=1):
                db.add(DrugCandidate(project_id=project.id, drug_name=c["drug_name"],
                                     drugbank_id=c.get("drugbank_id", ""), chebi_id=c.get("chebi_id", ""),
                                     pubchem_cid=c.get("pubchem_cid", ""), mol_weight=c.get("mw", 0.0),
                                     mechanism=c.get("mechanism", ""), targets=c.get("targets", []),
                                     indication=c.get("indication", ""), fda_status=c.get("fda_status", ""),
                                     evidence_sources=c.get("evidence_sources", []),
                                     score_network=c["scores"]["network"], score_pathway_reversal=c["scores"]["pathway_reversal"],
                                     score_target_overlap=c["scores"]["target_overlap"], score_bbb=c["scores"]["bbb"],
                                     score_admet=c["scores"]["admet"], score_clinical=c["scores"]["clinical"],
                                     composite_score=c["composite_score"], rank=i,
                                     details={"rationale": c.get("evidence", [])}))
            db.commit()
            logger.info("seeded %d drug candidates", len(drug_result["candidates"][:12]))

        print(f"\n✅ Demo seeded.\n   Login: demo@neuroomics.org / demo12345 (or admin@neuroomics.org / admin12345)\n"
              f"   Project: {project.name}")
    finally:
        db.close()


def run_drug_pipeline_for_seed() -> dict | None:
    try:
        from app.drugs.pipeline import run_drug_pipeline

        return run_drug_pipeline(["APP", "BACE1", "IL1B", "TNF", "IL6", "TREM2", "TYROBP", "APOE",
                                  "MAPT", "GSK3B", "MTOR", "BECN1", "HMOX1", "NFE2L2", "SOD1"], max_candidates=15)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning("drug seed failed: %s", exc)
        return None


if __name__ == "__main__":
    seed()
