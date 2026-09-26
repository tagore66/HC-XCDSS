import os
import uuid
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pydantic import BaseModel


def _ensure_env_loaded():
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()


class CheckoutSessionResult(BaseModel):
    provider_payment_id: str
    checkout_url: str
    status: str
    raw_response: Dict[str, Any] = {}


class PaymentVerifyResult(BaseModel):
    is_success: bool
    status: str  # PAID, FAILED, CANCELLED
    provider_payment_id: str
    error_message: Optional[str] = None


class RefundResult(BaseModel):
    is_success: bool
    status: str  # REFUNDED, FAILED
    refund_id: str
    error_message: Optional[str] = None


class BasePaymentProvider(ABC):
    """
    Abstract payment gateway provider.
    """

    @abstractmethod
    def create_checkout_session(
        self,
        payment_id: str,
        amount_minor: int,
        currency: str,
        customer_email: str,
        service_name: str,
        metadata: Dict[str, Any],
    ) -> CheckoutSessionResult:
        pass

    @abstractmethod
    def get_payment_status(self, provider_payment_id: str) -> str:
        pass

    @abstractmethod
    def verify_payment(self, provider_payment_id: str, payload: Dict[str, Any]) -> PaymentVerifyResult:
        pass

    @abstractmethod
    def refund_payment(self, provider_payment_id: str, amount_minor: int, reason: Optional[str] = None) -> RefundResult:
        pass


class MockPaymentProvider(BasePaymentProvider):
    """
    Deterministic Mock / Test Payment Provider for offline testmode simulation.
    """
    provider_name: str = "mock"

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def create_checkout_session(
        self,
        payment_id: str,
        amount_minor: int,
        currency: str,
        customer_email: str,
        service_name: str,
        metadata: Dict[str, Any],
    ) -> CheckoutSessionResult:
        prov_id = f"mock_pay_{uuid.uuid4().hex[:12]}"
        checkout_url = f"/api/payments/mock-checkout?session_id={prov_id}&payment_id={payment_id}"
        self.sessions[prov_id] = {
            "payment_id": payment_id,
            "amount_minor": amount_minor,
            "currency": currency,
            "customer_email": customer_email,
            "service_name": service_name,
            "status": "CHECKOUT_CREATED",
            "metadata": metadata,
        }
        return CheckoutSessionResult(
            provider_payment_id=prov_id,
            checkout_url=checkout_url,
            status="CHECKOUT_CREATED",
            raw_response={"simulated": True, "provider": "mock"},
        )

    def get_payment_status(self, provider_payment_id: str) -> str:
        session = self.sessions.get(provider_payment_id)
        if not session:
            return "NOT_FOUND"
        return session.get("status", "CHECKOUT_CREATED")

    def verify_payment(self, provider_payment_id: str, payload: Dict[str, Any]) -> PaymentVerifyResult:
        # Mock payment verification: simulate success unless explicit action='fail' is passed
        action = payload.get("action", "success")
        if action == "fail":
            return PaymentVerifyResult(
                is_success=False,
                status="FAILED",
                provider_payment_id=provider_payment_id,
                error_message="Card declined by test simulator.",
            )
        return PaymentVerifyResult(
            is_success=True,
            status="PAID",
            provider_payment_id=provider_payment_id,
        )

    def refund_payment(self, provider_payment_id: str, amount_minor: int, reason: Optional[str] = None) -> RefundResult:
        return RefundResult(
            is_success=True,
            status="REFUNDED",
            refund_id=f"mock_ref_{uuid.uuid4().hex[:8]}",
        )


