"""
HC-XCDSS Report Model
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    analysis_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    overall_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    findings_evaluated: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    findings_detected: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    total_evaluated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_detected: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    patient_interpretation: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    explainability: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    clinical_disclaimer: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis = relationship(
        "Analysis",
        back_populates="report",
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Exports structured report strictly conforming to the Report Engine schema.
        """
        return {
            "analysis_id": self.analysis_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "view": self.analysis.view if self.analysis else "Frontal",
            "image": self.analysis.image_path if self.analysis else None,
            "findings_evaluated": self.findings_evaluated or [],
            "findings_detected": self.findings_detected or [],
            "total_evaluated": self.total_evaluated,
            "total_detected": self.total_detected,
            "overall_summary": self.overall_summary,
            "patient_interpretation": self.patient_interpretation or {},
            "explainability": self.explainability or {},
            "clinical_disclaimer": self.clinical_disclaimer or {},
        }
