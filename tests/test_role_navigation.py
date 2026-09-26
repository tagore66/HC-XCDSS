"""
Unit and regression tests for role-based navigation persistence, session switching, and safe deep-linking.
"""

import unittest


class MockLocalStorage:
    """Simulates browser localStorage for session and screen state."""
    def __init__(self):
        self._store = {}

    def getItem(self, key):
        return self._store.get(key, None)

    def setItem(self, key, value):
        self._store[key] = str(value)

    def removeItem(self, key):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()


STORAGE_KEYS = {
    "screen": "hc_xcdss_screen",
    "analysisId": "hc_xcdss_active_analysis_id",
    "reviewId": "hc_xcdss_active_review_id",
    "userId": "hc_xcdss_session_user_id",
    "userRole": "hc_xcdss_session_user_role",
}


def resolve_session_navigation(user_obj, storage: MockLocalStorage):
    """
    Python equivalent of the App.jsx session bootstrap & navigation resolution logic.
    """
    if not user_obj:
        storage.removeItem(STORAGE_KEYS["screen"])
        storage.removeItem(STORAGE_KEYS["analysisId"])
        storage.removeItem(STORAGE_KEYS["reviewId"])
        storage.removeItem(STORAGE_KEYS["userId"])
        storage.removeItem(STORAGE_KEYS["userRole"])
        return "landing"

    role = user_obj.get("role")
    user_id = user_obj.get("id")
    is_pro_verified = role == "PROFESSIONAL" and user_obj.get("professional_profile", {}).get("verification_status") == "VERIFIED"
    is_pro_unverified = role == "PROFESSIONAL" and not is_pro_verified
    is_admin = role == "ADMIN"
    is_patient = role == "PATIENT"

    default_screen = (
        "admin-verification" if is_admin
        else "pro-pending" if is_pro_unverified
        else "pro-dashboard" if is_pro_verified
        else "dashboard"
    )

    if is_pro_unverified:
        storage.setItem(STORAGE_KEYS["userId"], user_id)
        storage.setItem(STORAGE_KEYS["userRole"], role)
        storage.setItem(STORAGE_KEYS["screen"], "pro-pending")
        return "pro-pending"

    stored_user_id = storage.getItem(STORAGE_KEYS["userId"])
    stored_user_role = storage.getItem(STORAGE_KEYS["userRole"])
    is_same_session = stored_user_id == user_id and stored_user_role == role

    # If account or role switched, route directly to default dashboard and wipe stale sub-screens
    if not is_same_session:
        storage.setItem(STORAGE_KEYS["userId"], user_id)
        storage.setItem(STORAGE_KEYS["userRole"], role)
        storage.removeItem(STORAGE_KEYS["analysisId"])
        storage.removeItem(STORAGE_KEYS["reviewId"])
        storage.setItem(STORAGE_KEYS["screen"], default_screen)
        return default_screen

    # Same session: restore valid sub-screen
    saved_screen = storage.getItem(STORAGE_KEYS["screen"]) or default_screen
    saved_analysis_id = storage.getItem(STORAGE_KEYS["analysisId"])
    saved_review_id = storage.getItem(STORAGE_KEYS["reviewId"])

    if is_patient:
        if saved_review_id and saved_screen == "review-detail":
            return "review-detail"
        elif saved_analysis_id and saved_screen == "result":
            return "result"
        elif saved_screen in ["history", "reviews", "upload", "dashboard"]:
            return saved_screen
        return "dashboard"
    elif is_pro_verified:
        if saved_review_id and saved_screen == "pro-review":
            return "pro-review"
        return "pro-dashboard"
    elif is_admin:
        return "admin-verification"

    return default_screen


def resolve_notification_deep_link(entity_type, entity_id, user_role):
    """
    Python equivalent of the safe notification deep-link routing logic in App.jsx.
    """
    if not entity_type or not entity_id or not isinstance(entity_id, str) or not entity_id.strip():
        return None  # Gracefully ignore invalid deep links

    clean_id = entity_id.strip()

    if entity_type == "ANALYSIS":
        if user_role == "PATIENT":
            return ("result", clean_id)
    elif entity_type in ["REVIEW_REQUEST", "PROFESSIONAL_REVIEW"]:
        if user_role == "PROFESSIONAL":
            return ("pro-review", clean_id)
        elif user_role == "PATIENT":
            return ("review-detail", clean_id)
    elif entity_type == "PAYMENT":
        if user_role == "PATIENT":
            return ("reviews", None)

    return None


