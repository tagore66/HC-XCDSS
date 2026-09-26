"""
HC-XCDSS JSON-to-Database Migration Utility

Migrates historical analysis records from outputs/analysis_history.json
into the SQLite database (Analysis, Report, AIContext models) idempotently.
"""

import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from sqlalchemy import text

from .base import Base
from .session import engine, SessionLocal
from .models import (
    User,
    PatientProfile,
    ProfessionalProfile,
    Analysis,
    Report,
    ReviewRequest,
    ProfessionalReview,
    AIContext,
    Conversation,
    ConversationMessage,
    Notification,
    NotificationType,
    NotificationEntityType,
    Payment,
    PaymentLedgerEntry,
    ProfessionalEarning,
)
from ..reporting.report_generator import generate_analysis_report
from ..ai.context_builder import build_patient_ai_context

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIRECTORY = PROJECT_ROOT / "outputs"
HISTORY_FILE = OUTPUT_DIRECTORY / "analysis_history.json"


def init_db():
    """
    Creates all database tables defined in Base metadata if they don't exist,
    and adds any missing columns non-destructively.
    """
    Base.metadata.create_all(bind=engine)

    # SQLite non-destructive schema patching for new columns (SQLite only)
    if engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            try:
                # Check users columns
                cursor = conn.execute(text("PRAGMA table_info(users)"))
                cols = [row[1] for row in cursor.fetchall()]
                if "username" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(50)"))
                    conn.commit()

                # Backfill any existing users without username
                cursor = conn.execute(text("SELECT id, email, full_name FROM users WHERE username IS NULL OR username = ''"))
                users_to_fix = cursor.fetchall()
                for u_id, u_email, u_name in users_to_fix:
                    cand = (u_name or (u_email.split('@')[0] if u_email else 'user'))
                    cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '', cand).lower().strip('._-')
                    base_un = cleaned[:30] if len(cleaned) >= 3 else "user"
                    un = base_un
                    c = 1
                    while conn.execute(text("SELECT 1 FROM users WHERE username = :un"), {"un": un}).first():
                        un = f"{base_un[:25]}{c}"
                        c += 1
                    conn.execute(text("UPDATE users SET username = :un WHERE id = :uid"), {"un": un, "uid": u_id})
                if users_to_fix:
                    conn.commit()
            except Exception as e:
                print(f"Schema check users warning: {e}")

            try:
                # Check review_requests columns
                cursor = conn.execute(text("PRAGMA table_info(review_requests)"))
                cols = [row[1] for row in cursor.fetchall()]
                if "payment_status" not in cols:
                    conn.execute(text("ALTER TABLE review_requests ADD COLUMN payment_status VARCHAR(32) DEFAULT 'UNPAID' NOT NULL"))
                    conn.commit()
                if "requested_information" not in cols:
                    conn.execute(text("ALTER TABLE review_requests ADD COLUMN requested_information TEXT"))
                    conn.commit()
                if "patient_additional_info" not in cols:
                    conn.execute(text("ALTER TABLE review_requests ADD COLUMN patient_additional_info TEXT"))
                    conn.commit()
            except Exception as e:
                print(f"Schema check review_requests warning: {e}")

            try:
                # Check professional_reviews columns
                cursor = conn.execute(text("PRAGMA table_info(professional_reviews)"))
                cols = [row[1] for row in cursor.fetchall()]
                if "clinical_summary" not in cols:
                    conn.execute(text("ALTER TABLE professional_reviews ADD COLUMN clinical_summary TEXT DEFAULT '' NOT NULL"))
                    conn.commit()
                if "clinical_impression" not in cols:
                    conn.execute(text("ALTER TABLE professional_reviews ADD COLUMN clinical_impression TEXT"))
                    conn.commit()
                if "finding_validations" not in cols:
                    conn.execute(text("ALTER TABLE professional_reviews ADD COLUMN finding_validations JSON DEFAULT '{}'"))
                    conn.commit()
                if "limitations" not in cols:
                    conn.execute(text("ALTER TABLE professional_reviews ADD COLUMN limitations TEXT"))
                    conn.commit()
                if "urgency" not in cols:
                    conn.execute(text("ALTER TABLE professional_reviews ADD COLUMN urgency VARCHAR(32) DEFAULT 'ROUTINE'"))
                    conn.commit()
                if "follow_up_required" not in cols:
                    conn.execute(text("ALTER TABLE professional_reviews ADD COLUMN follow_up_required BOOLEAN DEFAULT 0"))
                    conn.commit()
                if "message_to_patient" not in cols:
                    conn.execute(text("ALTER TABLE professional_reviews ADD COLUMN message_to_patient TEXT"))
                    conn.commit()
            except Exception as e:
                print(f"Schema check professional_reviews warning: {e}")

            try:
                # Check professional_profiles columns for verification workflow
                cursor = conn.execute(text("PRAGMA table_info(professional_profiles)"))
                cols = [row[1] for row in cursor.fetchall()]
                if "registration_number" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN registration_number VARCHAR(100)"))
                    conn.commit()
                if "state_medical_council" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN state_medical_council VARCHAR(150)"))
                    conn.commit()
                if "registration_year" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN registration_year VARCHAR(10)"))
                    conn.commit()
                if "registration_certificate_path" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN registration_certificate_path VARCHAR(500)"))
                    conn.commit()
                if "registration_certificate_filename" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN registration_certificate_filename VARCHAR(255)"))
                    conn.commit()
                if "identity_document_path" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN identity_document_path VARCHAR(500)"))
                    conn.commit()
                if "identity_document_filename" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN identity_document_filename VARCHAR(255)"))
                    conn.commit()
                if "supporting_document_path" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN supporting_document_path VARCHAR(500)"))
                    conn.commit()
                if "supporting_document_filename" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN supporting_document_filename VARCHAR(255)"))
                    conn.commit()
                if "verification_submitted_at" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN verification_submitted_at DATETIME"))
                    conn.commit()
                if "verified_at" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN verified_at DATETIME"))
                    conn.commit()
                if "verified_by" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN verified_by VARCHAR(36)"))
                    conn.commit()
                if "rejection_reason" not in cols:
                    conn.execute(text("ALTER TABLE professional_profiles ADD COLUMN rejection_reason TEXT"))
                    conn.commit()
            except Exception as e:
                print(f"Schema check professional_profiles warning: {e}")

    # Bootstrap default administrator account if none exists
    ensure_admin_account()


