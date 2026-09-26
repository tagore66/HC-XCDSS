"""
Unit and regression tests for production deployment hardening and security configuration:
- JWT production secret enforcement vs development fallback
- Environment-configurable CORS origin parsing and wildcard rejection
- 15MB file size limit guard on /api/analyze
- Medical output file access authorization (unauthenticated, unauthorized, authorized, query token, doctor, admin)
- Path traversal defense on /outputs/analyses/
"""

import os
import shutil
import unittest
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient

from src.auth.security import (
    get_jwt_secret_key,
    create_access_token,
    decode_access_token,
    INSECURE_DEV_FALLBACK_KEY,
)
from src.api.main import (
    app,
    get_cors_origins,
    DEFAULT_CORS_ORIGINS,
    ANALYSIS_DIRECTORY,
)
from src.db.session import get_db, SessionLocal
from src.db.models.user import User, UserRole
from src.db.models.analysis import Analysis
from src.db.models.review_request import ReviewRequest, ReviewStatus
from src.db.models.professional_profile import ProfessionalProfile, ProfessionalVerificationStatus


class TestDeploymentHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self.db = SessionLocal()

        # Create unique test users
        self.patient_a = User(
            id="test-patient-hard-a",
            email="patient.a.hard@test.com",
            role=UserRole.PATIENT,
            is_active=True,
            full_name="Patient A Hardened",
        )
        self.patient_b = User(
            id="test-patient-hard-b",
            email="patient.b.hard@test.com",
            role=UserRole.PATIENT,
            is_active=True,
            full_name="Patient B Hardened",
        )
        self.doctor = User(
            id="test-doc-hard-01",
            email="doc.hard@test.com",
            role=UserRole.PROFESSIONAL,
            is_active=True,
            full_name="Dr. Hardened MD",
        )
        self.admin = User(
            id="test-admin-hard-01",
            email="admin.hard@test.com",
            role=UserRole.ADMIN,
            is_active=True,
            full_name="Admin Hardened",
        )

        # Clean existing test records if any
        for u in [self.patient_a, self.patient_b, self.doctor, self.admin]:
            existing = self.db.query(User).filter(User.id == u.id).first()
            if existing:
                self.db.delete(existing)
        self.db.commit()

        self.db.add_all([self.patient_a, self.patient_b, self.doctor, self.admin])
        self.db.commit()

        # Doctor profile
        doc_prof = ProfessionalProfile(
            user_id=self.doctor.id,
            verification_status=ProfessionalVerificationStatus.VERIFIED,
            license_number="LIC-HARD-99",
            specialty="Radiology",
        )
        self.db.add(doc_prof)

        # Setup test analysis for Patient A
        self.test_analysis_id = "test_analysis_hardened_001"
        existing_analysis = self.db.query(Analysis).filter(Analysis.id == self.test_analysis_id).first()
        if existing_analysis:
            self.db.delete(existing_analysis)
            self.db.commit()

        analysis_record = Analysis(
            id=self.test_analysis_id,
            user_id=self.patient_a.id,
            view="Frontal",
            image_path=f"/outputs/analyses/{self.test_analysis_id}/xray.png",
            findings_raw={"Atelectasis": {"probability": 0.55, "threshold": 0.4189, "detected": True}},
            detected_findings=["Atelectasis"],
            heatmaps={"Atelectasis": f"/outputs/analyses/{self.test_analysis_id}/atelectasis_gradcam.jpg"},
        )
        self.db.add(analysis_record)

        # Review request assigning doctor to this analysis
        review_req = ReviewRequest(
            id="rev-req-hard-001",
            patient_id=self.patient_a.id,
            analysis_id=self.test_analysis_id,
            professional_id=self.doctor.id,
            status=ReviewStatus.ASSIGNED,
            payment_status="PAID",
        )
        self.db.add(review_req)
        self.db.commit()

        # Create physical test file in analysis directory
        self.test_dir = ANALYSIS_DIRECTORY / self.test_analysis_id
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.test_image_file = self.test_dir / "xray.png"
        self.test_image_file.write_bytes(b"\x89PNG\r\n\x1a\nTEST_IMAGE_DATA")

        # Generate tokens
        self.token_patient_a = create_access_token({"sub": self.patient_a.id, "role": "PATIENT"})
        self.token_patient_b = create_access_token({"sub": self.patient_b.id, "role": "PATIENT"})
        self.token_doctor = create_access_token({"sub": self.doctor.id, "role": "PROFESSIONAL"})
        self.token_admin = create_access_token({"sub": self.admin.id, "role": "ADMIN"})

    def tearDown(self):
        try:
            # Clean database records
            self.db.query(ReviewRequest).filter(ReviewRequest.id == "rev-req-hard-001").delete()
            self.db.query(Analysis).filter(Analysis.id == self.test_analysis_id).delete()
            self.db.query(ProfessionalProfile).filter(ProfessionalProfile.user_id == self.doctor.id).delete()
            self.db.query(User).filter(User.id.in_([
                self.patient_a.id, self.patient_b.id, self.doctor.id, self.admin.id
            ])).delete()
            self.db.commit()
        finally:
            self.db.close()

        # Clean file artifacts
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # --------------------------------------------------
    # 1. JWT Configuration & Production Hardening Tests
    # --------------------------------------------------

    def test_jwt_production_secret_missing_raises_error(self):
        """In production mode, missing JWT_SECRET_KEY must raise RuntimeError."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False):
            if "JWT_SECRET_KEY" in os.environ:
                with patch.dict(os.environ, {"JWT_SECRET_KEY": ""}):
                    with self.assertRaises(RuntimeError) as ctx:
                        get_jwt_secret_key()
                    self.assertIn("JWT_SECRET_KEY", str(ctx.exception))
            else:
                with self.assertRaises(RuntimeError) as ctx:
                    get_jwt_secret_key()
                self.assertIn("JWT_SECRET_KEY", str(ctx.exception))

    def test_jwt_production_secret_insecure_fallback_raises_error(self):
        """In production mode, default insecure dev secret must be rejected."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": INSECURE_DEV_FALLBACK_KEY
        }):
            with self.assertRaises(RuntimeError) as ctx:
                get_jwt_secret_key()
            self.assertIn("JWT_SECRET_KEY", str(ctx.exception))

    def test_jwt_production_valid_secret_acceptance(self):
        """In production mode, an explicit non-default secret key is accepted."""
        custom_secret = "prod-super-secure-key-2026-audit-hardened"
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET_KEY": custom_secret
        }):
            resolved_key = get_jwt_secret_key()
            self.assertEqual(resolved_key, custom_secret)
            # Verify token encoding and decoding
            token = create_access_token({"sub": "user-prod-123"})
            payload = decode_access_token(token)
            self.assertEqual(payload["sub"], "user-prod-123")

    def test_jwt_development_fallback_acceptance(self):
        """In development mode, missing secret key falls back to dev key without error."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development", "JWT_SECRET_KEY": ""}):
            key = get_jwt_secret_key()
            self.assertEqual(key, INSECURE_DEV_FALLBACK_KEY)

    # --------------------------------------------------
    # 2. CORS Configuration Tests
    # --------------------------------------------------

    def test_cors_origins_custom_env_parsing(self):
        """CORS_ORIGINS comma-separated values should be parsed into a clean list."""
        with patch.dict(os.environ, {
            "CORS_ORIGINS": "https://portal.hc-xcdss.com, https://doctor.hc-xcdss.com, https://admin.hc-xcdss.com"
        }):
            origins = get_cors_origins()
            self.assertEqual(origins, [
                "https://portal.hc-xcdss.com",
                "https://doctor.hc-xcdss.com",
                "https://admin.hc-xcdss.com"
            ])

    def test_cors_origins_wildcard_rejected(self):
        """Wildcard '*' origin should be filtered out for security."""
        with patch.dict(os.environ, {
            "CORS_ORIGINS": "*, https://portal.hc-xcdss.com"
        }):
            origins = get_cors_origins()
            self.assertEqual(origins, ["https://portal.hc-xcdss.com"])
            self.assertNotIn("*", origins)

    def test_cors_origins_dev_fallback(self):
        """When CORS_ORIGINS is empty, default dev origins are returned."""
        with patch.dict(os.environ, {"CORS_ORIGINS": ""}):
            origins = get_cors_origins()
            self.assertEqual(origins, DEFAULT_CORS_ORIGINS)

    # --------------------------------------------------
    # 3. Upload Size Guard Tests
    # --------------------------------------------------

    def test_analyze_upload_oversized_rejection(self):
        """Uploads exceeding 15MB are rejected with 400 Bad Request before inference."""
        oversized_bytes = b"0" * (15 * 1024 * 1024 + 1024)  # ~15.001 MB
        headers = {"Authorization": f"Bearer {self.token_patient_a}"}
        response = self.client.post(
            "/api/analyze",
            files={"file": ("test_large.jpg", oversized_bytes, "image/jpeg")},
            data={"view": "Frontal"},
            headers=headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("15MB", response.json()["detail"])

    # --------------------------------------------------
    # 4. Medical Output File Access & Authorization Tests
    # --------------------------------------------------

    def test_medical_output_unauthenticated_access_rejected(self):
        """Direct access without auth header or query token returns 401 Unauthorized."""
        response = self.client.get(f"/outputs/analyses/{self.test_analysis_id}/xray.png")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Authentication credentials were not provided", response.json()["detail"])

    def test_medical_output_invalid_token_rejected(self):
        """Access with invalid/corrupt token returns 401 Unauthorized."""
        response = self.client.get(
            f"/outputs/analyses/{self.test_analysis_id}/xray.png",
            headers={"Authorization": "Bearer invalid.jwt.token"}
        )
        self.assertEqual(response.status_code, 401)

    def test_medical_output_unauthorized_patient_access_forbidden(self):
        """Patient B cannot access Patient A's analysis files (403 Forbidden)."""
        response = self.client.get(
            f"/outputs/analyses/{self.test_analysis_id}/xray.png",
            headers={"Authorization": f"Bearer {self.token_patient_b}"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access denied", response.json()["detail"])

    def test_medical_output_path_traversal_blocked(self):
        """Path traversal sequences (e.g. ../../) are blocked."""
        response = self.client.get(
            f"/outputs/analyses/{self.test_analysis_id}/../../main.py",
            headers={"Authorization": f"Bearer {self.token_patient_a}"}
        )
        # Should be rejected with 403 or 404
        self.assertIn(response.status_code, [403, 404])

    def test_medical_output_authorized_patient_bearer_token(self):
        """Owning Patient A can retrieve image via Authorization Bearer header."""
        response = self.client.get(
            f"/outputs/analyses/{self.test_analysis_id}/xray.png",
            headers={"Authorization": f"Bearer {self.token_patient_a}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"\x89PNG\r\n\x1a\nTEST_IMAGE_DATA")
        self.assertEqual(response.headers["content-type"], "image/png")

    def test_medical_output_authorized_patient_query_token(self):
        """Owning Patient A can retrieve image via '?token=' query parameter (browser <img> support)."""
        response = self.client.get(
            f"/outputs/analyses/{self.test_analysis_id}/xray.png?token={self.token_patient_a}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"\x89PNG\r\n\x1a\nTEST_IMAGE_DATA")

    def test_medical_output_authorized_doctor_access(self):
        """Assigned verified doctor can retrieve analysis image for their case."""
        response = self.client.get(
            f"/outputs/analyses/{self.test_analysis_id}/xray.png",
            headers={"Authorization": f"Bearer {self.token_doctor}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"\x89PNG\r\n\x1a\nTEST_IMAGE_DATA")

    def test_medical_output_authorized_admin_access(self):
        """System administrator can retrieve analysis files for audit/support."""
        response = self.client.get(
            f"/outputs/analyses/{self.test_analysis_id}/xray.png",
            headers={"Authorization": f"Bearer {self.token_admin}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"\x89PNG\r\n\x1a\nTEST_IMAGE_DATA")


if __name__ == "__main__":
    unittest.main()
