"""
HC-XCDSS Payment Pydantic Schemas
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from ..db.models.payment import PaymentStatus, LedgerEntryType, EarningStatus


class CheckoutRequest(BaseModel):
    review_request_id: str = Field(..., description="ID of the review request to authorize")
    service_id: str = Field("XRAY_PROFESSIONAL_REVIEW", description="Service identifier from catalog")
    idempotency_key: Optional[str] = Field(None, description="Optional client idempotency key")


class CheckoutResponse(BaseModel):
    payment_id: str
    review_request_id: str
    service_id: str
    amount_minor: int
    amount_formatted: str
    currency: str
    status: PaymentStatus
    checkout_url: Optional[str] = None
    provider: str
    provider_payment_id: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    payment_id: str
    review_request_id: str
    status: PaymentStatus
    amount_minor: int
    amount_formatted: str
    currency: str
    provider_payment_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VerifySessionPayload(BaseModel):
    session_id: str = Field(..., description="Stripe checkout session_id or mock payment_id")


class WebhookSimulateRequest(BaseModel):
    payment_id: str
    action: str = Field("success", description="'success' or 'fail'")


class RefundRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for refund")


class RefundResponse(BaseModel):
    success: bool
    payment_id: str
    status: PaymentStatus
    refund_amount_minor: int
    message: str


class ProfessionalEarningResponse(BaseModel):
    id: str
    professional_id: str
    review_request_id: str
    payment_id: Optional[str] = None
    gross_amount_minor: int
    platform_fee_minor: int
    net_amount_minor: int
    currency: str
    status: EarningStatus
    created_at: Optional[datetime] = None
