"""
HC-XCDSS Payment, Ledger & Professional Earnings Database Models
"""

import enum
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    CHECKOUT_CREATED = "CHECKOUT_CREATED"
    AUTHORIZED = "AUTHORIZED"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class LedgerEntryType(str, enum.Enum):
    PATIENT_PAYMENT = "PATIENT_PAYMENT"
    PLATFORM_FEE = "PLATFORM_FEE"
    PROFESSIONAL_EARNING = "PROFESSIONAL_EARNING"
    REFUND = "REFUND"


class EarningStatus(str, enum.Enum):
    PENDING = "PENDING"
    AVAILABLE = "AVAILABLE"
    PAID = "PAID"
    REVERSED = "REVERSED"


class Payment(Base):
    __tablename__ = "payments"

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
    review_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("review_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="XRAY_PROFESSIONAL_REVIEW",
    )
    provider: Mapped[str] = mapped_column(
        String(32),
        default="mock",
        nullable=False,
    )
    provider_payment_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )
    amount_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(8),
        default="INR",
        nullable=False,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True,
    )
    checkout_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
        index=True,
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
    user = relationship("User", backref="payments")
    review_request = relationship("ReviewRequest", backref="payments")
    ledger_entries = relationship("PaymentLedgerEntry", back_populates="payment", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "payment_id": self.id,
            "user_id": self.user_id,
            "review_request_id": self.review_request_id,
            "service_id": self.service_id,
            "provider": self.provider,
            "provider_payment_id": self.provider_payment_id,
            "amount_minor": self.amount_minor,
            "amount_formatted": f"₹{self.amount_minor / 100:.2f}" if self.currency == "INR" else f"{self.amount_minor / 100:.2f} {self.currency}",
            "currency": self.currency,
            "status": self.status.value if isinstance(self.status, PaymentStatus) else str(self.status),
            "checkout_url": self.checkout_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PaymentLedgerEntry(Base):
    __tablename__ = "payment_ledger_entries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    payment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_type: Mapped[LedgerEntryType] = mapped_column(
        Enum(LedgerEntryType),
        nullable=False,
        index=True,
    )
    amount_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(8),
        default="INR",
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    payment = relationship("Payment", back_populates="ledger_entries")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "entry_type": self.entry_type.value if isinstance(self.entry_type, LedgerEntryType) else str(self.entry_type),
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ProfessionalEarning(Base):
    __tablename__ = "professional_earnings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    professional_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    review_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("review_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    gross_amount_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    platform_fee_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    net_amount_minor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(8),
        default="INR",
        nullable=False,
    )
    status: Mapped[EarningStatus] = mapped_column(
        Enum(EarningStatus),
        default=EarningStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    professional = relationship("User", foreign_keys=[professional_id])
    review_request = relationship("ReviewRequest", foreign_keys=[review_request_id])
    payment = relationship("Payment", foreign_keys=[payment_id])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "professional_id": self.professional_id,
            "review_request_id": self.review_request_id,
            "payment_id": self.payment_id,
            "gross_amount_minor": self.gross_amount_minor,
            "platform_fee_minor": self.platform_fee_minor,
            "net_amount_minor": self.net_amount_minor,
            "currency": self.currency,
            "status": self.status.value if isinstance(self.status, EarningStatus) else str(self.status),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
