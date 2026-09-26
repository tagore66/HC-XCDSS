"""
Unit and regression tests for professional case workspace access and claim/accept workflow.
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


class TestProfessionalWorkspaceAccess(unittest.TestCase):
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
            full_name="Alice Patient",
        )
        self.db.add(self.patient)

        # Seed test verified doctor 1
        self.doctor1 = User(
            id="test-doctor-001",
            email="doctor1@test.com",
            role=UserRole.PROFESSIONAL,
            is_active=True,
            full_name="Dr. Specialist One",
        )
        self.db.add(self.doctor1)

        doctor1_profile = ProfessionalProfile(
            user_id=self.doctor1.id,
            verification_status=ProfessionalVerificationStatus.VERIFIED,
            license_number="LIC-001",
            specialty="Radiology",
        )
        self.db.add(doctor1_profile)

        # Seed test verified doctor 2
        self.doctor2 = User(
            id="test-doctor-002",
            email="doctor2@test.com",
            role=UserRole.PROFESSIONAL,
            is_active=True,
            full_name="Dr. Specialist Two",
        )
        self.db.add(self.doctor2)

        doctor2_profile = ProfessionalProfile(
            user_id=self.doctor2.id,
            verification_status=ProfessionalVerificationStatus.VERIFIED,
            license_number="LIC-002",
            specialty="Pulmonology",
        )
        self.db.add(doctor2_profile)

        # Seed test unverified / pending doctor
        self.pending_doctor = User(
            id="test-pending-doctor",
            email="pending@test.com",
            role=UserRole.PROFESSIONAL,
            is_active=True,
            full_name="Dr. Pending",
        )
        self.db.add(self.pending_doctor)

        pending_profile = ProfessionalProfile(
            user_id=self.pending_doctor.id,
            verification_status=ProfessionalVerificationStatus.PENDING,
            license_number="LIC-PENDING",
            specialty="General",
        )
        self.db.add(pending_profile)

        # Seed test analysis for patient
        self.analysis = Analysis(
            id="analysis-ws-001",
            user_id=self.patient.id,
            image_path="/outputs/test_xray.jpg",
            view="Frontal",
            findings_raw={"Pneumonia": 0.78, "Infiltration": 0.45},
            detected_findings=["Pneumonia"],
            heatmaps={"Pneumonia": "/outputs/heatmap_pneu.jpg"},
            patient_explanations=[],
        )
        self.db.add(self.analysis)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_verified_doctor_can_accept_unassigned_request(self):
        # 1. Create open pool request (no doctor selected) and mark PAID
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-ws-001",
            patient_message="Open pool review request",
        )
        req.payment_status = "PAID"
        req.status = ReviewStatus.REQUESTED
        self.db.commit()

        # Prior to accepting: req.professional_id is None
        self.assertIsNone(req.professional_id)

        # 2. Before accepting, doctor cannot open workspace
        with self.assertRaises(PermissionError) as ctx:
            ReviewService.get_professional_case_workspace(
                db=self.db,
                review_id=req.id,
                professional=self.doctor1,
            )
        self.assertIn("Access denied", str(ctx.exception))

        # 3. Doctor 1 accepts the request
        accepted_req = ReviewService.accept_review_request(
            db=self.db,
            review_id=req.id,
            professional=self.doctor1,
        )

        self.assertEqual(accepted_req.professional_id, self.doctor1.id)
        self.assertEqual(accepted_req.status, ReviewStatus.ACCEPTED)
        self.assertIsNotNone(accepted_req.accepted_at)

    def test_assigned_doctor_can_open_workspace(self):
        # Create, pay, and accept request with Doctor 1
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-ws-001",
            patient_message="Please review pneumonia signs",
        )
        req.payment_status = "PAID"
        self.db.commit()

        ReviewService.accept_review_request(
            db=self.db,
            review_id=req.id,
            professional=self.doctor1,
        )

        # Doctor 1 can open workspace
        workspace_data = ReviewService.get_professional_case_workspace(
            db=self.db,
            review_id=req.id,
            professional=self.doctor1,
        )

        self.assertIsNotNone(workspace_data)
        self.assertIn("patient", workspace_data)
        self.assertEqual(workspace_data["patient"]["full_name"], "Alice Patient")
        self.assertIn("analysis", workspace_data)
        self.assertEqual(workspace_data["analysis"]["analysis_id"], "analysis-ws-001")
        self.assertIn("Pneumonia", workspace_data["analysis"]["findings"])

    def test_another_doctor_gets_permission_error(self):
        # Create, pay, and assign/accept with Doctor 1
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-ws-001",
        )
        req.payment_status = "PAID"
        self.db.commit()

        ReviewService.accept_review_request(
            db=self.db,
            review_id=req.id,
            professional=self.doctor1,
        )

        # Doctor 2 attempts to accept the already assigned case -> raises PermissionError
        with self.assertRaises(PermissionError) as ctx_accept:
            ReviewService.accept_review_request(
                db=self.db,
                review_id=req.id,
                professional=self.doctor2,
            )
        self.assertIn("assigned to another professional", str(ctx_accept.exception))

        # Doctor 2 attempts to open workspace -> raises PermissionError
        with self.assertRaises(PermissionError) as ctx_workspace:
            ReviewService.get_professional_case_workspace(
                db=self.db,
                review_id=req.id,
                professional=self.doctor2,
            )
        self.assertIn("Access denied", str(ctx_workspace.exception))

    def test_direct_doctor_assignment_workflow(self):
        # Patient explicitly selects Doctor 1 at creation
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-ws-001",
            preferred_professional_id=self.doctor1.id,
            patient_message="Direct assignment to Dr. One",
        )
        req.payment_status = "PAID"
        req.status = ReviewStatus.ASSIGNED
        self.db.commit()

        # Doctor 1 is already assigned
        self.assertEqual(req.professional_id, self.doctor1.id)

        # Doctor 1 can immediately open the workspace or accept it
        workspace_data = ReviewService.get_professional_case_workspace(
            db=self.db,
            review_id=req.id,
            professional=self.doctor1,
        )
        self.assertIsNotNone(workspace_data)
        self.assertEqual(workspace_data["patient"]["id"], self.patient.id)

        # Doctor 2 cannot open Doctor 1's directly assigned case
        with self.assertRaises(PermissionError):
            ReviewService.get_professional_case_workspace(
                db=self.db,
                review_id=req.id,
                professional=self.doctor2,
            )

    def test_unpaid_case_cannot_be_opened_or_accepted(self):
        # Create UNPAID request
        req = ReviewService.create_review_request(
            db=self.db,
            patient=self.patient,
            analysis_id="analysis-ws-001",
            preferred_professional_id=self.doctor1.id,
        )
        self.assertEqual(req.payment_status, "UNPAID")

        # Accept attempt fails
        with self.assertRaises(PermissionError) as ctx_acc:
            ReviewService.accept_review_request(
                db=self.db,
                review_id=req.id,
                professional=self.doctor1,
            )
        self.assertIn("payment has been completed", str(ctx_acc.exception))

        # Workspace attempt fails
        with self.assertRaises(PermissionError) as ctx_ws:
            ReviewService.get_professional_case_workspace(
                db=self.db,
                review_id=req.id,
                professional=self.doctor1,
            )
    def test_unverified_pending_doctor_cannot_access_workspace(self):
        from fastapi import HTTPException
        from src.auth.dependencies import get_current_verified_professional

        # 1. Unverified doctor profile check raises HTTPException 403
        with self.assertRaises(HTTPException) as ctx:
            get_current_verified_professional(
                current_user=self.pending_doctor,
                db=self.db,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("not verified", ctx.exception.detail)

        # 2. Patient user check raises HTTPException 403
        with self.assertRaises(HTTPException) as ctx_pat:
            get_current_verified_professional(
                current_user=self.patient,
                db=self.db,
            )
        self.assertEqual(ctx_pat.exception.status_code, 403)
        self.assertIn("not a healthcare professional", ctx_pat.exception.detail)

        # 3. Verified doctor succeeds
        verified_user = get_current_verified_professional(
            current_user=self.doctor1,
            db=self.db,
        )
        self.assertEqual(verified_user.id, self.doctor1.id)


if __name__ == "__main__":
    unittest.main()
