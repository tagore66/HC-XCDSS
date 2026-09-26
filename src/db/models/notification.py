"""
HC-XCDSS Notification Database Model
"""

import enum
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class NotificationType(str, enum.Enum):
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    REVIEW_REQUEST_CREATED = "REVIEW_REQUEST_CREATED"
    REVIEW_REQUEST_ASSIGNED = "REVIEW_REQUEST_ASSIGNED"
    REVIEW_REQUEST_ACCEPTED = "REVIEW_REQUEST_ACCEPTED"
    REVIEW_STARTED = "REVIEW_STARTED"
    INFORMATION_REQUESTED = "INFORMATION_REQUESTED"
    INFORMATION_PROVIDED = "INFORMATION_PROVIDED"
    REVIEW_COMPLETED = "REVIEW_COMPLETED"
    REVIEW_CANCELLED = "REVIEW_CANCELLED"
    AI_ASSISTANT_RESPONSE = "AI_ASSISTANT_RESPONSE"
    PAYMENT_CHECKOUT_CREATED = "PAYMENT_CHECKOUT_CREATED"
    PAYMENT_SUCCESSFUL = "PAYMENT_SUCCESSFUL"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    REFUND_COMPLETED = "REFUND_COMPLETED"
    PROFESSIONAL_REGISTERED = "PROFESSIONAL_REGISTERED"
    PROFESSIONAL_VERIFIED = "PROFESSIONAL_VERIFIED"
    PROFESSIONAL_REJECTED = "PROFESSIONAL_REJECTED"


class NotificationEntityType(str, enum.Enum):
    ANALYSIS = "ANALYSIS"
    REVIEW_REQUEST = "REVIEW_REQUEST"
    PROFESSIONAL_REVIEW = "PROFESSIONAL_REVIEW"
    CONVERSATION = "CONVERSATION"
    PAYMENT = "PAYMENT"
    USER = "USER"
    PROFESSIONAL_PROFILE = "PROFESSIONAL_PROFILE"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    entity_type: Mapped[NotificationEntityType] = mapped_column(
        Enum(NotificationEntityType),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user = relationship(
        "User",
        back_populates="notifications",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type.value if isinstance(self.type, NotificationType) else str(self.type),
            "title": self.title,
            "message": self.message,
            "entity_type": self.entity_type.value if isinstance(self.entity_type, NotificationEntityType) else str(self.entity_type),
            "entity_id": self.entity_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }
