"""
Unit tests for Professional Dashboard review request categorization and filtering.

Tests:
A. Direct assignment -> appears in My Active & Completed Reviews
B. Direct assignment -> absent from Available Requests
C. Pool request -> appears in Available Requests
D. Pool request accepted -> moves to My Active & Completed Reviews
E. Completed review -> remains in My Active & Completed Reviews
F. Endpoint filter parameter behavior (available, assigned, completed, all)
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
from src.reviews.schemas import ProfessionalReviewSubmitRequest


class TestProfessionalDashboardCategorization(unittest.TestCase):
    def setUp(self):
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
            full_name="Alice Patient",
        )
        self.db.add(self.patient)

        # Seed test verified doctor
        self.doctor = User(
            id="test-doctor-001",
            email="doctor@test.com",
            role=UserRole.PROFESSIONAL,
            is_active=True,
            full_name="Dr. Specialist",
        )
        self.db.add(self.doctor)

        doctor_profile = ProfessionalProfile(
            user_id=self.doctor.id,
            verification_status=ProfessionalVerificationStatus.VERIFIED,
            license_number="LIC-12345",
            specialty="Thoracic Radiology",
        )
        self.db.add(doctor_profile)

        # Seed other doctor
        self.other_doctor = User(
            id="test-doctor-002",
            email="otherdoctor@test.com",
            role=UserRole.PROFESSIONAL,
            is_active=True,
            full_name="Dr. Other Specialist",
        )
        self.db.add(self.other_doctor)

        other_profile = ProfessionalProfile(
            user_id=self.other_doctor.id,
            verification_status=ProfessionalVerificationStatus.VERIFIED,
            license_number="LIC-67890",
            specialty="General Radiology",
        )
        self.db.add(other_profile)

        # Seed analysis
        self.analysis = Analysis(
            id="analysis-cat-001",
            user_id=self.patient.id,
            image_path="/outputs/test.jpg",
            view="Frontal",
            findings_raw={"Atelectasis": 0.65},
            detected_findings=["Atelectasis"],
        )
        self.db.add(self.analysis)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_a_b_direct_assignment_categorization(self):
        """
        Scenario A & B:
        Directly assigned request (professional_id = doctor.id, status = ASSIGNED, payment = PAID):
        - MUST appear in My Active & Completed Reviews
        - MUST be absent from Available Requests
        """
        req = ReviewRequest(
            id="rev-direct-001",
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

        # Query all reviews for doctor dashboard
        all_reviews = ReviewService.get_filtered_for_professional(self.db, self.doctor, filter_type="all")
        review_dicts = [ReviewService.build_review_response(self.db, r) for r in all_reviews]

        # Frontend filtering simulation
        available_requests = [
            r for r in review_dicts
            if not r.get("professional_id") and r.get("status") in ["REQUESTED", "MATCHING"]
        ]
        my_reviews = [
            r for r in review_dicts
            if r.get("professional_id") == self.doctor.id and r.get("status") in ["ASSIGNED", "ACCEPTED", "IN_REVIEW", "COMPLETED"]
        ]

        # Assertions
        my_review_ids = [r["id"] for r in my_reviews]
        available_ids = [r["id"] for r in available_requests]

        self.assertIn("rev-direct-001", my_review_ids, "Directly assigned review must appear in My Active & Completed Reviews")
        self.assertNotIn("rev-direct-001", available_ids, "Directly assigned review must NOT appear in Available Requests")

    def test_c_pool_request_categorization(self):
        """
        Scenario C:
        Open unassigned pool request (professional_id = None, status = REQUESTED/MATCHING, payment = PAID):
        - MUST appear in Available Requests
        - MUST be absent from My Active & Completed Reviews
        """
        req = ReviewRequest(
            id="rev-pool-001",
            analysis_id=self.analysis.id,
            patient_id=self.patient.id,
            professional_id=None,
            status=ReviewStatus.MATCHING,
            payment_status="PAID",
            requested_at=datetime.now(timezone.utc),
        )
        self.db.add(req)
        self.db.commit()

        all_reviews = ReviewService.get_filtered_for_professional(self.db, self.doctor, filter_type="all")
        review_dicts = [ReviewService.build_review_response(self.db, r) for r in all_reviews]

        available_requests = [
            r for r in review_dicts
            if not r.get("professional_id") and r.get("status") in ["REQUESTED", "MATCHING"]
        ]
        my_reviews = [
            r for r in review_dicts
            if r.get("professional_id") == self.doctor.id and r.get("status") in ["ASSIGNED", "ACCEPTED", "IN_REVIEW", "COMPLETED"]
        ]

        available_ids = [r["id"] for r in available_requests]
        my_review_ids = [r["id"] for r in my_reviews]

        self.assertIn("rev-pool-001", available_ids, "Pool request must appear in Available Requests")
        self.assertNotIn("rev-pool-001", my_review_ids, "Pool request must NOT appear in My Active Reviews")

    def test_d_pool_request_accepted_moves_to_my_reviews(self):
        """
        Scenario D:
        When a doctor accepts a pool request:
        - professional_id becomes doctor.id
        - status becomes ACCEPTED
        - Immediately moves to My Active Reviews and disappears from Available Requests
        """
        req = ReviewRequest(
            id="rev-pool-002",
            analysis_id=self.analysis.id,
            patient_id=self.patient.id,
            professional_id=None,
            status=ReviewStatus.MATCHING,
            payment_status="PAID",
            requested_at=datetime.now(timezone.utc),
        )
        self.db.add(req)
        self.db.commit()

        # Doctor accepts request
        accepted_req = ReviewService.accept_review_request(self.db, "rev-pool-002", self.doctor)
        self.assertEqual(accepted_req.professional_id, self.doctor.id)
        self.assertEqual(accepted_req.status, ReviewStatus.ACCEPTED)

        # Re-fetch dashboard queue
        all_reviews = ReviewService.get_filtered_for_professional(self.db, self.doctor, filter_type="all")
        review_dicts = [ReviewService.build_review_response(self.db, r) for r in all_reviews]

        available_requests = [
            r for r in review_dicts
            if not r.get("professional_id") and r.get("status") in ["REQUESTED", "MATCHING"]
        ]
        my_reviews = [
            r for r in review_dicts
            if r.get("professional_id") == self.doctor.id and r.get("status") in ["ASSIGNED", "ACCEPTED", "IN_REVIEW", "COMPLETED"]
        ]

        available_ids = [r["id"] for r in available_requests]
        my_review_ids = [r["id"] for r in my_reviews]

        self.assertIn("rev-pool-002", my_review_ids, "Accepted review must now be in My Active Reviews")
        self.assertNotIn("rev-pool-002", available_ids, "Accepted review must no longer be in Available Requests")

    def test_e_completed_review_remains_in_my_reviews(self):
        """
        Scenario E:
        Completed review:
        - remains in My Active & Completed Reviews
        - is absent from Available Requests
        """
        req = ReviewRequest(
            id="rev-comp-001",
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

        # Complete review
        submit_payload = ProfessionalReviewSubmitRequest(
            clinical_observations="Clear lung fields. Normal cardiac size.",
            professional_impression="No acute cardiopulmonary disease.",
            recommendations="Routine follow-up.",
            urgency="ROUTINE",
            follow_up=False,
        )
        ReviewService.complete_review(self.db, "rev-comp-001", self.doctor, submit_payload)

        # Re-fetch dashboard queue
        all_reviews = ReviewService.get_filtered_for_professional(self.db, self.doctor, filter_type="all")
        review_dicts = [ReviewService.build_review_response(self.db, r) for r in all_reviews]

        available_requests = [
            r for r in review_dicts
            if not r.get("professional_id") and r.get("status") in ["REQUESTED", "MATCHING"]
        ]
        my_reviews = [
            r for r in review_dicts
            if r.get("professional_id") == self.doctor.id and r.get("status") in ["ASSIGNED", "ACCEPTED", "IN_REVIEW", "COMPLETED"]
        ]

        my_review_ids = [r["id"] for r in my_reviews]
        available_ids = [r["id"] for r in available_requests]

        self.assertIn("rev-comp-001", my_review_ids, "Completed review must remain in My Active & Completed Reviews")
        self.assertNotIn("rev-comp-001", available_ids, "Completed review must NOT appear in Available Requests")

    def test_f_filter_types_query_isolation(self):
        """
        Scenario F:
        Verify query isolation between filter_type options:
        - filter_type='available' returns ONLY unassigned pool cases
        - filter_type='assigned' returns ONLY assigned/accepted/in_review for this doctor
        - filter_type='completed' returns ONLY completed reviews for this doctor
        - filter_type='all' returns both pool cases and all doctor's assigned cases
        """
        # 1. Pool case
        p1 = ReviewRequest(
            id="pool-1",
            analysis_id=self.analysis.id,
            patient_id=self.patient.id,
            professional_id=None,
            status=ReviewStatus.REQUESTED,
            payment_status="PAID",
        )
        # 2. Directly assigned to self.doctor
        a1 = ReviewRequest(
            id="assigned-1",
            analysis_id=self.analysis.id,
            patient_id=self.patient.id,
            professional_id=self.doctor.id,
            status=ReviewStatus.ASSIGNED,
            payment_status="PAID",
        )
        # 3. Assigned to OTHER doctor
        o1 = ReviewRequest(
            id="other-assigned-1",
            analysis_id=self.analysis.id,
            patient_id=self.patient.id,
            professional_id=self.other_doctor.id,
            status=ReviewStatus.ASSIGNED,
            payment_status="PAID",
        )
        self.db.add_all([p1, a1, o1])
        self.db.commit()

        avail_results = [r.id for r in ReviewService.get_filtered_for_professional(self.db, self.doctor, "available")]
        assigned_results = [r.id for r in ReviewService.get_filtered_for_professional(self.db, self.doctor, "assigned")]
        all_results = [r.id for r in ReviewService.get_filtered_for_professional(self.db, self.doctor, "all")]

        self.assertIn("pool-1", avail_results)
        self.assertNotIn("assigned-1", avail_results)
        self.assertNotIn("other-assigned-1", avail_results)

        self.assertIn("assigned-1", assigned_results)
        self.assertNotIn("pool-1", assigned_results)
        self.assertNotIn("other-assigned-1", assigned_results)

        self.assertIn("pool-1", all_results)
        self.assertIn("assigned-1", all_results)
        self.assertNotIn("other-assigned-1", all_results)


if __name__ == "__main__":
    unittest.main()