class StripePaymentProvider(BasePaymentProvider):
    """
    Stripe Payment Gateway Integration (Test & Production Modes).
    """
    provider_name: str = "stripe"

    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
        self.frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and (self.api_key.startswith("sk_test_") or self.api_key.startswith("sk_live_") or self.api_key.startswith("sk_")))

    def create_checkout_session(
        self,
        payment_id: str,
        amount_minor: int,
        currency: str,
        customer_email: str,
        service_name: str,
        metadata: Dict[str, Any],
    ) -> CheckoutSessionResult:
        if not self.is_configured:
            raise ValueError("Stripe API key is not configured in environment.")

        import stripe
        stripe.api_key = self.api_key

        clean_metadata = {k: str(v) for k, v in metadata.items()}
        clean_metadata["payment_id"] = str(payment_id)

        session_params: Dict[str, Any] = {
            "payment_method_types": ["card"],
            "line_items": [
                {
                    "price_data": {
                        "currency": currency.lower(),
                        "product_data": {
                            "name": service_name,
                            "description": f"HC-XCDSS Clinical Review Consultation (Ref: {payment_id[:8]})",
                        },
                        "unit_amount": int(amount_minor),
                    },
                    "quantity": 1,
                }
            ],
            "mode": "payment",
            "client_reference_id": str(payment_id),
            "metadata": clean_metadata,
            "success_url": f"{self.frontend_url}/?session_id={{CHECKOUT_SESSION_ID}}&payment_status=success",
            "cancel_url": f"{self.frontend_url}/?payment_status=cancelled",
        }
        if customer_email and "@" in customer_email:
            session_params["customer_email"] = customer_email

        session = stripe.checkout.Session.create(**session_params)

        return CheckoutSessionResult(
            provider_payment_id=session.id,
            checkout_url=session.url or "",
            status=session.status or "open",
            raw_response={
                "id": session.id,
                "payment_status": session.payment_status,
                "mode": session.mode,
            },
        )

    def get_payment_status(self, provider_payment_id: str) -> str:
        if not self.is_configured:
            return "NOT_CONFIGURED"

        import stripe
        stripe.api_key = self.api_key

        try:
            session = stripe.checkout.Session.retrieve(provider_payment_id)
            if session.payment_status == "paid":
                return "PAID"
            elif session.status == "expired":
                return "FAILED"
            elif session.payment_status == "unpaid":
                return "CHECKOUT_CREATED"
            return (session.status or "CHECKOUT_CREATED").upper()
        except Exception:
            return "UNKNOWN"

    def verify_payment(self, provider_payment_id: str, payload: Dict[str, Any]) -> PaymentVerifyResult:
        if not self.is_configured:
            return PaymentVerifyResult(
                is_success=False,
                status="FAILED",
                provider_payment_id=provider_payment_id,
                error_message="Stripe is not configured.",
            )

        import stripe
        stripe.api_key = self.api_key

        try:
            session = stripe.checkout.Session.retrieve(provider_payment_id)
            if session.payment_status == "paid":
                return PaymentVerifyResult(
                    is_success=True,
                    status="PAID",
                    provider_payment_id=provider_payment_id,
                )
            return PaymentVerifyResult(
                is_success=False,
                status="FAILED",
                provider_payment_id=provider_payment_id,
                error_message=f"Payment status is {session.payment_status}",
            )
        except Exception as e:
            return PaymentVerifyResult(
                is_success=False,
                status="FAILED",
                provider_payment_id=provider_payment_id,
                error_message=str(e),
            )

    def refund_payment(self, provider_payment_id: str, amount_minor: int, reason: Optional[str] = None) -> RefundResult:
        if not self.is_configured:
            return RefundResult(
                is_success=False,
                status="FAILED",
                refund_id="",
                error_message="Stripe is not configured.",
            )

        import stripe
        stripe.api_key = self.api_key

        try:
            payment_intent_id = provider_payment_id
            if provider_payment_id.startswith("cs_"):
                session = stripe.checkout.Session.retrieve(provider_payment_id)
                payment_intent_id = session.payment_intent

            if not payment_intent_id:
                return RefundResult(
                    is_success=False,
                    status="FAILED",
                    refund_id="",
                    error_message="Could not resolve Stripe PaymentIntent for refund.",
                )

            refund_params: Dict[str, Any] = {
                "payment_intent": payment_intent_id,
                "amount": int(amount_minor),
            }
            if reason in ["duplicate", "fraudulent", "requested_by_customer"]:
                refund_params["reason"] = reason

            refund = stripe.Refund.create(**refund_params)
            return RefundResult(
                is_success=True,
                status="REFUNDED",
                refund_id=refund.id,
            )
        except Exception as e:
            return RefundResult(
                is_success=False,
                status="FAILED",
                refund_id="",
                error_message=str(e),
            )


def get_payment_provider() -> BasePaymentProvider:
    """
    Factory to retrieve configured payment provider.
    Defaults safely to MockPaymentProvider.
    """
    _ensure_env_loaded()
    provider_name = os.getenv("PAYMENT_PROVIDER", "mock").strip().lower()
    if provider_name == "stripe":
        return StripePaymentProvider()
    return MockPaymentProvider()
