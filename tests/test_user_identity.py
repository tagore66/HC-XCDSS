"""
Tests for User Identity (Username, Display Name, Directory Display)
"""

import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.base import Base
from src.db.models.user import User, UserRole
from src.db.models.professional_profile import ProfessionalProfile, ProfessionalVerificationStatus
from src.auth.service import AuthService
from src.auth.schemas import UserRegisterRequest
from src.reviews.matching_service import DoctorMatchingService


class TestUserIdentity(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def test_user_registration_auto_username(self):
        req = UserRegisterRequest(
            email="tagore.patient@example.com",
            password="Password123!",
            full_name="Tagore Patient",
            role=UserRole.PATIENT,
        )
        user = AuthService.register_user(self.db, req)
        self.assertIsNotNone(user.username)
        self.assertIn("tagore", user.username.lower())
        self.assertEqual(user.get_display_name(), "Tagore Patient")

        d = user.to_dict()
        self.assertEqual(d["username"], user.username)
        self.assertEqual(d["display_name"], "Tagore Patient")

    def test_user_custom_username_and_uniqueness(self):
        req1 = UserRegisterRequest(
            email="doctor1@example.com",
            password="Password123!",
            username="drmohan",
            full_name="Mohan Specialist",
            role=UserRole.PROFESSIONAL,
        )
        user1 = AuthService.register_user(self.db, req1)
        self.assertEqual(user1.username, "drmohan")
        self.assertEqual(user1.get_display_name(), "Dr. Mohan Specialist")

        # Attempt to register another user with the same username
        req2 = UserRegisterRequest(
            email="doctor2@example.com",
            password="Password123!",
            username="drmohan",
            full_name="Another Mohan",
            role=UserRole.PROFESSIONAL,
        )
        with self.assertRaises(ValueError):
            AuthService.register_user(self.db, req2)

    def test_doctor_directory_display_name(self):
        req = UserRegisterRequest(
            email="doc.verified@hospital.org",
            password="Password123!",
            username="drsmith",
            full_name="John Smith",
            role=UserRole.PROFESSIONAL,
        )
        user = AuthService.register_user(self.db, req)
        prof = self.db.query(ProfessionalProfile).filter(ProfessionalProfile.user_id == user.id).first()
        prof.verification_status = ProfessionalVerificationStatus.VERIFIED
        prof.specialty = "Pulmonology"
        self.db.commit()

        directory = DoctorMatchingService.get_verified_directory(self.db)
        self.assertEqual(len(directory), 1)
        doc_entry = directory[0]
        self.assertEqual(doc_entry["display_name"], "Dr. John Smith")
        self.assertEqual(doc_entry["username"], "drsmith")


if __name__ == "__main__":
    unittest.main()
