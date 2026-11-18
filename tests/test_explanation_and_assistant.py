"""
HC-XCDSS Human-Centred Explanation Layer & AI Assistant Tests
Tests automatic role detection, role-tailored responses, AI Assistant flow, and clinical safety.
"""

import unittest
from fastapi.testclient import TestClient
from src.ai.assistant_service import AIAssistantService
from src.api.main import app, get_current_user
from src.db.models.user import User, UserRole
from src.db.session import SessionLocal
from src.db.models.analysis import Analysis


class DeterministicTestProvider:
    """Mock provider ensuring unit tests run deterministically without external API dependencies."""
    is_configured = False
    provider_name = "test_deterministic"
    model_name = "deterministic_v1"


class TestHumanCentredExplanationAndAssistant(unittest.TestCase):

    def setUp(self):
        self.test_provider = DeterministicTestProvider()
        self.service = AIAssistantService(provider=self.test_provider)
        self.mock_report = {
            "analysis_id": "TEST_CASE_01",
            "view": "Frontal",
            "detected_findings": ["Atelectasis", "Cardiomegaly"],
            "findings": {
                "Atelectasis": {"probability": 0.65, "threshold": 0.45, "detected": True},
                "Cardiomegaly": {"probability": 0.52, "threshold": 0.35, "detected": True},
                "Consolidation": {"probability": 0.15, "threshold": 0.40, "detected": False},
                "Edema": {"probability": 0.10, "threshold": 0.38, "detected": False},
                "Pleural Effusion": {"probability": 0.22, "threshold": 0.42, "detected": False},
            },
        }

    def test_patient_explanation_clarity(self):
        """Test patient receives plain language, empathetic explanation with no ML jargon."""
        res = self.service.answer_question(
            report_or_analysis=self.mock_report,
            question="What did the AI find?",
            role="patient"
        )
        self.assertEqual(res["role"], "patient")
        self.assertIn("Atelectasis", res["answer"])
        self.assertIn("Cardiomegaly", res["answer"])
        # Must not contain calibration claims
        self.assertNotIn("calibrated", res["answer"].lower())

    def test_patient_gradcam_explanation(self):
        """Test patient Grad-CAM question is explained as visual attention rather than diagnostic boundary."""
        res = self.service.answer_question(
            report_or_analysis=self.mock_report,
            question="Why was this area highlighted?",
            role="patient"
        )
        self.assertEqual(res["role"], "patient")
        self.assertIn("attention map", res["answer"].lower())
        self.assertIn("not a boundary of disease", res["answer"].lower())

    def test_patient_doctor_questions(self):
        """Test patient receives actionable questions for their doctor."""
        res = self.service.answer_question(
            report_or_analysis=self.mock_report,
            question="What should I ask my doctor?",
            role="patient"
        )
        self.assertIn("Questions to Discuss with Your Doctor", res["answer"])

    def test_physician_threshold_breakdown(self):
        """Test physician receives clinical statistics, operating thresholds, and validation context."""
        res = self.service.answer_question(
            report_or_analysis=self.mock_report,
            question="Evaluate radiological correlation with operating thresholds.",
            role="professional"
        )
        self.assertEqual(res["role"], "professional")
        self.assertIn("Operating Threshold", res["answer"])
        self.assertIn("CheXpert validation data", res["answer"])
        self.assertNotIn("calibrated", res["answer"].lower())

    def test_physician_gradcam_activation(self):
        """Test physician receives technical Grad-CAM activation details (features.norm5 layer)."""
        res = self.service.answer_question(
            report_or_analysis=self.mock_report,
            question="Explain the Grad-CAM spatial activation on this view.",
            role="professional"
        )
        self.assertEqual(res["role"], "professional")
        self.assertIn("norm5", res["answer"])
        self.assertIn("spatial activation", res["answer"].lower())

    def test_api_endpoint_rbac_automatic_role(self):
        """Test endpoint /api/assistant/{analysis_id} automatically enforces authenticated session role."""
        from src.api.main import ai_assistant_service
        orig_provider = ai_assistant_service.provider
        ai_assistant_service.provider = DeterministicTestProvider()

        client = TestClient(app)
        db = SessionLocal()
        try:
            analysis = db.query(Analysis).first()
            if not analysis:
                self.skipTest("No analysis in test database")

            # 1. Patient request
            user_patient = db.query(User).filter(User.role == UserRole.PATIENT).first()
            if not user_patient:
                user_patient = User(email="test_patient_rbac@example.com", role=UserRole.PATIENT, is_active=True)
                db.add(user_patient)
                db.commit()
                db.refresh(user_patient)

            app.dependency_overrides[get_current_user] = lambda: user_patient
            resp_p = client.post(
                f"/api/assistant/{analysis.id}",
                json={"message": "What did the AI find?"}
            )
            self.assertEqual(resp_p.status_code, 200)
            data_p = resp_p.json()
            self.assertEqual(data_p["role"], "patient")

            # 2. Professional request
            user_doctor = db.query(User).filter(User.role == UserRole.PROFESSIONAL).first()
            if not user_doctor:
                user_doctor = User(email="test_doctor_rbac@example.com", role=UserRole.PROFESSIONAL, is_active=True)
                db.add(user_doctor)
                db.commit()
                db.refresh(user_doctor)

            app.dependency_overrides[get_current_user] = lambda: user_doctor
            resp_d = client.post(
                f"/api/assistant/{analysis.id}",
                json={"message": "Evaluate radiological correlation with operating thresholds."}
            )
            self.assertEqual(resp_d.status_code, 200)
            data_d = resp_d.json()
            self.assertEqual(data_d["role"], "professional")
            self.assertIn("Operating Threshold", data_d["answer"])
        finally:
            ai_assistant_service.provider = orig_provider
            db.close()
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
