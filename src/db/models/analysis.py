"""
HC-XCDSS Analysis Model
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class Analysis(Base):
    __tablename__ = "analyses"

    # Preserving the unique 12-character analysis ID
    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    view: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="Frontal",
    )
    image_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    findings_raw: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    detected_findings: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    heatmaps: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    patient_explanations: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="analyses",
    )
    report = relationship(
        "Report",
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan",
    )
    review_requests = relationship(
        "ReviewRequest",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    ai_context = relationship(
        "AIContext",
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan",
    )
    conversations = relationship(
        "Conversation",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Exports analysis dictionary strictly conforming to existing API response contracts.
        """
        data: Dict[str, Any] = {
            "analysis_id": self.id,
            "user_id": self.user_id,
            "view": self.view,
            "image": self.image_path,
            "findings": self.findings_raw or {},
            "detected_findings": self.detected_findings or [],
            "heatmaps": self.heatmaps or {},
            "patient_explanations": self.patient_explanations or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        if self.report:
            data["report"] = self.report.to_dict()

        return data
