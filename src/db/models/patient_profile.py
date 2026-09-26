"""
HC-XCDSS Patient Profile Model
"""

import uuid
from typing import Optional
from datetime import datetime, timezone, date
from sqlalchemy import String, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

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
    phone: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    location_city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    location_state: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    location_country: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    date_of_birth: Mapped[Optional[date]] = mapped_column(
        Date,
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
        back_populates="patient_profile",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "phone": self.phone,
            "location_city": self.location_city,
            "location_state": self.location_state,
            "location_country": self.location_country,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
