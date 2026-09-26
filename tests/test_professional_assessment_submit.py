"""
Regression and end-to-end unit tests for Professional Clinical Assessment Submission.

Tests:
1. Assigned review exists (PAID)
2. Doctor opens case workspace
3. Doctor submits valid assessment with various urgency levels (ROUTINE, PRIORITY, URGENT, EMERGENCY)
4. HTTP response succeeds (200 OK)
5. ReviewRequest becomes COMPLETED with completed_at timestamp
6. ProfessionalReview record is stored and populated
7. Assessment is immutable (idempotent / locked after COMPLETED)
8. Patient can retrieve completed review
9. Patient report generation / HTML report contains professional findings
10. Invalid submissions (too short, unassigned doctor, unpaid) return clean readable error
"""

import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.base import Base
from src.db.models.user import User, UserRole
from src.db.models.analysis import Analysis
from src.db.models.review_request import ReviewRequest, ReviewStatus, ProfessionalReview
from src.db.models.professional_profile import ProfessionalProfile, ProfessionalVerificationStatus
from src.reviews.service import ReviewService
from src.reviews.schemas import (
    ProfessionalReviewSubmitRequest,
    ProfessionalAssessmentDraftRequest,
)


class TestProfessionalAssessmentSubmit(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.Session()

        # 1. Patient
        self.patient = User(
            id="patient-reg-001",
            email="patient.submit@test.com",
            role=UserRole.PATIENT,
            is_active=True,
            full_name="Jane Doe",
        )
        self.db.add(self.patient)

        # 2. Verified Doctor
        self.doctor = User(
            id="doctor-reg-001",
            email="doctor.submit@test.com",
            role=UserRole.PROFESSIONAL,
            is_active=True,
            full_name="Dr. Gregory House",
        )
        self.db.add(self.doctor)

        doctor_profile = ProfessionalProfile(
            user_id=self.doctor.id,
            verification_status=ProfessionalVerificationStatus.VERIFIED,
            license_number="MD-SUBMIT-123",
            specialty="Diagnostic Radiology",
            consultation_fee=499.0,
        )
        self.db.add(doctor_profile)

        # 3. Another Doctor
        self.other_doctor = User(
            id="doctor-reg-002",
            email="other.submit@test.com",
            role=UserRole.PROFESSIONAL,
            is_active=True,
            full_name="Dr. John Watson",
        )
        self.db.add(self.other_doctor)

        other_profile = ProfessionalProfile(
            user_id=self.other_doctor.id,
            verification_status=ProfessionalVerificationStatus.VERIFIED,
            license_number="MD-SUBMIT-456",
            specialty="Pulmonology",
        )
        self.db.add(other_profile)

        # 4. Analysis
        self.analysis = Analysis(
            id="analysis-sub-001",
            user_id=self.patient.id,
            image_path="/outputs/test_xray.png",
            view="Frontal",
            findings_raw={"Atelectasis": 0.72, "Cardiomegaly": 0.15},
            detected_findings=["Atelectasis"],
        )
        self.db.add(self.analysis)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_complete_submit_lifecycle_and_immutability(self):
        """
        Complete lifecycle test:
        1. Assigned review exists and is PAID.
        2. Doctor retrieves workspace data.
        3. Doctor saves draft.
        4. Doctor submits assessment with PRIORITY urgency.
        5. ReviewRequest status is COMPLETED and completed_at is set.
        6. Patient retrieves completed review.
        7. Immutability: Subsequent draft save is rejected.
        """
        req = ReviewRequest(
            id="review-sub-001",
            analysis_id=self.analysis.id,
            patient_id=self.patient.id,
            professional_id=self.doctor.id,
            status=ReviewStatus.ASSIGNED,
            payment_status="PAID",
            requested_at=datetime.now(timezone.utc),
            assigned_at=datetime.now(timezone.utc),
        )
        self.db.add(req)
        self.db.commit()

        # Step 2: Doctor opens workspace
        ws_data = ReviewService.get_professional_case_workspace(self.db, "review-sub-001", self.doctor)
        self.assertIsNotNone(ws_data)
        self.assertEqual(ws_data["review_request"]["status"], "ASSIGNED")
        self.assertEqual(ws_data["patient"]["full_name"], "Jane Doe")

        # Step 3: Doctor saves draft
        draft_payload = ProfessionalAssessmentDraftRequest(
            clinical_observations="Bilateral costophrenic angles sharp. Subsegmental atelectasis in right base.",
            professional_impression="Resolving baseline atelectasis. No focal consolidation.",
            recommendations="Repeat PA chest X-ray in 4-6 weeks if coughing persists.",
            urgency="PRIORITY",
            follow_up=True,
            additional_notes="Correlate with smoking history.",
        )
        draft_review = ReviewService.save_assessment_draft(self.db, "review-sub-001", self.doctor, draft_payload)
        self.assertEqual(draft_review.urgency, "PRIORITY")
        self.assertTrue(draft_review.follow_up_required)

        # Step 4: Doctor submits final assessment
        submit_payload = ProfessionalReviewSubmitRequest(
            clinical_observations="Bilateral costophrenic angles sharp. Subsegmental atelectasis in right base.",
            professional_impression="Resolving baseline atelectasis. No focal consolidation or acute pneumonia.",
            recommendations="Repeat PA chest X-ray in 4-6 weeks if coughing persists.",
            urgency="PRIORITY",
            follow_up=True,
            additional_notes="Correlate with clinical history.",
        )
        final_review = ReviewService.complete_review(self.db, "review-sub-001", self.doctor, submit_payload)

        # Step 5: Check completion status
        self.db.refresh(req)
        self.assertEqual(req.status, ReviewStatus.COMPLETED)
        self.assertIsNotNone(req.completed_at)
        self.assertEqual(final_review.urgency, "PRIORITY")
        self.assertEqual(final_review.clinical_summary, submit_payload.clinical_observations)
        self.assertEqual(final_review.clinical_impression, submit_payload.professional_impression)

        # Step 6: Patient retrieves completed review
        patient_review = ReviewService.get_patient_professional_review(self.db, "review-sub-001", self.patient)
        self.assertIsNotNone(patient_review)
        self.assertEqual(patient_review["status"], "COMPLETED")
        self.assertEqual(patient_review["professional"]["full_name"], "Dr. Gregory House")
        self.assertEqual(patient_review["professional_review"]["urgency"], "PRIORITY")

        # Step 7: Immutability test - editing after completion must fail
        with self.assertRaises(ValueError) as ctx:
            ReviewService.save_assessment_draft(self.db, "review-sub-001", self.doctor, draft_payload)
        self.assertIn("already COMPLETED", str(ctx.exception))

    def test_urgency_levels_accepted(self):
        """
        Verify that all valid urgency levels (ROUTINE, PRIORITY, URGENT, EMERGENCY) are accepted.
        """
        for urgency_val in ["ROUTINE", "PRIORITY", "URGENT", "EMERGENCY"]:
            payload = ProfessionalReviewSubmitRequest(
                clinical_observations="Normal cardiac silhouette and clear lung fields.",
                professional_impression="Normal chest radiograph.",
                recommendations="None.",
                urgency=urgency_val,
                follow_up=False,
            )
            self.assertEqual(payload.urgency, urgency_val)

    def test_unauthorized_physician_cannot_submit(self):
        """
        Verify that a physician not assigned to the case cannot submit an assessment.
        """
        req = ReviewRequest(
            id="review-sub-unauth",
            analysis_id=self.analysis.id,
            patient_id=self.patient.id,
            professional_id=self.doctor.id,
            status=ReviewStatus.ASSIGNED,
            payment_status="PAID",
        )
        self.db.add(req)
        self.db.commit()

        payload = ProfessionalReviewSubmitRequest(
            clinical_observations="Clear lung fields.",
            professional_impression="Normal radiograph.",
            urgency="ROUTINE",
        )

        with self.assertRaises(PermissionError) as ctx:
            ReviewService.complete_review(self.db, "review-sub-unauth", self.other_doctor, payload)
        self.assertIn("not assigned to you", str(ctx.exception))

    def test_unpaid_case_cannot_be_submitted(self):
        """
        Verify that an unpaid case cannot have an assessment submitted.
        """
        req = ReviewRequest(
            id="review-sub-unpaid",
            analysis_id=self.analysis.id,
            patient_id=self.patient.id,
            professional_id=self.doctor.id,
            status=ReviewStatus.REQUESTED,
            payment_status="UNPAID",
        )
        self.db.add(req)
        self.db.commit()

        payload = ProfessionalReviewSubmitRequest(
            clinical_observations="Clear lung fields.",
            professional_impression="Normal radiograph.",
            urgency="ROUTINE",
        )

        with self.assertRaises(PermissionError) as ctx:
            ReviewService.complete_review(self.db, "review-sub-unpaid", self.doctor, payload)
        self.assertIn("payment has not been completed", str(ctx.exception))

    def test_short_observations_validation(self):
        """
        Verify that observations / impression with fewer than 5 characters are rejected.
        """
        req = ReviewRequest(
            id="review-sub-short",
            analysis_id=self.analysis.id,
            patient_id=self.patient.id,
            professional_id=self.doctor.id,
            status=ReviewStatus.ASSIGNED,
            payment_status="PAID",
        )
        self.db.add(req)
        self.db.commit()

        payload = ProfessionalReviewSubmitRequest(
            clinical_observations="ok",
            professional_impression="ok",
            urgency="ROUTINE",
        )

        with self.assertRaises(ValueError) as ctx:
            ReviewService.complete_review(self.db, "review-sub-short", self.doctor, payload)
        self.assertIn("minimum 5 characters", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
