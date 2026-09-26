"""
Unit and regression tests for professional review assignment transactional emails and idempotency.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models.user import User, UserRole
from src.db.models.analysis import Analysis
from src.db.models.review_request import ReviewRequest, ReviewStatus
from src.db.models.professional_profile import ProfessionalProfile, ProfessionalVerificationStatus
from src.db.models.payment import Payment, PaymentStatus
from src.db.models.notification import Notification
from src.reviews.service import ReviewService
from src.payments.service import PaymentService
from src.notifications.email_service import EmailService


class TestProfessionalEmailNotifications(unittest.TestCase):
    def setUp(self):
        # In-memory isolated SQLite database
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.Session()

        # Seed test patient
        self.patient = User(
            id="test-patient-email",
            email="patient@example.com",
            role=UserRole.PATIENT,
            is_active=True,
            full_name="Jane Patient",
        )
        self.db.add(self.patient)

        # Seed test verified doctor
        self.doctor = User(
            id="test-doctor-email",
            email="dr.specialist@example.com",
            role=UserRole.PROFESSIONAL,
            is_active=True,
            full_name="Dr. Specialist MD",
        )
        self.db.add(self.doctor)

        doctor_profile = ProfessionalProfile(
            user_id=self.doctor.id,
            verification_status=ProfessionalVerificationStatus.VERIFIED,
            license_number="LIC-EMAIL-01",
            specialty="Radiology",
        )
        self.db.add(doctor_profile)

        # Seed test analysis
        self.analysis = Analysis(
            id="analysis-em-001",
            user_id=self.patient.id,
            image_path="/outputs/xray.jpg",
            view="Frontal",
            findings_raw={"Effusion": 0.82},
            detected_findings=["Effusion"],
            heatmaps={},
            patient_explanations=[],
        )
        self.db.add(self.analysis)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    @patch.object(EmailService, "send_email", return_value=True)
    def test_assigned_doctor_receives_email_after_successful_payment(self, mock_send_email):
        # 1. Create review request directly assigning Doctor
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-em-001",
            preferred_professional_id=self.doctor.id,
            patient_message="Please review my X-ray for effusion.",
        )
        self.assertEqual(req.payment_status, "UNPAID")
        self.assertEqual(req.professional_id, self.doctor.id)

        # 2. Create Payment checkout record
        payment = Payment(
            id="pay-test-001",
            user_id=self.patient.id,
            review_request_id=req.id,
            service_id="XRAY_PROFESSIONAL_REVIEW",
            amount_minor=49900,
            currency="INR",
            status=PaymentStatus.CHECKOUT_CREATED,
        )
        self.db.add(payment)
        self.db.commit()

        # 3. Execute successful payment confirmation
        PaymentService.process_payment_success(
            db=self.db,
            payment_id=payment.id,
            provider_payment_id="ch_stripe_mock_123",
        )

        # 4. Verify email was dispatched to assigned doctor
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args
        to_email = call_args[0][0]
        subject = call_args[0][1]
        text_body = call_args[0][2]
        html_body = call_args[0][3]

        self.assertEqual(to_email, "dr.specialist@example.com")
        self.assertIn("New Patient Review Assigned", subject)
        self.assertIn("Jane Patient", text_body)
        self.assertIn(req.id[:8], text_body)

        # Privacy check: Verify no radiograph findings or image path leaked
        self.assertNotIn("Effusion", text_body)
        self.assertNotIn("0.82", text_body)
        self.assertNotIn("/outputs/xray.jpg", text_body)

    @patch.object(EmailService, "send_email", return_value=True)
    def test_unassigned_pool_request_does_not_email_doctor(self, mock_send_email):
        # 1. Create open pool request (no doctor specified)
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-em-001",
            patient_message="Open pool consultation",
        )
        self.assertIsNone(req.professional_id)

        # 2. Create Payment record
        payment = Payment(
            id="pay-pool-001",
            user_id=self.patient.id,
            review_request_id=req.id,
            service_id="XRAY_PROFESSIONAL_REVIEW",
            amount_minor=49900,
            currency="INR",
            status=PaymentStatus.CHECKOUT_CREATED,
        )
        self.db.add(payment)
        self.db.commit()

        # 3. Process payment
        PaymentService.process_payment_success(
            db=self.db,
            payment_id=payment.id,
        )

        # 4. Confirm NO assignment email was sent (pool case)
        mock_send_email.assert_not_called()

        # Request moved to MATCHING status
        self.db.refresh(req)
        self.assertEqual(req.status, ReviewStatus.MATCHING)
        self.assertEqual(req.payment_status, "PAID")

    @patch.object(EmailService, "send_email", return_value=True)
    def test_repeated_payment_confirmation_does_not_send_duplicate_emails(self, mock_send_email):
        # Create request and payment
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-em-001",
            preferred_professional_id=self.doctor.id,
        )
        payment = Payment(
            id="pay-idem-001",
            user_id=self.patient.id,
            review_request_id=req.id,
            service_id="XRAY_PROFESSIONAL_REVIEW",
            amount_minor=49900,
            currency="INR",
            status=PaymentStatus.CHECKOUT_CREATED,
        )
        self.db.add(payment)
        self.db.commit()

        # First payment success confirmation
        PaymentService.process_payment_success(db=self.db, payment_id=payment.id)
        self.assertEqual(mock_send_email.call_count, 1)

        # Second duplicate payment webhook / confirmation call
        PaymentService.process_payment_success(db=self.db, payment_id=payment.id)
        # Count MUST remain 1
        self.assertEqual(mock_send_email.call_count, 1)

    @patch.object(EmailService, "send_email", return_value=True)
    def test_in_app_notifications_still_created(self, mock_send_email):
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-em-001",
            preferred_professional_id=self.doctor.id,
        )
        payment = Payment(
            id="pay-notif-001",
            user_id=self.patient.id,
            review_request_id=req.id,
            service_id="XRAY_PROFESSIONAL_REVIEW",
            amount_minor=49900,
            currency="INR",
            status=PaymentStatus.CHECKOUT_CREATED,
        )
        self.db.add(payment)
        self.db.commit()

        PaymentService.process_payment_success(db=self.db, payment_id=payment.id)

        # Check in-app notifications created in database
        doctor_notifications = self.db.query(Notification).filter(Notification.user_id == self.doctor.id).all()
        self.assertGreaterEqual(len(doctor_notifications), 1)

        patient_notifications = self.db.query(Notification).filter(Notification.user_id == self.patient.id).all()
        self.assertGreaterEqual(len(patient_notifications), 1)

    @patch.object(EmailService, "send_email", side_effect=Exception("SMTP Connection Timeout"))
    def test_email_delivery_failure_does_not_break_payment_confirmation(self, mock_send_email):
        # Even if SMTP raises a network error, payment and case assignment must succeed
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-em-001",
            preferred_professional_id=self.doctor.id,
        )
        payment = Payment(
            id="pay-fail-resilience-001",
            user_id=self.patient.id,
            review_request_id=req.id,
            service_id="XRAY_PROFESSIONAL_REVIEW",
            amount_minor=49900,
            currency="INR",
            status=PaymentStatus.CHECKOUT_CREATED,
        )
        self.db.add(payment)
        self.db.commit()

        # Should NOT raise an exception
        confirmed_payment = PaymentService.process_payment_success(db=self.db, payment_id=payment.id)
        
        self.assertEqual(confirmed_payment.status, PaymentStatus.PAID)
        self.db.refresh(req)
        self.assertEqual(req.status, ReviewStatus.ASSIGNED)
        self.assertEqual(req.payment_status, "PAID")


if __name__ == "__main__":
    unittest.main()
