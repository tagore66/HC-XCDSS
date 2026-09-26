"""
HC-XCDSS Analysis History Store (Database-backed with User-Scoped Ownership)
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from ..db.session import SessionLocal
from ..db.models import Analysis, Report, User, UserRole, AIContext
from ..reporting.report_generator import generate_analysis_report


def parse_datetime_helper(dt_val: Any) -> datetime:
    """
    Safely parse datetime string or object into timezone-aware datetime.
    """
    if isinstance(dt_val, datetime):
        return dt_val if dt_val.tzinfo else dt_val.replace(tzinfo=timezone.utc)
    if isinstance(dt_val, str):
        try:
            dt = datetime.fromisoformat(dt_val)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def get_all_analyses(current_user: Optional[User] = None) -> List[Dict[str, Any]]:
    """
    Retrieve analyses based on ownership rules:
    - If unauthenticated: returns empty list (private platform).
    - If ADMIN: returns all analyses.
    - If PATIENT: returns analyses owned by that patient.
    - If PROFESSIONAL: returns analyses owned by that professional or assigned to them via ReviewRequest.
    """
    if current_user is None:
        return []

    db = SessionLocal()
    try:
        query = db.query(Analysis)

        if current_user.role == UserRole.ADMIN:
            # Admins see everything
            pass
        elif current_user.role == UserRole.PROFESSIONAL:
            # Professional sees own analyses OR analyses for review requests assigned to them
            from ..db.models.review_request import ReviewRequest
            assigned_analysis_ids = [
                r.analysis_id
                for r in db.query(ReviewRequest.analysis_id)
                .filter(ReviewRequest.professional_id == current_user.id)
                .all()
            ]
            query = query.filter(
                (Analysis.user_id == current_user.id) | (Analysis.id.in_(assigned_analysis_ids))
            )
        else:
            # Patients see their own analyses
            query = query.filter(Analysis.user_id == current_user.id)

        analyses = query.order_by(Analysis.created_at.desc()).all()

        results = []
        for a in analyses:
            data = a.to_dict()
            if "report" not in data:
                data["report"] = generate_analysis_report(data)
            results.append(data)

        return results
    finally:
        db.close()


def get_analysis(analysis_id: str, current_user: Optional[User] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific analysis by its unique ID with strict ownership and authorized professional checks:
    - Unauthenticated callers get None.
    - ADMIN users can access any analysis.
    - Non-admin authenticated users can access their own analyses.
    - Verified professionals can access analyses assigned to them in an authorized ReviewRequest.
    """
    if current_user is None:
        return None

    db = SessionLocal()
    try:
        a = (
            db.query(Analysis)
            .filter(Analysis.id == analysis_id)
            .first()
        )
        if not a:
            return None

        # Check access permission
        if current_user.role != UserRole.ADMIN:
            if a.user_id == current_user.id:
                # Owner has access
                pass
            elif current_user.role == UserRole.PROFESSIONAL:
                # Check if this professional is assigned/authorized for a review request on this analysis
                from ..db.models.review_request import ReviewRequest
                has_authorized_review = db.query(ReviewRequest).filter(
                    ReviewRequest.analysis_id == analysis_id,
                    ReviewRequest.professional_id == current_user.id
                ).first()
                if not has_authorized_review:
                    return None
            else:
                return None

        data = a.to_dict()
        if "report" not in data:
            data["report"] = generate_analysis_report(data)
        return data
    finally:
        db.close()


def save_analysis(result: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Save a newly completed analysis and its structured report to the database.
    """
    analysis_id = result.get("analysis_id")
    if not analysis_id:
        raise ValueError("Cannot save analysis without an analysis_id.")

    db = SessionLocal()
    try:
        # Check if record already exists
        existing = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        created_at_dt = parse_datetime_helper(result.get("created_at"))

        if existing:
            analysis_obj = existing
        else:
            analysis_obj = Analysis(
                id=analysis_id,
                user_id=user_id,
                view=result.get("view", "Frontal"),
                image_path=result.get("image"),
                findings_raw=result.get("findings", {}),
                detected_findings=result.get("detected_findings", []),
                heatmaps=result.get("heatmaps", {}),
                patient_explanations=result.get("patient_explanations", []),
                created_at=created_at_dt,
            )
            db.add(analysis_obj)
            db.flush()

        # Save Report
        report_data = result.get("report")
        if not report_data or not isinstance(report_data, dict):
            report_data = generate_analysis_report(result)
            result["report"] = report_data

        existing_report = db.query(Report).filter(Report.analysis_id == analysis_id).first()
        if not existing_report:
            report_obj = Report(
                analysis_id=analysis_id,
                overall_summary=report_data.get("overall_summary", ""),
                findings_evaluated=report_data.get("findings_evaluated", []),
                findings_detected=report_data.get("findings_detected", []),
                total_evaluated=report_data.get("total_evaluated", 0),
                total_detected=report_data.get("total_detected", 0),
                patient_interpretation=report_data.get("patient_interpretation", {}),
                explainability=report_data.get("explainability", {}),
                clinical_disclaimer=report_data.get("clinical_disclaimer", {}),
                created_at=parse_datetime_helper(report_data.get("created_at") or result.get("created_at")),
            )
            db.add(report_obj)
            db.flush()

        # Automatically prepare and persist AIContext immediately (Milestone 6.5)
        existing_ai_ctx = db.query(AIContext).filter(AIContext.analysis_id == analysis_id).first()
        if not existing_ai_ctx and report_data:
            from ..ai.context_builder import build_patient_ai_context
            ai_ctx_data = build_patient_ai_context(report_data)
            ai_ctx_obj = AIContext(
                analysis_id=analysis_id,
                context_data=ai_ctx_data,
            )
            db.add(ai_ctx_obj)

        db.commit()

        # Trigger ANALYSIS_COMPLETED notification for authenticated user
        if user_id:
            try:
                from ..notifications.service import NotificationService
                NotificationService.on_analysis_completed(
                    db=db,
                    user_id=user_id,
                    analysis_id=analysis_id,
                    view=result.get("view", "Frontal"),
                )
            except Exception as notif_err:
                print(f"Analysis notification warning: {notif_err}")

        # Refresh response dictionary
        saved_dict = analysis_obj.to_dict()
        result["created_at"] = saved_dict["created_at"]
        result["user_id"] = user_id
        return result
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def delete_analysis(analysis_id: str, current_user: Optional[User] = None) -> Optional[bool]:
    """
    Delete a specific analysis and its associated cascade records with ownership validation.
    Returns True if deleted, False if permission denied or error, None if not found.
    """
    db = SessionLocal()
    try:
        a = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not a:
            return None

        # Ownership permission check
        if a.user_id is not None:
            if current_user is None:
                return False
            if current_user.role != UserRole.ADMIN and a.user_id != current_user.id:
                return False

        db.delete(a)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def delete_all_analyses() -> bool:
    """
    Delete all analysis records from the database (admin maintenance).
    """
    db = SessionLocal()
    try:
        db.query(Analysis).delete()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()