def ensure_admin_account(reset_if_exists: bool = False):
    """
    Ensures an Administrator account exists for development and platform governance.
    Reads ADMIN_EMAIL and ADMIN_PASSWORD from environment (with secure defaults).
    Hashes password using get_password_hash.
    If custom environment variables are provided or reset_if_exists is True, updates the admin credentials.
    """
    import os
    from ..auth.security import get_password_hash
    from .models.user import User, UserRole

    env_email = os.getenv("ADMIN_EMAIL")
    env_password = os.getenv("ADMIN_PASSWORD")
    admin_name = os.getenv("ADMIN_NAME", "Platform Administrator").strip()

    admin_email = (env_email.strip().lower() if env_email else "admin@hcxcdss.org")
    admin_password = (env_password.strip() if env_password else "Admin#HCXCDSS2026!")

    db = SessionLocal()
    try:
        # Check if admin already exists by email
        existing_user = db.query(User).filter(User.email == admin_email).first()
        if existing_user:
            existing_user.role = UserRole.ADMIN
            existing_user.is_active = True
            if env_password or reset_if_exists:
                existing_user.hashed_password = get_password_hash(admin_password)
                if admin_name:
                    existing_user.full_name = admin_name
            db.commit()
            return

        # Create new admin
        admin_user = User(
            email=admin_email,
            hashed_password=get_password_hash(admin_password),
            full_name=admin_name,
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[AdminBootstrap] Warning: Could not bootstrap admin account: {e}")
    finally:
        db.close()


def parse_iso_datetime(dt_str: Any) -> datetime:
    """
    Helper to parse ISO datetime string into timezone-aware datetime.
    """
    if isinstance(dt_str, datetime):
        return dt_str if dt_str.tzinfo else dt_str.replace(tzinfo=timezone.utc)
    if isinstance(dt_str, str):
        try:
            dt = datetime.fromisoformat(dt_str)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def migrate_json_history() -> Tuple[int, int, int]:
    """
    Migrates analysis_history.json into the SQLite database.

    Returns:
        Tuple[int, int, int]: (total_in_json, analyses_migrated, reports_migrated)
    """
    # 1. Initialize schema
    init_db()

    if not HISTORY_FILE.exists():
        return (0, 0, 0)

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return (0, 0, 0)
    except Exception as e:
        print(f"Error reading {HISTORY_FILE}: {e}")
        return (0, 0, 0)

    total_in_json = len(data)
    analyses_migrated = 0
    reports_migrated = 0

    db = SessionLocal()
    try:
        for item in data:
            if not isinstance(item, dict):
                continue

            analysis_id = item.get("analysis_id")
            if not analysis_id:
                continue

            # Check if analysis already exists in DB
            existing_analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

            if not existing_analysis:
                created_at_dt = parse_iso_datetime(item.get("created_at"))

                new_analysis = Analysis(
                    id=analysis_id,
                    user_id=None,  # Legacy analyses have no authenticated owner
                    view=item.get("view", "Frontal"),
                    image_path=item.get("image"),
                    findings_raw=item.get("findings", {}),
                    detected_findings=item.get("detected_findings", []),
                    heatmaps=item.get("heatmaps", {}),
                    patient_explanations=item.get("patient_explanations", []),
                    created_at=created_at_dt,
                )
                db.add(new_analysis)
                db.flush()  # Ensure foreign key exists for report
                analyses_migrated += 1
                analysis_obj = new_analysis
            else:
                analysis_obj = existing_analysis

            # Check if Report exists for this analysis
            existing_report = db.query(Report).filter(Report.analysis_id == analysis_id).first()
            report_data = item.get("report")

            if not existing_report:
                if not report_data or not isinstance(report_data, dict):
                    report_data = generate_analysis_report(item)

                new_report = Report(
                    analysis_id=analysis_id,
                    overall_summary=report_data.get("overall_summary", ""),
                    findings_evaluated=report_data.get("findings_evaluated", []),
                    findings_detected=report_data.get("findings_detected", []),
                    total_evaluated=report_data.get("total_evaluated", 0),
                    total_detected=report_data.get("total_detected", 0),
                    patient_interpretation=report_data.get("patient_interpretation", {}),
                    explainability=report_data.get("explainability", {}),
                    clinical_disclaimer=report_data.get("clinical_disclaimer", {}),
                    created_at=parse_iso_datetime(report_data.get("created_at") or item.get("created_at")),
                )
                db.add(new_report)
                db.flush()
                reports_migrated += 1
            else:
                if not report_data or not isinstance(report_data, dict):
                    report_data = existing_report.to_dict()

            # Check and prepare AIContext immediately
            existing_ai_context = db.query(AIContext).filter(AIContext.analysis_id == analysis_id).first()
            if not existing_ai_context and report_data:
                ai_ctx_data = build_patient_ai_context(report_data)
                new_ai_context = AIContext(
                    analysis_id=analysis_id,
                    context_data=ai_ctx_data,
                )
                db.add(new_ai_context)

        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

    return (total_in_json, analyses_migrated, reports_migrated)


if __name__ == "__main__":
    print("Initializing database and running history migration...")
    total, a_count, r_count = migrate_json_history()
    print(f"Total in JSON: {total}")
    print(f"New analyses migrated: {a_count}")
    print(f"New reports migrated: {r_count}")
