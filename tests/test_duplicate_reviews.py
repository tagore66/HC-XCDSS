"""
Unit and regression tests for idempotent review request creation and patient review list filtering.
"""

import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models.user import User, UserRole
from src.db.models.analysis import Analysis
from src.db.models.review_request import ReviewRequest, ReviewStatus
from src.db.models.professional_profile import ProfessionalProfile, ProfessionalVerificationStatus
from src.reviews.service import ReviewService


class TestDuplicateReviewsAndFiltering(unittest.TestCase):
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
            id="test-patient-001",
            email="patient@test.com",
            role=UserRole.PATIENT,
            is_active=True,
            full_name="Test Patient",
        )
        self.db.add(self.patient)

        # Seed test verified professional 1
        self.doctor1 = User(
            id="test-doctor-001",
            email="doctor1@test.com",
            role=UserRole.PROFESSIONAL,
            is_active=True,
            full_name="Dr. Specialist One",
        )
        self.db.add(self.doctor1)

        doctor_profile1 = ProfessionalProfile(
            user_id=self.doctor1.id,
            verification_status=ProfessionalVerificationStatus.VERIFIED,
            license_number="MED-12345",
            specialty="Radiology",
        )
        self.db.add(doctor_profile1)

        # Seed test verified professional 2
        self.doctor2 = User(
            id="test-doctor-002",
            email="doctor2@test.com",
            role=UserRole.PROFESSIONAL,
            is_active=True,
            full_name="Dr. Specialist Two",
        )
        self.db.add(self.doctor2)

        doctor_profile2 = ProfessionalProfile(
            user_id=self.doctor2.id,
            verification_status=ProfessionalVerificationStatus.VERIFIED,
            license_number="MED-67890",
            specialty="Pulmonology",
        )
        self.db.add(doctor_profile2)

        # Seed test analyses for patient
        self.analysis1 = Analysis(
            id="analysis-001",
            user_id=self.patient.id,
            image_path="chest_xray_1.jpg",
            view="Frontal",
            findings_raw={"Cardiomegaly": 0.85},
            detected_findings=["Cardiomegaly"],
            heatmaps={},
            patient_explanations=[],
        )
        self.db.add(self.analysis1)

        self.analysis2 = Analysis(
            id="analysis-002",
            user_id=self.patient.id,
            image_path="chest_xray_2.jpg",
            view="Frontal",
            findings_raw={"Effusion": 0.72},
            detected_findings=["Effusion"],
            heatmaps={},
            patient_explanations=[],
        )
        self.db.add(self.analysis2)

        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_first_request_creates_one_record(self):
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-001",
            patient_message="First review request",
        )

        self.assertIsNotNone(req)
        self.assertEqual(req.analysis_id, "analysis-001")
        self.assertEqual(req.patient_id, self.patient.id)
        self.assertEqual(req.payment_status, "UNPAID")
        self.assertEqual(req.status, ReviewStatus.REQUESTED)
        self.assertEqual(req.patient_message, "First review request")

        all_records = self.db.query(ReviewRequest).filter(ReviewRequest.analysis_id == "analysis-001").all()
        self.assertEqual(len(all_records), 1)

    def test_repeated_request_reuses_unpaid_record(self):
        # 1. First request creation
        req1 = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-001",
            patient_message="Initial note",
        )
        first_id = req1.id

        # 2. Second request for same patient + analysis while UNPAID, with updated note & selected doctor 1
        req2 = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-001",
            patient_message="Updated note with doctor selected",
            preferred_professional_id=self.doctor1.id,
        )

        # Must reuse the exact same record ID
        self.assertEqual(req2.id, first_id)
        self.assertEqual(req2.patient_message, "Updated note with doctor selected")
        self.assertEqual(req2.professional_id, self.doctor1.id)
        self.assertEqual(req2.status, ReviewStatus.ASSIGNED)
        self.assertEqual(req2.payment_status, "UNPAID")

        # 3. Third request changing doctor from doctor 1 to doctor 2 while still UNPAID
        req3 = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-001",
            patient_message="Switched to doctor 2",
            preferred_professional_id=self.doctor2.id,
        )
        self.assertEqual(req3.id, first_id)
        self.assertEqual(req3.patient_message, "Switched to doctor 2")
        self.assertEqual(req3.professional_id, self.doctor2.id)
        self.assertEqual(req3.status, ReviewStatus.ASSIGNED)
        self.assertEqual(req3.payment_status, "UNPAID")

        # Verify database still only contains 1 review request record
        all_records = self.db.query(ReviewRequest).filter(ReviewRequest.analysis_id == "analysis-001").all()
        self.assertEqual(len(all_records), 1)

    def test_paid_request_cannot_create_another_active_request(self):
        # Create request and mark it PAID
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-001",
        )
        req.payment_status = "PAID"
        req.status = ReviewStatus.ASSIGNED
        self.db.commit()

        # Attempt to create another request for the same analysis must raise ValueError
        with self.assertRaises(ValueError) as ctx:
            ReviewService.create_review_request(
                db=self.db,
                patient=self.patient,
                analysis_id="analysis-001",
            )

        self.assertIn("An active review request already exists", str(ctx.exception))

        # Confirm still only 1 record exists in database
        all_records = self.db.query(ReviewRequest).filter(ReviewRequest.analysis_id == "analysis-001").all()
        self.assertEqual(len(all_records), 1)

    def test_cancelled_and_unpaid_requests_excluded_from_patient_list(self):
        # 1. Unpaid request -> should NOT be visible in normal list
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-001",
        )
        
        patient_list = ReviewService.get_patient_review_requests(db=self.db, patient=self.patient)
        self.assertEqual(len(patient_list), 0)

        # 2. Mark PAID -> should BE visible in normal patient list
        req.payment_status = "PAID"
        req.status = ReviewStatus.ASSIGNED
        self.db.commit()

        patient_list = ReviewService.get_patient_review_requests(db=self.db, patient=self.patient)
        self.assertEqual(len(patient_list), 1)
        self.assertEqual(patient_list[0].id, req.id)

        # 3. Mark CANCELLED -> should NOT be visible in normal patient list
        req.status = ReviewStatus.CANCELLED
        self.db.commit()

        patient_list = ReviewService.get_patient_review_requests(db=self.db, patient=self.patient)
        self.assertEqual(len(patient_list), 0)

    def test_multi_analysis_isolation_and_statuses(self):
        # Patient creates request for analysis 1 and pays for it
        req1 = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-001",
        )
        req1.payment_status = "PAID"
        req1.status = ReviewStatus.IN_REVIEW
        self.db.commit()

        # Patient creates request for analysis 2 but abandons checkout (UNPAID)
        req2 = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-002",
        )

        # Patient list must contain ONLY analysis 1
        patient_list = ReviewService.get_patient_review_requests(db=self.db, patient=self.patient)
        self.assertEqual(len(patient_list), 1)
        self.assertEqual(patient_list[0].analysis_id, "analysis-001")

        # Now when req1 completes, it still shows in patient list
        req1.status = ReviewStatus.COMPLETED
        self.db.commit()

        patient_list_after_completion = ReviewService.get_patient_review_requests(db=self.db, patient=self.patient)
        self.assertEqual(len(patient_list_after_completion), 1)
        self.assertEqual(patient_list_after_completion[0].status, ReviewStatus.COMPLETED)

    def test_cancel_review_request_integration(self):
        # Create request and mark PAID
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-001",
            preferred_professional_id=self.doctor1.id,
        )
        req.payment_status = "PAID"
        self.db.commit()

        # Cancel via ReviewService
        cancelled_req = ReviewService.cancel_review_request(
            db=self.db,
            review_id=req.id,
            patient=self.patient,
        )
        self.assertEqual(cancelled_req.status, ReviewStatus.CANCELLED)

        # Confirm not present in patient list
        patient_list = ReviewService.get_patient_review_requests(db=self.db, patient=self.patient)
        self.assertEqual(len(patient_list), 0)


if __name__ == "__main__":
    unittest.main()