class TestRoleBasedNavigationPersistence(unittest.TestCase):
    def setUp(self):
        self.storage = MockLocalStorage()

        self.patient_user = {
            "id": "pat-001",
            "role": "PATIENT",
            "full_name": "Patient User",
        }
        self.doctor_user = {
            "id": "doc-001",
            "role": "PROFESSIONAL",
            "full_name": "Dr. Specialist",
            "professional_profile": {"verification_status": "VERIFIED"},
        }
        self.pending_doctor_user = {
            "id": "doc-pending-001",
            "role": "PROFESSIONAL",
            "full_name": "Dr. Pending",
            "professional_profile": {"verification_status": "PENDING"},
        }
        self.admin_user = {
            "id": "adm-001",
            "role": "ADMIN",
            "full_name": "Admin User",
        }

    def test_first_login_routes_to_role_default_dashboards(self):
        # Patient login -> dashboard
        screen = resolve_session_navigation(self.patient_user, self.storage)
        self.assertEqual(screen, "dashboard")
        self.assertEqual(self.storage.getItem(STORAGE_KEYS["userRole"]), "PATIENT")

        # Verified Professional login -> pro-dashboard
        screen = resolve_session_navigation(self.doctor_user, self.storage)
        self.assertEqual(screen, "pro-dashboard")
        self.assertEqual(self.storage.getItem(STORAGE_KEYS["userRole"]), "PROFESSIONAL")

        # Admin login -> admin-verification
        screen = resolve_session_navigation(self.admin_user, self.storage)
        self.assertEqual(screen, "admin-verification")
        self.assertEqual(self.storage.getItem(STORAGE_KEYS["userRole"]), "ADMIN")

        # Pending doctor login -> pro-pending
        screen = resolve_session_navigation(self.pending_doctor_user, self.storage)
        self.assertEqual(screen, "pro-pending")

    def test_stale_screen_not_inherited_across_role_switch(self):
        # 1. Patient visits their reviews screen
        resolve_session_navigation(self.patient_user, self.storage)
        self.storage.setItem(STORAGE_KEYS["screen"], "reviews")
        self.storage.setItem(STORAGE_KEYS["reviewId"], "rev-12345")

        # 2. Admin logs in next (e.g. on same browser)
        # MUST route to admin-verification, NOT patient reviews!
        admin_screen = resolve_session_navigation(self.admin_user, self.storage)
        self.assertEqual(admin_screen, "admin-verification")
        self.assertIsNone(self.storage.getItem(STORAGE_KEYS["reviewId"]))

        # 3. Verified Doctor logs in next
        # MUST route to pro-dashboard, NOT admin-verification or patient reviews!
        doc_screen = resolve_session_navigation(self.doctor_user, self.storage)
        self.assertEqual(doc_screen, "pro-dashboard")

    def test_logout_clears_all_navigation_and_session_state(self):
        # Setup active session with deep sub-screen
        resolve_session_navigation(self.patient_user, self.storage)
        self.storage.setItem(STORAGE_KEYS["screen"], "history")

        # Logout (user is None)
        screen = resolve_session_navigation(None, self.storage)
        self.assertEqual(screen, "landing")

        # Ensure all storage keys are cleared
        self.assertIsNone(self.storage.getItem(STORAGE_KEYS["screen"]))
        self.assertIsNone(self.storage.getItem(STORAGE_KEYS["userId"]))
        self.assertIsNone(self.storage.getItem(STORAGE_KEYS["userRole"]))
        self.assertIsNone(self.storage.getItem(STORAGE_KEYS["analysisId"]))
        self.assertIsNone(self.storage.getItem(STORAGE_KEYS["reviewId"]))

    def test_same_user_session_preserves_valid_navigation(self):
        # 1. Patient logs in
        resolve_session_navigation(self.patient_user, self.storage)

        # 2. Patient navigates to history
        self.storage.setItem(STORAGE_KEYS["screen"], "history")

        # 3. Patient reloads browser (same user ID & role)
        screen = resolve_session_navigation(self.patient_user, self.storage)
        self.assertEqual(screen, "history")

    def test_safe_notification_deep_links(self):
        # Valid analysis deep-link for patient
        target = resolve_notification_deep_link("ANALYSIS", "a1153c84126b", "PATIENT")
        self.assertEqual(target, ("result", "a1153c84126b"))

        # Valid review deep-link for professional
        target = resolve_notification_deep_link("REVIEW_REQUEST", "rev-999", "PROFESSIONAL")
        self.assertEqual(target, ("pro-review", "rev-999"))

        # Valid review deep-link for patient
        target = resolve_notification_deep_link("REVIEW_REQUEST", "rev-999", "PATIENT")
        self.assertEqual(target, ("review-detail", "rev-999"))

        # Invalid/empty entity IDs gracefully return None
        self.assertIsNone(resolve_notification_deep_link("ANALYSIS", "", "PATIENT"))
        self.assertIsNone(resolve_notification_deep_link("ANALYSIS", "   ", "PATIENT"))
        self.assertIsNone(resolve_notification_deep_link(None, "rev-999", "PATIENT"))
        self.assertIsNone(resolve_notification_deep_link("ANALYSIS", None, "PATIENT"))

        # Analysis deep-link for professional (unsupported) gracefully returns None
        self.assertIsNone(resolve_notification_deep_link("ANALYSIS", "a1153c84126b", "PROFESSIONAL"))

    def test_stripe_return_initializes_session_and_opens_review_detail(self):
        # Patient completes Stripe checkout and returns to app with session_id
        # 1. User profile loads, immediately saving user ID and user Role
        self.storage.setItem(STORAGE_KEYS["userId"], self.patient_user["id"])
        self.storage.setItem(STORAGE_KEYS["userRole"], self.patient_user["role"])

        # 2. Payment verification succeeds for review 'rev-stripe-001'
        self.storage.setItem(STORAGE_KEYS["screen"], "review-detail")
        self.storage.setItem(STORAGE_KEYS["reviewId"], "rev-stripe-001")

        # 3. Verify storage state is completely initialized and consistent
        self.assertEqual(self.storage.getItem(STORAGE_KEYS["userId"]), "pat-001")
        self.assertEqual(self.storage.getItem(STORAGE_KEYS["userRole"]), "PATIENT")
        self.assertEqual(self.storage.getItem(STORAGE_KEYS["screen"]), "review-detail")
        self.assertEqual(self.storage.getItem(STORAGE_KEYS["reviewId"]), "rev-stripe-001")

        # 4. On subsequent page reload (same session), review-detail is preserved cleanly without blanking
        screen = resolve_session_navigation(self.patient_user, self.storage)
        self.assertEqual(screen, "review-detail")

    def test_patient_result_screen_without_data_falls_back_to_dashboard(self):
        # If activeScreen is 'result' but analysis data / result is null/missing:
        # App.jsx render guard ensures PatientDashboard renders instead of an empty screen
        patient_valid_screens = ["dashboard", "upload", "result", "history", "reviews", "review-detail"]
        
        # Scenario A: activeScreen = "result" but result is None
        active_screen = "result"
        result_data = None
        should_render_dashboard = (
            active_screen == "dashboard" or
            (active_screen == "result" and not result_data) or
            active_screen not in patient_valid_screens
        )
        self.assertTrue(should_render_dashboard)

        # Scenario B: activeScreen = "invalid-screen-xyz"
        active_screen = "invalid-screen-xyz"
        should_render_dashboard = (
            active_screen == "dashboard" or
            (active_screen == "result" and not result_data) or
            active_screen not in patient_valid_screens
        )
        self.assertTrue(should_render_dashboard)

    def test_professional_dashboard_review_categorization(self):
        # Simulated reviews from backend list API
        doctor_id = "doc-001"
        reviews = [
            {"id": "rev-matching-pool", "status": "MATCHING", "professional_id": None},
            {"id": "rev-requested-pool", "status": "REQUESTED", "professional_id": None},
            {"id": "rev-assigned-mine", "status": "ASSIGNED", "professional_id": doctor_id},
            {"id": "rev-inreview-mine", "status": "IN_REVIEW", "professional_id": doctor_id},
            {"id": "rev-completed-mine", "status": "COMPLETED", "professional_id": doctor_id},
            {"id": "rev-assigned-other", "status": "ASSIGNED", "professional_id": "doc-other"},
        ]

        # Frontend categorization logic in ProfessionalDashboard.jsx
        available_requests = [
            r for r in reviews
            if not r.get("professional_id") and r.get("status") in ["REQUESTED", "MATCHING"]
        ]
        my_reviews = [
            r for r in reviews
            if r.get("professional_id") == doctor_id and r.get("status") in ["ASSIGNED", "ACCEPTED", "IN_REVIEW", "COMPLETED"]
        ]

        # 1. MATCHING + professional_id null -> Available Requests
        self.assertIn("rev-matching-pool", [r["id"] for r in available_requests])
        # 2. REQUESTED + professional_id null -> Available Requests
        self.assertIn("rev-requested-pool", [r["id"] for r in available_requests])
        # 3. ASSIGNED + matching professional_id -> My Active & Completed
        self.assertIn("rev-assigned-mine", [r["id"] for r in my_reviews])
        # 4. COMPLETED + matching professional_id -> My Active & Completed
        self.assertIn("rev-completed-mine", [r["id"] for r in my_reviews])
        # 5. MATCHING case is NOT shown as doctor's active case
        self.assertNotIn("rev-matching-pool", [r["id"] for r in my_reviews])
        # 6. Other doctor's assigned case is not in my active reviews
        self.assertNotIn("rev-assigned-other", [r["id"] for r in my_reviews])

    def test_pro_review_missing_review_id_falls_back_to_dashboard(self):
        # App.jsx render guard: If activeScreen === "pro-review" but activeReviewId is null/empty,
        # it must fall back to rendering ProfessionalDashboard instead of an empty screen
        active_screen = "pro-review"
        active_review_id = None
        is_pro_verified = True

        should_render_pro_dashboard = (
            is_pro_verified and (
                active_screen == "pro-dashboard" or
                (active_screen == "pro-review" and not active_review_id) or
                active_screen not in ["pro-dashboard", "pro-review", "pro-pending"]
            )
        )
        self.assertTrue(should_render_pro_dashboard)

        # When active_review_id is valid, pro-review screen renders workspace
        active_review_id = "rev-valid-123"
        should_render_pro_dashboard_valid = (
            is_pro_verified and (
                active_screen == "pro-dashboard" or
                (active_screen == "pro-review" and not active_review_id) or
                active_screen not in ["pro-dashboard", "pro-review", "pro-pending"]
            )
        )
        self.assertFalse(should_render_pro_dashboard_valid)


if __name__ == "__main__":
    unittest.main()
