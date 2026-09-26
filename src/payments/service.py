"""
HC-XCDSS Payment Service & Ledger Engine

Handles checkout sessions, state machine validation, double-entry ledger bookkeeping,
platform fee calculation, and professional earnings allocation.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

logger = logging.getLogger("hc_xcdss.payments")

from ..db.models.payment import (
    Payment,
    PaymentStatus,
    LedgerEntryType,
    PaymentLedgerEntry,
    ProfessionalEarning,
    EarningStatus,
)
from ..db.models.review_request import ReviewRequest, ReviewStatus
from ..db.models.user import User, UserRole
from ..db.models.notification import NotificationType, NotificationEntityType
from ..notifications.service import NotificationService
from ..notifications.email_service import EmailService
from .catalog import get_service_or_raise, SERVICE_CATALOG
from .providers import get_payment_provider, BasePaymentProvider


# Allowed transitions in Payment State Machine
VALID_TRANSITIONS: Dict[PaymentStatus, List[PaymentStatus]] = {
    PaymentStatus.PENDING: [PaymentStatus.CHECKOUT_CREATED, PaymentStatus.FAILED, PaymentStatus.CANCELLED],
    PaymentStatus.CHECKOUT_CREATED: [PaymentStatus.AUTHORIZED, PaymentStatus.PAID, PaymentStatus.FAILED, PaymentStatus.CANCELLED],
    PaymentStatus.AUTHORIZED: [PaymentStatus.PAID, PaymentStatus.FAILED, PaymentStatus.CANCELLED],
    PaymentStatus.PAID: [PaymentStatus.REFUNDED],
    PaymentStatus.FAILED: [],
    PaymentStatus.CANCELLED: [],
    PaymentStatus.REFUNDED: [],
}


class PaymentService:
    """
    Centralized Payment and Financial Ledger Service.
    """

    @staticmethod
    def validate_transition(current_status: PaymentStatus, target_status: PaymentStatus) -> bool:
        allowed = VALID_TRANSITIONS.get(current_status, [])
        return target_status in allowed

    @staticmethod
    def create_checkout(
        db: Session,
        patient: User,
        review_request_id: str,
        service_id: str = "XRAY_PROFESSIONAL_REVIEW",
        idempotency_key: Optional[str] = None,
        provider: Optional[BasePaymentProvider] = None,
    ) -> Payment:
        """
        Creates a checkout session for a review request.
        Guarantees backend price authority, ownership checks, and idempotency.
        """
        if idempotency_key:
            existing_key_pay = db.query(Payment).filter(Payment.idempotency_key == idempotency_key).first()
            if existing_key_pay:
                return existing_key_pay

        # 1. Verify review request exists and belongs to patient
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_request_id).first()
        if not req:
            raise ValueError(f"Review request '{review_request_id}' not found.")
        if req.patient_id != patient.id:
            raise ValueError("Access denied: You do not own this review request.")

        # Check if already paid
        if req.payment_status == "PAID":
            existing_paid = db.query(Payment).filter(
                Payment.review_request_id == review_request_id,
                Payment.status == PaymentStatus.PAID
            ).first()
            if existing_paid:
                return existing_paid

        # 2. Check catalog definition & resolve specialist consultation fee
        service = get_service_or_raise(service_id)
        amount_minor = service.amount_minor
        currency = service.currency

        # If a specific verified specialist was selected, resolve fee securely from database profile
        if req.professional_id:
            from ..db.models.professional_profile import ProfessionalProfile
            pro_profile = db.query(ProfessionalProfile).filter(ProfessionalProfile.user_id == req.professional_id).first()
            if pro_profile and pro_profile.consultation_fee is not None and pro_profile.consultation_fee > 0:
                amount_minor = int(round(pro_profile.consultation_fee * 100))

        # 3. Create or reuse active pending payment record
        existing_pay = (
            db.query(Payment)
            .filter(
                Payment.review_request_id == review_request_id,
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.CHECKOUT_CREATED]),
            )
            .first()
        )

        pay_provider = provider or get_payment_provider()
        prov_name = getattr(pay_provider, "provider_name", "mock")

        if not existing_pay:
            existing_pay = Payment(
                user_id=patient.id,
                review_request_id=review_request_id,
                service_id=service.service_id,
                provider=prov_name,
                amount_minor=amount_minor,
                currency=currency,
                status=PaymentStatus.PENDING,
                idempotency_key=idempotency_key,
            )
            db.add(existing_pay)
            db.commit()
            db.refresh(existing_pay)
        else:
            existing_pay.provider = prov_name
            existing_pay.amount_minor = amount_minor

        # 4. Generate provider checkout session
        session_result = pay_provider.create_checkout_session(
            payment_id=existing_pay.id,
            amount_minor=amount_minor,
            currency=currency,
            customer_email=patient.email,
            service_name=service.name,
            metadata={"review_request_id": review_request_id, "patient_id": patient.id, "professional_id": req.professional_id or ""},
        )

        existing_pay.provider_payment_id = session_result.provider_payment_id
        existing_pay.checkout_url = session_result.checkout_url
        existing_pay.status = PaymentStatus.CHECKOUT_CREATED
        db.commit()
        db.refresh(existing_pay)

        # Trigger notification
        try:
            NotificationService.create_notification(
                db=db,
                user_id=patient.id,
                notification_type=NotificationType.PAYMENT_CHECKOUT_CREATED,
                title="Review Consultation Checkout Ready",
                message=f"Checkout session created for {service.name} (₹{amount_minor / 100:.2f}).",
                entity_type=NotificationEntityType.PAYMENT,
                entity_id=existing_pay.id,
            )
        except Exception as e:
            print(f"Payment notification warning: {e}")

        return existing_pay

    @staticmethod
    def process_payment_success(
        db: Session,
        payment_id: str,
        provider_payment_id: Optional[str] = None,
    ) -> Payment:
        """
        Executes idempotent payment success handling:
        1. Transitions payment status to PAID.
        2. Appends immutable ledger entry (PATIENT_PAYMENT).
        3. Authorizes ReviewRequest (payment_status='PAID').
        4. If specific specialist chosen: assigns and notifies assigned doctor.
           If Any Doctor: transitions to open matching pool.
        5. Fires PAYMENT_SUCCESSFUL notification.
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError(f"Payment '{payment_id}' not found.")

        # Idempotency guard: If already marked PAID, return existing without double-booking
        if payment.status == PaymentStatus.PAID:
            return payment

        if not PaymentService.validate_transition(payment.status, PaymentStatus.PAID):
            raise ValueError(f"Cannot transition payment from {payment.status.value} to PAID.")

        now_dt = datetime.now(timezone.utc)
        payment.status = PaymentStatus.PAID
        if provider_payment_id:
            payment.provider_payment_id = provider_payment_id
        payment.updated_at = now_dt

        # Append to financial ledger (Immutable Ledger Entry)
        ledger_entry = PaymentLedgerEntry(
            payment_id=payment.id,
            entry_type=LedgerEntryType.PATIENT_PAYMENT,
            amount_minor=payment.amount_minor,
            currency=payment.currency,
            description=f"Patient consultation payment for review #{payment.review_request_id[:8]}",
            created_at=now_dt,
        )
        db.add(ledger_entry)

        # Financially authorize ReviewRequest and handle assignment routing
        req = db.query(ReviewRequest).filter(ReviewRequest.id == payment.review_request_id).first()
        if req:
            req.payment_status = "PAID"
            
            # MODE A: Specific Doctor Selected
            if req.professional_id:
                req.status = ReviewStatus.ASSIGNED
                if not req.assigned_at:
                    req.assigned_at = now_dt
                
                # Notify the specifically selected doctor of paid review assignment
                try:
                    NotificationService.on_review_requested(db, req.professional_id, req.id, req.analysis_id)
                    pro_user = db.query(User).filter(User.id == req.professional_id).first()
                    pro_name = pro_user.full_name if pro_user and pro_user.full_name else "Dr. Specialist"
                    NotificationService.on_review_assigned(db, req.patient_id, req.id, pro_name)

                    # Trigger transactional email to assigned professional (Idempotent per successful payment)
                    patient_user = db.query(User).filter(User.id == req.patient_id).first()
                    patient_name = patient_user.full_name if patient_user and patient_user.full_name else "Patient"
                    if pro_user and pro_user.email:
                        email_sent = EmailService.notify_professional_review_assigned(
                            professional_email=pro_user.email,
                            professional_name=pro_name,
                            patient_name=patient_name,
                            review_id=req.id,
                            analysis_id=req.analysis_id,
                        )
                        if email_sent:
                            logger.info(f"[PaymentService] Successfully dispatched professional assignment email to '{pro_user.email}' for review #{req.id}")
                        else:
                            logger.warning(f"[PaymentService] Professional assignment email to '{pro_user.email}' for review #{req.id} was not delivered by SMTP service.")
                except Exception as notif_err:
                    logger.error(f"[PaymentService:ERROR] Professional assignment notification failure for review #{req.id}: {notif_err}", exc_info=True)
            
            # MODE B: Any Available Doctor (Open Matching Pool)
            else:
                if req.status == ReviewStatus.REQUESTED:
                    req.status = ReviewStatus.MATCHING

        db.commit()
        db.refresh(payment)

        # Notify Patient
        try:
            NotificationService.create_notification(
                db=db,
                user_id=payment.user_id,
                notification_type=NotificationType.PAYMENT_SUCCESSFUL,
                title="Payment Successful",
                message="Your professional review consultation payment was successful. A doctor will review your case shortly.",
                entity_type=NotificationEntityType.PAYMENT,
                entity_id=payment.id,
            )
        except Exception as e:
            print(f"Payment notification warning: {e}")

        return payment

    @staticmethod
    def process_payment_failure(
        db: Session,
        payment_id: str,
        reason: Optional[str] = None,
    ) -> Payment:
        """
        Executes payment failure transition.
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError(f"Payment '{payment_id}' not found.")

        if payment.status in [PaymentStatus.PAID, PaymentStatus.REFUNDED]:
            return payment

        payment.status = PaymentStatus.FAILED
        payment.updated_at = datetime.now(timezone.utc)

        # Mark review payment as FAILED
        req = db.query(ReviewRequest).filter(ReviewRequest.id == payment.review_request_id).first()
        if req and req.payment_status != "PAID":
            req.payment_status = "FAILED"

        db.commit()
        db.refresh(payment)

        # Notify Patient
        try:
            NotificationService.create_notification(
                db=db,
                user_id=payment.user_id,
                notification_type=NotificationType.PAYMENT_FAILED,
                title="Payment Unsuccessful",
                message=reason or "Your review consultation payment could not be processed.",
                entity_type=NotificationEntityType.PAYMENT,
                entity_id=payment.id,
            )
        except Exception as e:
            print(f"Payment notification warning: {e}")

        return payment

    @staticmethod
    def record_professional_earning(
        db: Session,
        review_request_id: str,
        professional_id: str,
    ) -> Optional[ProfessionalEarning]:
        """
        Calculates platform fee split and creates immutable ProfessionalEarning record
        when doctor completes a review.
        """
        # Find corresponding paid payment
        payment = (
            db.query(Payment)
            .filter(
                Payment.review_request_id == review_request_id,
                Payment.status == PaymentStatus.PAID,
            )
            .first()
        )

        gross_minor = payment.amount_minor if payment else 49900  # Fallback to standard catalog price
        currency = payment.currency if payment else "INR"
        service = SERVICE_CATALOG.get(payment.service_id if payment else "XRAY_PROFESSIONAL_REVIEW")
        fee_pct = service.platform_fee_percent if service else 20.0

        # Decimal-safe fee calculation (integer rounding)
        platform_fee_minor = int(
            (Decimal(gross_minor) * Decimal(str(fee_pct)) / Decimal("100")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        net_minor = gross_minor - platform_fee_minor

        # Check existing earning
        existing_earn = (
            db.query(ProfessionalEarning)
            .filter(ProfessionalEarning.review_request_id == review_request_id)
            .first()
        )
        if existing_earn:
            return existing_earn

        now_dt = datetime.now(timezone.utc)
        earning = ProfessionalEarning(
            professional_id=professional_id,
            review_request_id=review_request_id,
            payment_id=payment.id if payment else None,
            gross_amount_minor=gross_minor,
            platform_fee_minor=platform_fee_minor,
            net_amount_minor=net_minor,
            currency=currency,
            status=EarningStatus.AVAILABLE,
            created_at=now_dt,
        )
        db.add(earning)

        # Add Ledger Entries
        if payment:
            db.add(
                PaymentLedgerEntry(
                    payment_id=payment.id,
                    entry_type=LedgerEntryType.PLATFORM_FEE,
                    amount_minor=platform_fee_minor,
                    currency=currency,
                    description=f"Platform commission ({fee_pct}%) on review #{review_request_id[:8]}",
                    created_at=now_dt,
                )
            )
            db.add(
                PaymentLedgerEntry(
                    payment_id=payment.id,
                    entry_type=LedgerEntryType.PROFESSIONAL_EARNING,
                    amount_minor=net_minor,
                    currency=currency,
                    description=f"Physician net earnings payable for review #{review_request_id[:8]}",
                    created_at=now_dt,
                )
            )

        db.commit()
        db.refresh(earning)
        return earning

    @staticmethod
    def process_refund(
        db: Session,
        payment_id: str,
        actor: User,
        reason: Optional[str] = None,
        provider: Optional[BasePaymentProvider] = None,
    ) -> Payment:
        """
        Executes refund with role validation (Admin only or verified workflow).
        """
        if actor.role != UserRole.ADMIN:
            raise ValueError("Unauthorized: Only administrators can initiate refunds.")

        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError(f"Payment '{payment_id}' not found.")

        if payment.status != PaymentStatus.PAID:
            raise ValueError(f"Cannot refund a payment with status '{payment.status.value}'.")

        pay_provider = provider or get_payment_provider()
        ref_result = pay_provider.refund_payment(
            provider_payment_id=payment.provider_payment_id or "mock",
            amount_minor=payment.amount_minor,
            reason=reason,
        )

        if not ref_result.is_success:
            raise ValueError(f"Provider refund failed: {ref_result.error_message}")

        now_dt = datetime.now(timezone.utc)
        payment.status = PaymentStatus.REFUNDED
        payment.updated_at = now_dt

        # Ledger Entry (REFUND)
        db.add(
            PaymentLedgerEntry(
                payment_id=payment.id,
                entry_type=LedgerEntryType.REFUND,
                amount_minor=-payment.amount_minor,
                currency=payment.currency,
                description=f"Refund issued for payment #{payment.id[:8]}. Reason: {reason or 'Administrative'}",
                created_at=now_dt,
            )
        )

        # Mark review payment status
        req = db.query(ReviewRequest).filter(ReviewRequest.id == payment.review_request_id).first()
        if req:
            req.payment_status = "REFUNDED"

        # Reverse professional earnings if any
        earning = db.query(ProfessionalEarning).filter(ProfessionalEarning.payment_id == payment.id).first()
        if earning:
            earning.status = EarningStatus.REVERSED

        db.commit()
        db.refresh(payment)

        # Notify Patient
        try:
            NotificationService.create_notification(
                db=db,
                user_id=payment.user_id,
                notification_type=NotificationType.REFUND_COMPLETED,
                title="Refund Processed",
                message="Your consultation payment refund has been processed.",
                entity_type=NotificationEntityType.PAYMENT,
                entity_id=payment.id,
            )
        except Exception as e:
            print(f"Payment notification warning: {e}")

        return payment
