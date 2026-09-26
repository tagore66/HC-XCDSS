"""
HC-XCDSS Persistent Storage Provider Tests
Verifies:
1. LocalStorageProvider file operations and path formatting
2. CloudinaryStorageProvider upload and deletion with mocked Cloudinary API
3. get_storage_provider() selection and graceful fallback
4. Professional verification document cloud persistence and secure 302 redirect
5. Authorization enforcement on local and remote document access
6. Local storage fallback and non-regression
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from src.storage.provider import (
    StorageProvider,
    LocalStorageProvider,
    CloudinaryStorageProvider,
    get_storage_provider,
)
from src.db.session import SessionLocal
from src.db.models import User, UserRole, ProfessionalProfile, Analysis
from src.auth.security import create_access_token, get_password_hash
from src.api.main import app


class TestStorageProviders(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.local_provider = LocalStorageProvider(base_dir=Path(self.temp_dir))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_local_storage_provider_save_analysis_artifact_from_path(self):
        src_file = Path(self.temp_dir) / "source_img.png"
        src_file.write_bytes(b"\x89PNG\r\n\x1a\nTEST_CONTENT")

        analysis_id = "test_analysis_1"
        url = self.local_provider.save_analysis_artifact(analysis_id, src_file, "uploaded_xray.png")

        self.assertEqual(url, f"/outputs/analyses/{analysis_id}/uploaded_xray.png")
        saved_file = Path(self.temp_dir) / "analyses" / analysis_id / "uploaded_xray.png"
        self.assertTrue(saved_file.exists())
        self.assertEqual(saved_file.read_bytes(), b"\x89PNG\r\n\x1a\nTEST_CONTENT")

    def test_local_storage_provider_save_analysis_artifact_from_bytes(self):
        analysis_id = "test_analysis_2"
        data = b'{"result": "ok"}'
        url = self.local_provider.save_analysis_artifact(analysis_id, data, "result.json")

        self.assertEqual(url, f"/outputs/analyses/{analysis_id}/result.json")
        saved_file = Path(self.temp_dir) / "analyses" / analysis_id / "result.json"
        self.assertTrue(saved_file.exists())
        self.assertEqual(saved_file.read_bytes(), data)

    def test_local_storage_provider_save_verification_document(self):
        user_id = "test_doctor_user"
        pdf_bytes = b"%PDF-1.4 test document"
        saved_path = self.local_provider.save_verification_document(user_id, "reg_cert", pdf_bytes, "license.pdf")

        self.assertTrue(Path(saved_path).exists())
        self.assertIn(user_id, saved_path)
        self.assertIn("reg_cert_license.pdf", saved_path)
        self.assertEqual(Path(saved_path).read_bytes(), pdf_bytes)

    def test_local_storage_provider_delete_analysis_artifacts(self):
        analysis_id = "test_del_1"
        self.local_provider.save_analysis_artifact(analysis_id, b"data", "test.txt")
        self.assertTrue((Path(self.temp_dir) / "analyses" / analysis_id).exists())

        deleted = self.local_provider.delete_analysis_artifacts(analysis_id)
        self.assertTrue(deleted)
        self.assertFalse((Path(self.temp_dir) / "analyses" / analysis_id).exists())

    def test_local_storage_provider_delete_all_analysis_artifacts(self):
        self.local_provider.save_analysis_artifact("a1", b"1", "1.txt")
        self.local_provider.save_analysis_artifact("a2", b"2", "2.txt")
        self.assertTrue((Path(self.temp_dir) / "analyses" / "a1").exists())
        self.assertTrue((Path(self.temp_dir) / "analyses" / "a2").exists())

        deleted = self.local_provider.delete_all_analysis_artifacts()
        self.assertTrue(deleted)
        self.assertFalse((Path(self.temp_dir) / "analyses" / "a1").exists())
        self.assertFalse((Path(self.temp_dir) / "analyses" / "a2").exists())

    @patch("cloudinary.uploader.upload")
    def test_cloudinary_storage_provider_save_analysis_artifact(self, mock_upload):
        mock_upload.return_value = {
            "secure_url": "https://res.cloudinary.com/demo/image/upload/v1/hc_xcdss/analyses/an1/xray.jpg",
            "url": "http://res.cloudinary.com/demo/image/upload/v1/hc_xcdss/analyses/an1/xray.jpg"
        }

        provider = CloudinaryStorageProvider(
            cloud_name="test_cloud",
            api_key="test_key",
            api_secret="test_secret"
        )

        url = provider.save_analysis_artifact("an1", b"image_bytes", "xray.jpg")
        self.assertEqual(url, "https://res.cloudinary.com/demo/image/upload/v1/hc_xcdss/analyses/an1/xray.jpg")

        mock_upload.assert_called_once_with(
            b"image_bytes",
            public_id="hc_xcdss/analyses/an1/xray",
            folder="hc_xcdss/analyses/an1",
            resource_type="image",
            overwrite=True,
            unique_filename=False
        )

    @patch("cloudinary.uploader.upload")
    def test_cloudinary_storage_provider_save_verification_document(self, mock_upload):
        mock_upload.return_value = {
            "secure_url": "https://res.cloudinary.com/demo/raw/upload/v1/hc_xcdss/verification_documents/u1/reg_cert_license.pdf"
        }

        provider = CloudinaryStorageProvider(
            cloud_name="test_cloud",
            api_key="test_key",
            api_secret="test_secret"
        )

        url = provider.save_verification_document("u1", "reg_cert", b"%PDF data", "license.pdf")
        self.assertEqual(url, "https://res.cloudinary.com/demo/raw/upload/v1/hc_xcdss/verification_documents/u1/reg_cert_license.pdf")

        mock_upload.assert_called_once_with(
            b"%PDF data",
            public_id="hc_xcdss/verification_documents/u1/reg_cert_license",
            folder="hc_xcdss/verification_documents/u1",
            resource_type="raw",
            overwrite=True,
            unique_filename=False
        )

    @patch("cloudinary.api.delete_folder")
    @patch("cloudinary.api.delete_resources_by_prefix")
    def test_cloudinary_storage_provider_delete_analysis_artifacts(self, mock_del_resources, mock_del_folder):
        provider = CloudinaryStorageProvider(
            cloud_name="test_cloud",
            api_key="test_key",
            api_secret="test_secret"
        )

        deleted = provider.delete_analysis_artifacts("an1")
        self.assertTrue(deleted)
        self.assertEqual(mock_del_resources.call_count, 2)  # image and raw
        mock_del_folder.assert_called_once_with("hc_xcdss/analyses/an1")

    def test_get_storage_provider_selection_and_fallback(self):
        # 1. Default when unset -> LocalStorageProvider
        with patch.dict(os.environ, {}, clear=True):
            provider = get_storage_provider()
            self.assertIsInstance(provider, LocalStorageProvider)

        # 2. Explicit STORAGE_PROVIDER=local -> LocalStorageProvider
        with patch.dict(os.environ, {"STORAGE_PROVIDER": "local"}):
            provider = get_storage_provider()
            self.assertIsInstance(provider, LocalStorageProvider)

        # 3. STORAGE_PROVIDER=cloudinary but missing keys -> fallback to LocalStorageProvider
        with patch.dict(os.environ, {"STORAGE_PROVIDER": "cloudinary"}):
            provider = get_storage_provider()
            self.assertIsInstance(provider, LocalStorageProvider)

        # 4. STORAGE_PROVIDER=cloudinary with keys -> CloudinaryStorageProvider
        with patch.dict(os.environ, {
            "STORAGE_PROVIDER": "cloudinary",
            "CLOUDINARY_CLOUD_NAME": "my_cloud",
            "CLOUDINARY_API_KEY": "my_key",
            "CLOUDINARY_API_SECRET": "my_secret",
        }):
            provider = get_storage_provider()
            self.assertIsInstance(provider, CloudinaryStorageProvider)


class TestCloudStorageIntegrationFlows(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()

        # Seed test admin and patient
        self.admin_user = User(
            email="admin_storage_test@hospital.org",
            username="admin_storage_test",
            hashed_password=get_password_hash("AdminPass123!"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.patient_user = User(
            email="patient_storage_test@hospital.org",
            username="pat_storage_test",
            hashed_password=get_password_hash("PatientPass123!"),
            role=UserRole.PATIENT,
            is_active=True,
        )

        self.db.add_all([self.admin_user, self.patient_user])
        self.db.commit()

        for u in [self.admin_user, self.patient_user]:
            self.db.refresh(u)

        self.token_admin = create_access_token({"sub": self.admin_user.id, "role": "ADMIN"})
        self.token_patient = create_access_token({"sub": self.patient_user.id, "role": "PATIENT"})

    def tearDown(self):
        self.db.query(Analysis).filter(Analysis.user_id == self.patient_user.id).delete(synchronize_session=False)
        self.db.query(ProfessionalProfile).filter(ProfessionalProfile.user_id == self.admin_user.id).delete(synchronize_session=False)
        self.db.query(User).filter(User.email.in_([
            "admin_storage_test@hospital.org",
            "patient_storage_test@hospital.org",
            "pro_cloud_test@hospital.org"
        ])).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_remote_verification_document_redirects_for_authorized_admin(self):
        cloud_url = "https://res.cloudinary.com/demo/raw/upload/v1/hc_xcdss/verification_documents/u123/reg_cert_license.pdf"
        pro_user = User(
            email="pro_cloud_test@hospital.org",
            username="pro_cloud_test",
            hashed_password=get_password_hash("DoctorPass123!"),
            role=UserRole.PROFESSIONAL,
            is_active=True,
        )
        self.db.add(pro_user)
        self.db.flush()

        profile = ProfessionalProfile(
            user_id=pro_user.id,
            registration_number="REG-CLOUD-999",
            state_medical_council="Medical Council",
            specialty="Radiology",
            registration_certificate_path=cloud_url,
            registration_certificate_filename="license.pdf",
        )
        self.db.add(profile)
        self.db.commit()

        # 1. Admin accesses document -> receives 302 Redirect to cloud URL
        response = self.client.get(
            f"/api/admin/professionals/{pro_user.id}/documents/registration_certificate",
            headers={"Authorization": f"Bearer {self.token_admin}"},
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], cloud_url)

        # 2. Unauthorized patient accesses document -> receives 403 Forbidden
        response_forbidden = self.client.get(
            f"/api/admin/professionals/{pro_user.id}/documents/registration_certificate",
            headers={"Authorization": f"Bearer {self.token_patient}"},
            follow_redirects=False
        )
        self.assertEqual(response_forbidden.status_code, 403)


if __name__ == "__main__":
    unittest.main()
