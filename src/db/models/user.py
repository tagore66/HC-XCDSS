"""
HC-XCDSS User Model & Roles
"""

import enum
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class UserRole(str, enum.Enum):
    PATIENT = "PATIENT"
    PROFESSIONAL = "PROFESSIONAL"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.PATIENT,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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
    analyses = relationship(
        "Analysis",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    patient_profile = relationship(
        "PatientProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    professional_profile = relationship(
        "ProfessionalProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    patient_review_requests = relationship(
        "ReviewRequest",
        foreign_keys="ReviewRequest.patient_id",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    professional_review_requests = relationship(
        "ReviewRequest",
        foreign_keys="ReviewRequest.professional_id",
        back_populates="professional",
    )
    professional_reviews = relationship(
        "ProfessionalReview",
        back_populates="professional",
        cascade="all, delete-orphan",
    )
    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Notification.created_at.desc()",
    )

    def get_display_name(self) -> str:
        if self.full_name and self.full_name.strip():
            name = self.full_name.strip()
            if self.role == UserRole.PROFESSIONAL:
                if not name.lower().startswith("dr.") and not name.lower().startswith("dr "):
                    return f"Dr. {name}"
            return name
        if self.username and self.username.strip():
            return self.username.strip()
        return self.email.split("@")[0] if self.email else "User"

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "display_name": self.get_display_name(),
            "role": self.role.value if isinstance(self.role, UserRole) else str(self.role),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
