"""
HC-XCDSS Review Request & Professional Review Database Models
"""

import enum
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class ReviewStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    MATCHING = "MATCHING"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    IN_REVIEW = "IN_REVIEW"
    RESPONDED = "RESPONDED"
    COMPLETED = "COMPLETED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class ReviewRequest(Base):
    __tablename__ = "review_requests"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    analysis_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    professional_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus),
        default=ReviewStatus.REQUESTED,
        nullable=False,
        index=True,
    )
    patient_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    requested_information: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    patient_additional_info: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    payment_status: Mapped[str] = mapped_column(
        String(32),
        default="UNPAID",
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    declined_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis = relationship(
        "Analysis",
        back_populates="review_requests",
    )
    patient = relationship(
        "User",
        foreign_keys=[patient_id],
        back_populates="patient_review_requests",
    )
    professional = relationship(
        "User",
        foreign_keys=[professional_id],
        back_populates="professional_review_requests",
    )
    professional_review = relationship(
        "ProfessionalReview",
        back_populates="review_request",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "patient_id": self.patient_id,
            "professional_id": self.professional_id,
            "status": self.status.value if isinstance(self.status, ReviewStatus) else str(self.status),
            "patient_message": self.patient_message,
            "requested_information": self.requested_information,
            "patient_additional_info": self.patient_additional_info,
            "payment_status": self.payment_status,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "declined_at": self.declined_at.isoformat() if self.declined_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProfessionalReview(Base):
    __tablename__ = "professional_reviews"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    review_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("review_requests.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    professional_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    clinical_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    clinical_impression: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    finding_validations: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
    )
    professional_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    recommendations: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    limitations: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    urgency: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        default="ROUTINE",
    )
    follow_up_required: Mapped[Optional[bool]] = mapped_column(
        nullable=True,
        default=False,
    )
    message_to_patient: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    review_request = relationship(
        "ReviewRequest",
        back_populates="professional_review",
    )
    professional = relationship(
        "User",
        back_populates="professional_reviews",
    )

    @property
    def clinical_observations(self) -> Optional[str]:
        return self.clinical_summary or self.assessment

    @property
    def professional_impression(self) -> Optional[str]:
        return self.clinical_impression or self.clinical_summary or self.assessment

    @property
    def additional_notes(self) -> Optional[str]:
        return self.professional_notes

    @property
    def follow_up(self) -> bool:
        return bool(self.follow_up_required)

    @property
    def completed_at(self) -> Optional[datetime]:
        if self.review_request and self.review_request.completed_at:
            return self.review_request.completed_at
        if self.review_request and self.review_request.status == ReviewStatus.COMPLETED:
            return self.reviewed_at
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "review_request_id": self.review_request_id,
            "professional_id": self.professional_id,
            "assessment": self.assessment or self.clinical_summary,
            "clinical_summary": self.clinical_summary,
            "clinical_observations": self.clinical_summary or self.assessment,
            "clinical_impression": self.clinical_impression or self.clinical_summary,
            "professional_impression": self.clinical_impression or self.clinical_summary,
            "finding_validations": self.finding_validations or {},
            "professional_notes": self.professional_notes,
            "additional_notes": self.professional_notes,
            "recommendations": self.recommendations,
            "limitations": self.limitations,
            "urgency": self.urgency or "ROUTINE",
            "follow_up_required": bool(self.follow_up_required),
            "follow_up": bool(self.follow_up_required),
            "message_to_patient": self.message_to_patient or self.recommendations,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

