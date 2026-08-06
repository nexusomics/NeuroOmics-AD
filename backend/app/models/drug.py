"""Drug candidate model for repurposing results."""
from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class DrugCandidate(Base):
    __tablename__ = "drug_candidates"

    id = Column(String(36), primary_key=True, default=_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    drug_name = Column(String(255), nullable=False)
    drugbank_id = Column(String(32), default="")
    chebi_id = Column(String(32), default="")
    pubchem_cid = Column(String(32), default="")
    mol_formula = Column(String(64), default="")
    mol_weight = Column(Float, default=0.0)
    mechanism = Column(Text, default="")
    targets = Column(JSON, default=list)  # list of gene symbols
    indication = Column(String(255), default="")
    fda_status = Column(String(64), default="")  # Approved | Investigational | Experimental
    evidence_sources = Column(JSON, default=list)

    # composite ranking scores
    score_network = Column(Float, default=0.0)
    score_pathway_reversal = Column(Float, default=0.0)
    score_target_overlap = Column(Float, default=0.0)
    score_bbb = Column(Float, default=0.0)
    score_admet = Column(Float, default=0.0)
    score_clinical = Column(Float, default=0.0)
    composite_score = Column(Float, default=0.0)
    rank = Column(Integer, default=0)

    details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=dt.datetime.now(dt.timezone.utc))

    project = relationship("Project", back_populates="drug_candidates")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "drug_name": self.drug_name,
            "drugbank_id": self.drugbank_id,
            "chebi_id": self.chebi_id,
            "pubchem_cid": self.pubchem_cid,
            "mol_formula": self.mol_formula,
            "mol_weight": self.mol_weight,
            "mechanism": self.mechanism,
            "targets": self.targets or [],
            "indication": self.indication,
            "fda_status": self.fda_status,
            "evidence_sources": self.evidence_sources or [],
            "score_network": self.score_network,
            "score_pathway_reversal": self.score_pathway_reversal,
            "score_target_overlap": self.score_target_overlap,
            "score_bbb": self.score_bbb,
            "score_admet": self.score_admet,
            "score_clinical": self.score_clinical,
            "composite_score": self.composite_score,
            "rank": self.rank,
            "details": self.details or {},
        }
