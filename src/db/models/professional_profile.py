"""
HC-XCDSS Professional Profile Model & Verification Status
"""

import enum
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Float, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class ProfessionalVerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class ProfessionalProfile(Base):
    __tablename__ = "professional_profiles"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    specialty: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    qualification: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    license_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    license_country_or_state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    hospital_or_clinic: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    location_city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    location_state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    location_country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    consultation_fee: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    verification_status: Mapped[ProfessionalVerificationStatus] = mapped_column(
        Enum(ProfessionalVerificationStatus),
        default=ProfessionalVerificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    # Extended Verification Fields (Milestone 1)
    registration_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    state_medical_council: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
    registration_year: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    registration_certificate_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    registration_certificate_filename: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    identity_document_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    identity_document_filename: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    supporting_document_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    supporting_document_filename: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    verification_submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text,
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
    user = relationship(
        "User",
        back_populates="professional_profile",
    )

    @property
    def has_registration_certificate(self) -> bool:
        return bool(self.registration_certificate_path)

    @property
    def has_identity_document(self) -> bool:
        return bool(self.identity_document_path)

    @property
    def has_supporting_document(self) -> bool:
        return bool(self.supporting_document_path)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "specialty": self.specialty,
            "qualification": self.qualification,
            "license_number": self.license_number or self.registration_number,
            "license_country_or_state": self.license_country_or_state or self.state_medical_council,
            "registration_number": self.registration_number or self.license_number,
            "state_medical_council": self.state_medical_council or self.license_country_or_state,
            "registration_year": self.registration_year,
            "has_registration_certificate": bool(self.registration_certificate_path),
            "registration_certificate_filename": self.registration_certificate_filename,
            "has_identity_document": bool(self.identity_document_path),
            "identity_document_filename": self.identity_document_filename,
            "has_supporting_document": bool(self.supporting_document_path),
            "supporting_document_filename": self.supporting_document_filename,
            "hospital_or_clinic": self.hospital_or_clinic,
            "location_city": self.location_city,
            "location_state": self.location_state,
            "location_country": self.location_country,
            "bio": self.bio,
            "consultation_fee": self.consultation_fee,
            "verification_status": (
                self.verification_status.value
                if isinstance(self.verification_status, ProfessionalVerificationStatus)
                else str(self.verification_status)
            ),
            "verification_submitted_at": self.verification_submitted_at.isoformat() if self.verification_submitted_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verified_by": self.verified_by,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
