"""
HC-XCDSS Review Workflow Business Logic Service
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session
from ..db.models.user import User, UserRole
from ..db.models.analysis import Analysis
from ..db.models.professional_profile import ProfessionalProfile, ProfessionalVerificationStatus
from ..db.models.review_request import ReviewRequest, ReviewStatus, ProfessionalReview
from ..reporting.report_generator import generate_analysis_report
from ..notifications.service import NotificationService
from ..notifications.email_service import EmailService
from .schemas import (
    CreateReviewRequest,
    ProfessionalReviewSubmitRequest,
    ProfessionalAssessmentDraftRequest,
    ProfessionalAssessmentSubmitRequest,
)


class ReviewService:
    """
    Core business logic for patient review requests and professional review lifecycle.
    """

    # --------------------------------------------------
    # Patient Operations
    # --------------------------------------------------

    @staticmethod
    def create_review_request(
        db: Session,
        patient: User,
        analysis_id: str,
        patient_message: Optional[str] = None,
        preferred_professional_id: Optional[str] = None,
    ) -> ReviewRequest:
        """
        Create a new review request for an analysis owned by the patient.
        If an existing request for this analysis and patient is UNPAID, reuse it.
        """
        analysis_id_clean = analysis_id.strip()

        # 1. Verify analysis exists and belongs to this patient
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id_clean).first()
        if not analysis:
            raise ValueError(f"Analysis '{analysis_id_clean}' was not found.")

        if analysis.user_id is None or analysis.user_id != patient.id:
            raise ValueError("You can only request professional reviews for your own analyses.")

        # 2. Handle optional preferred professional
        preferred_pro_id = None
        status = ReviewStatus.REQUESTED
        assigned_at = None

        if preferred_professional_id:
            preferred_user = (
                db.query(User)
                .join(ProfessionalProfile, User.id == ProfessionalProfile.user_id)
                .filter(
                    User.id == preferred_professional_id,
                    User.role == UserRole.PROFESSIONAL,
                    User.is_active == True,
                    ProfessionalProfile.verification_status == ProfessionalVerificationStatus.VERIFIED,
                )
                .first()
            )
            if not preferred_user:
                raise ValueError("Selected professional is not active or verified.")

            preferred_pro_id = preferred_user.id
            status = ReviewStatus.ASSIGNED
            assigned_at = datetime.now(timezone.utc)

        # 3. Check for existing UNPAID request for the same patient + analysis to reuse (Idempotency)
        existing_unpaid = (
            db.query(ReviewRequest)
            .filter(
                ReviewRequest.analysis_id == analysis_id_clean,
                ReviewRequest.patient_id == patient.id,
                ReviewRequest.payment_status == "UNPAID",
                ReviewRequest.status != ReviewStatus.CANCELLED,
            )
            .order_by(ReviewRequest.created_at.desc())
            .first()
        )
        if existing_unpaid:
            existing_unpaid.professional_id = preferred_pro_id
            existing_unpaid.status = status
            existing_unpaid.patient_message = patient_message.strip() if patient_message else None
            existing_unpaid.requested_at = datetime.now(timezone.utc)
            existing_unpaid.assigned_at = assigned_at
            db.commit()
            db.refresh(existing_unpaid)
            return existing_unpaid

        # 4. Check for active review request on this analysis (PAID / in-progress)
        active_statuses = [
            ReviewStatus.REQUESTED,
            ReviewStatus.ASSIGNED,
            ReviewStatus.ACCEPTED,
            ReviewStatus.IN_REVIEW,
        ]
        existing_active = (
            db.query(ReviewRequest)
            .filter(
                ReviewRequest.analysis_id == analysis_id_clean,
                ReviewRequest.status.in_(active_statuses),
            )
            .first()
        )
        if existing_active:
            raise ValueError(
                f"An active review request already exists for this analysis (current status: {existing_active.status.value})."
            )

        # 5. Create fresh request
        new_request = ReviewRequest(
            analysis_id=analysis_id_clean,
            patient_id=patient.id,
            professional_id=preferred_pro_id,
            status=status,
            patient_message=patient_message.strip() if patient_message else None,
            payment_status="UNPAID",
            requested_at=datetime.now(timezone.utc),
            assigned_at=assigned_at,
        )

        db.add(new_request)
        db.commit()
        db.refresh(new_request)

        # Do not fire specialist notifications before payment is completed
        return new_request

    @staticmethod
    def get_patient_review_requests(db: Session, patient: User) -> List[ReviewRequest]:
        """
        Get all review requests created by the patient.
        Excludes abandoned UNPAID and CANCELLED requests.
        """
        return (
            db.query(ReviewRequest)
            .filter(
                ReviewRequest.patient_id == patient.id,
                ReviewRequest.payment_status != "UNPAID",
                ReviewRequest.status != ReviewStatus.CANCELLED,
            )
            .order_by(ReviewRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def get_review_request_by_id(
        db: Session,
        review_id: str,
        current_user: User
    ) -> Optional[ReviewRequest]:
        """
        Retrieve a specific review request enforcing RBAC:
        - Admin can access any request.
        - Patient can only access their own requests.
        - Professional can access requests assigned to them or unassigned pool requests.
        - Professional CANNOT access cases specifically assigned to another doctor.
        """
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        if not req:
            return None

        if current_user.role == UserRole.ADMIN:
            return req

        if current_user.role == UserRole.PATIENT:
            if req.patient_id == current_user.id:
                return req
            return None

        if current_user.role == UserRole.PROFESSIONAL:
            # Case 1: Assigned to this specific professional
            if req.professional_id == current_user.id:
                return req
            # Case 2: Open pool request (not assigned to another doctor)
            if req.professional_id is None and req.status in [ReviewStatus.REQUESTED, ReviewStatus.MATCHING]:
                return req
            return None

        return None

    @staticmethod
    def get_analysis_review(
        db: Session,
        analysis_id: str,
        current_user: User
    ) -> Optional[Dict[str, Any]]:
        """
        Get review request and professional review for a specific analysis.
        """
        req = (
            db.query(ReviewRequest)
            .filter(ReviewRequest.analysis_id == analysis_id)
            .order_by(ReviewRequest.created_at.desc())
            .first()
        )
        if not req:
            return None

        # Check ownership
        if current_user.role != UserRole.ADMIN and req.patient_id != current_user.id and req.professional_id != current_user.id:
            return None

        return ReviewService.build_review_detail_response(db, req)

    @staticmethod
    def cancel_review_request(
        db: Session,
        review_id: str,
        patient: User
    ) -> ReviewRequest:
        """
        Cancel an active review request by patient owner (only allowed before ACCEPTED).
        """
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        if not req or req.patient_id != patient.id:
            raise ValueError(f"Review request '{review_id}' not found or access denied.")

        if req.status in [ReviewStatus.ACCEPTED, ReviewStatus.IN_REVIEW, ReviewStatus.COMPLETED]:
            raise ValueError(f"Cannot cancel review request after it has been accepted by a physician (status: {req.status.value}).")

        if req.status in [ReviewStatus.CANCELLED, ReviewStatus.DECLINED, ReviewStatus.EXPIRED]:
            raise ValueError(f"Cannot cancel a request that is already {req.status.value.lower()}.")

        req.status = ReviewStatus.CANCELLED
        req.cancelled_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(req)

        try:
            if req.professional_id:
                NotificationService.on_review_cancelled(db, req.professional_id, req.id, patient.full_name or "Patient")
        except Exception as e:
            print(f"Notification error: {e}")

        return req

    # --------------------------------------------------
    # Professional Operations (Verified Only)
    # --------------------------------------------------

    @staticmethod
    def get_filtered_for_professional(
        db: Session,
        professional: User,
        filter_type: str = "all"
    ) -> List[ReviewRequest]:
        """
        List requests based on filter:
        - available: unassigned pool cases (professional_id is None and status in [REQUESTED, MATCHING])
        - assigned: cases assigned/accepted/in_review for this professional
        - completed: completed cases reviewed by this professional
        - all / default: both unassigned pool cases and all assigned/in-progress/completed cases for this professional
        """
        query = db.query(ReviewRequest).filter(ReviewRequest.payment_status == "PAID")
        filter_clean = (filter_type or "all").lower().strip()

        if filter_clean == "available":
            return (
                query.filter(
                    (ReviewRequest.professional_id == None) &
                    ReviewRequest.status.in_([ReviewStatus.REQUESTED, ReviewStatus.MATCHING])
                )
                .order_by(ReviewRequest.created_at.desc())
                .all()
            )
        elif filter_clean == "assigned":
            return (
                query.filter(
                    ReviewRequest.professional_id == professional.id,
                    ReviewRequest.status.in_([ReviewStatus.ASSIGNED, ReviewStatus.ACCEPTED, ReviewStatus.IN_REVIEW])
                )
                .order_by(ReviewRequest.created_at.desc())
                .all()
            )
        elif filter_clean == "completed":
            return (
                query.filter(
                    ReviewRequest.professional_id == professional.id,
                    ReviewRequest.status == ReviewStatus.COMPLETED
                )
                .order_by(ReviewRequest.completed_at.desc())
                .all()
            )
        else:
            # "all" / fallback: open unassigned pool cases OR any case assigned to this professional
            return (
                query.filter(
                    (
                        (ReviewRequest.professional_id == None) &
                        ReviewRequest.status.in_([ReviewStatus.REQUESTED, ReviewStatus.MATCHING])
                    )
                    |
                    (
                        (ReviewRequest.professional_id == professional.id) &
                        ReviewRequest.status.in_([
                            ReviewStatus.ASSIGNED,
                            ReviewStatus.ACCEPTED,
                            ReviewStatus.IN_REVIEW,
                            ReviewStatus.COMPLETED
                        ])
                    )
                )
                .order_by(ReviewRequest.created_at.desc())
                .all()
            )

    @staticmethod
    def accept_review_request(
        db: Session,
        review_id: str,
        professional: User
    ) -> ReviewRequest:
        """
        Professional accepts a review request with atomic concurrency check.
        """
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        if not req:
            raise ValueError(f"Review request '{review_id}' was not found.")

        if req.payment_status != "PAID":
            raise PermissionError("Cannot accept review request before consultation payment has been completed.")

        if req.professional_id and req.professional_id != professional.id:
            raise PermissionError("This review request is assigned to another professional.")

        if req.status not in [ReviewStatus.REQUESTED, ReviewStatus.ASSIGNED, ReviewStatus.MATCHING]:
            raise ValueError(f"Cannot accept review request with status '{req.status.value}'.")

        req.professional_id = professional.id
        req.status = ReviewStatus.ACCEPTED
        req.accepted_at = datetime.now(timezone.utc)
        if not req.assigned_at:
            req.assigned_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(req)

        try:
            pro_name = professional.full_name or "Dr. Specialist"
            NotificationService.on_review_accepted(db, req.patient_id, req.id, pro_name)
        except Exception as e:
            print(f"Notification error: {e}")

        return req

    @staticmethod
    def start_review(
        db: Session,
        review_id: str,
        professional: User
    ) -> ReviewRequest:
        """
        Transition request from ACCEPTED to IN_REVIEW.
        """
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        if not req or req.professional_id != professional.id:
            raise ValueError("Review request not found or not assigned to you.")

        if req.status != ReviewStatus.ACCEPTED:
            raise ValueError(f"Review request must be in 'ACCEPTED' state to start review (current: {req.status.value}).")

        req.status = ReviewStatus.IN_REVIEW
        db.commit()
        db.refresh(req)

        try:
            pro_name = professional.full_name or "Dr. Specialist"
            NotificationService.on_review_started(db, req.patient_id, req.id, pro_name)
        except Exception as e:
            print(f"Notification error: {e}")

        return req

    @staticmethod
    def get_assessment(
        db: Session,
        review_id: str,
        professional: User
    ) -> Optional[ProfessionalReview]:
        """
        Retrieve existing professional assessment draft or completed assessment for an assigned case.
        """
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        if not req:
            raise ValueError(f"Review request '{review_id}' was not found.")

        if req.professional_id != professional.id:
            raise PermissionError("Access denied: this case is not assigned to you.")

        if req.payment_status != "PAID":
            raise PermissionError("Access denied: consultation payment has not been completed.")

        return db.query(ProfessionalReview).filter(ProfessionalReview.review_request_id == review_id).first()

    @staticmethod
    def save_assessment_draft(
        db: Session,
        review_id: str,
        professional: User,
        payload: ProfessionalAssessmentDraftRequest
    ) -> ProfessionalReview:
        """
        Save or update a draft assessment for an assigned, paid case without marking it COMPLETED.
        """
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        if not req:
            raise ValueError(f"Review request '{review_id}' was not found.")

        if req.professional_id != professional.id:
            raise PermissionError("Access denied: this case is not assigned to you.")

        if req.payment_status != "PAID":
            raise PermissionError("Access denied: consultation payment has not been completed.")

        if req.status == ReviewStatus.COMPLETED:
            raise ValueError("Cannot edit an assessment that is already COMPLETED.")

        # Transition to IN_REVIEW if currently ASSIGNED or ACCEPTED
        if req.status in [ReviewStatus.ASSIGNED, ReviewStatus.ACCEPTED, ReviewStatus.REQUESTED]:
            req.status = ReviewStatus.IN_REVIEW
            if not req.accepted_at:
                req.accepted_at = datetime.now(timezone.utc)

        observations = (payload.clinical_observations or payload.clinical_summary or payload.assessment or "").strip()
        impression = (payload.professional_impression or payload.clinical_impression or observations).strip()
        recommendations = (payload.recommendations or "").strip() or None
        notes = (payload.additional_notes or payload.professional_notes or "").strip() or None
        urgency = payload.urgency or "ROUTINE"
        follow_up = bool(payload.follow_up if payload.follow_up is not None else payload.follow_up_required)
        limitations = (payload.limitations or "").strip() or None
        msg_to_pat = (payload.message_to_patient or recommendations or "").strip() or None

        now_dt = datetime.now(timezone.utc)
        prof_review = db.query(ProfessionalReview).filter(ProfessionalReview.review_request_id == review_id).first()

        if not prof_review:
            prof_review = ProfessionalReview(
                review_request_id=review_id,
                professional_id=professional.id,
                assessment=observations or impression,
                clinical_summary=observations or impression,
                clinical_impression=impression,
                finding_validations=payload.finding_validations or {},
                professional_notes=notes,
                recommendations=recommendations,
                limitations=limitations,
                urgency=urgency,
                follow_up_required=follow_up,
                message_to_patient=msg_to_pat,
                reviewed_at=now_dt,
            )
            db.add(prof_review)
        else:
            prof_review.assessment = observations or impression
            prof_review.clinical_summary = observations or impression
            prof_review.clinical_impression = impression
            prof_review.finding_validations = payload.finding_validations or {}
            prof_review.professional_notes = notes
            prof_review.recommendations = recommendations
            prof_review.limitations = limitations
            prof_review.urgency = urgency
            prof_review.follow_up_required = follow_up
            prof_review.message_to_patient = msg_to_pat
            prof_review.updated_at = now_dt

        db.commit()
        db.refresh(prof_review)
        return prof_review

    @staticmethod
    def complete_review(
        db: Session,
        review_id: str,
        professional: User,
        review_input: ProfessionalReviewSubmitRequest
    ) -> ProfessionalReview:
        """
        Submit professional review, create immutable ProfessionalReview record, set status to COMPLETED.
        """
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        if not req:
            raise ValueError(f"Review request '{review_id}' was not found.")

        if req.professional_id != professional.id:
            raise PermissionError("Access denied: this case is not assigned to you.")

        if req.payment_status != "PAID":
            raise PermissionError("Access denied: consultation payment has not been completed.")

        # Idempotency check: if already completed, return existing review record
        if req.status == ReviewStatus.COMPLETED:
            existing_rev = db.query(ProfessionalReview).filter(ProfessionalReview.review_request_id == review_id).first()
            if existing_rev:
                return existing_rev

        observations = (review_input.clinical_observations or review_input.clinical_summary or review_input.assessment or "").strip()
        impression = (review_input.professional_impression or review_input.clinical_impression or "").strip()

        # Validation: required observations or impression
        if not observations and impression:
            observations = impression
        elif not impression and observations:
            impression = observations

        if not observations or len(observations) < 5:
            raise ValueError("Clinical observations / professional impression must be provided (minimum 5 characters).")

        now_dt = datetime.now(timezone.utc)
        recommendations = (review_input.recommendations or "").strip() or None
        notes = (review_input.additional_notes or review_input.professional_notes or "").strip() or None
        urgency = review_input.urgency or "ROUTINE"
        follow_up = bool(review_input.follow_up if review_input.follow_up is not None else review_input.follow_up_required)
        limitations = (review_input.limitations or "").strip() or None
        msg_to_pat = (review_input.message_to_patient or recommendations or "").strip() or None

        prof_review = db.query(ProfessionalReview).filter(ProfessionalReview.review_request_id == review_id).first()
        if not prof_review:
            prof_review = ProfessionalReview(
                review_request_id=review_id,
                professional_id=professional.id,
                assessment=observations,
                clinical_summary=observations,
                clinical_impression=impression,
                finding_validations=review_input.finding_validations or {},
                professional_notes=notes,
                recommendations=recommendations,
                limitations=limitations,
                urgency=urgency,
                follow_up_required=follow_up,
                message_to_patient=msg_to_pat,
                reviewed_at=now_dt,
            )
            db.add(prof_review)
        else:
            prof_review.assessment = observations
            prof_review.clinical_summary = observations
            prof_review.clinical_impression = impression
            prof_review.finding_validations = review_input.finding_validations or {}
            prof_review.professional_notes = notes
            prof_review.recommendations = recommendations
            prof_review.limitations = limitations
            prof_review.urgency = urgency
            prof_review.follow_up_required = follow_up
            prof_review.message_to_patient = msg_to_pat
            prof_review.reviewed_at = now_dt

        req.status = ReviewStatus.COMPLETED
        req.completed_at = now_dt
        db.commit()
        db.refresh(prof_review)

        # Record physician earning allocation (Milestone 13)
        try:
            from ..payments.service import PaymentService
            PaymentService.record_professional_earning(
                db=db,
                review_request_id=req.id,
                professional_id=professional.id,
            )
        except Exception as earn_err:
            print(f"Earning allocation warning: {earn_err}")

        try:
            pro_name = professional.full_name or "Dr. Specialist"
            NotificationService.on_review_completed(db, req.patient_id, req.id, pro_name)

            patient_user = db.query(User).filter(User.id == req.patient_id).first()
            if patient_user and patient_user.email:
                EmailService.notify_patient_review_completed(
                    patient_email=patient_user.email,
                    patient_name=patient_user.full_name or "Patient",
                    doctor_name=pro_name,
                    review_id=req.id,
                )
        except Exception as e:
            print(f"Notification / Email warning: {e}")

        return prof_review

    @staticmethod
    def submit_assessment(
        db: Session,
        review_id: str,
        professional: User,
        payload: ProfessionalReviewSubmitRequest
    ) -> ProfessionalReview:
        """
        Alias for completing / submitting professional assessment.
        """
        return ReviewService.complete_review(db, review_id, professional, payload)

    @staticmethod
    def respond_review(
        db: Session,
        review_id: str,
        professional: User,
        review_input: ProfessionalReviewSubmitRequest
    ) -> ProfessionalReview:
        """
        Alias for completing / submitting doctor response (POST .../respond).
        """
        return ReviewService.complete_review(db, review_id, professional, review_input)

    @staticmethod
    def request_information(
        db: Session,
        review_id: str,
        professional: User,
        questions: str
    ) -> ReviewRequest:
        """
        Professional requests additional clinical history/information from the patient.
        """
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        if not req or req.professional_id != professional.id:
            raise ValueError("Review request not found or not assigned to you.")

        if req.status not in [ReviewStatus.ACCEPTED, ReviewStatus.IN_REVIEW]:
            raise ValueError(f"Cannot request information when review status is '{req.status.value}'.")

        q_clean = questions.strip()
        if len(q_clean) < 5:
            raise ValueError("Requested information question must be at least 5 characters long.")

        req.requested_information = q_clean
        db.commit()
        db.refresh(req)

        try:
            pro_name = professional.full_name or "Dr. Specialist"
            NotificationService.on_information_requested(db, req.patient_id, req.id, pro_name)
        except Exception as e:
            print(f"Notification error: {e}")

        return req

    @staticmethod
    def provide_additional_info(
        db: Session,
        review_id: str,
        patient: User,
        info: str
    ) -> ReviewRequest:
        """
        Patient provides requested additional clinical information to the assigned doctor.
        """
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        if not req or req.patient_id != patient.id:
            raise ValueError("Review request not found or does not belong to you.")

        if req.status in [ReviewStatus.COMPLETED, ReviewStatus.CANCELLED, ReviewStatus.EXPIRED]:
            raise ValueError(f"Cannot provide additional info on a '{req.status.value}' request.")

        info_clean = info.strip()
        if len(info_clean) < 2:
            raise ValueError("Provided information must be at least 2 characters long.")

        req.patient_additional_info = info_clean
        db.commit()
        db.refresh(req)

        try:
            if req.professional_id:
                pat_name = patient.full_name or "Patient"
                NotificationService.on_information_provided(db, req.professional_id, req.id, pat_name)
        except Exception as e:
            print(f"Notification error: {e}")

        return req

    @staticmethod
    def decline_review_request(
        db: Session,
        review_id: str,
        professional: User
    ) -> ReviewRequest:
        """
        Professional declines a request.
        If assigned, releases back to REQUESTED pool and clears professional_id.
        """
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        if not req:
            raise ValueError("Review request not found.")

        if req.status == ReviewStatus.COMPLETED:
            raise ValueError("Cannot decline an already completed review.")

        if req.professional_id and req.professional_id != professional.id:
            raise ValueError("Access denied: request belongs to another professional.")

        now_dt = datetime.now(timezone.utc)

        # Release assigned request back to REQUESTED pool
        req.professional_id = None
        req.status = ReviewStatus.REQUESTED
        req.declined_at = now_dt
        req.accepted_at = None
        req.assigned_at = None
        db.commit()
        db.refresh(req)
        return req

    # --------------------------------------------------
    # Formatting Helpers
    # --------------------------------------------------

    @staticmethod
    def build_review_response(db: Session, req: ReviewRequest) -> Dict[str, Any]:
        """
        Constructs standard ReviewRequestResponse dict with professional public info.
        """
        pro_info = None
        if req.professional_id:
            pro_user = db.query(User).filter(User.id == req.professional_id).first()
            if pro_user:
                pro_prof = db.query(ProfessionalProfile).filter(ProfessionalProfile.user_id == pro_user.id).first()
                disp_name = pro_user.get_display_name() if hasattr(pro_user, "get_display_name") else (pro_user.full_name or "Doctor")
                pro_info = {
                    "id": pro_user.id,
                    "full_name": pro_user.full_name,
                    "username": pro_user.username,
                    "display_name": disp_name,
                    "email": pro_user.email,
                    "specialty": pro_prof.specialty if pro_prof else None,
                    "qualification": pro_prof.qualification if pro_prof else None,
                    "hospital_or_clinic": pro_prof.hospital_or_clinic if pro_prof else None,
                    "location_city": pro_prof.location_city if pro_prof else None,
                    "location_state": pro_prof.location_state if pro_prof else None,
                    "location_country": pro_prof.location_country if pro_prof else None,
                }

        prof_rev_dict = None
        # Only expose completed review assessment to general/patient responses; drafts remain private to the physician.
        if req.professional_review and req.status == ReviewStatus.COMPLETED:
            prof_rev_dict = req.professional_review.to_dict()

        data = req.to_dict()
        data["professional"] = pro_info
        data["professional_review"] = prof_rev_dict
        return data

    @staticmethod
    def build_review_detail_response(db: Session, req: ReviewRequest) -> Dict[str, Any]:
        """
        Constructs detailed ReviewRequestDetailResponse with full analysis report and professional review.
        """
        base_resp = ReviewService.build_review_response(db, req)
        analysis = db.query(Analysis).filter(Analysis.id == req.analysis_id).first()

        analysis_dict = analysis.to_dict() if analysis else {}
        ai_report = analysis_dict.get("report")
        if not ai_report and analysis:
            ai_report = generate_analysis_report(analysis_dict)

        return {
            "review_request": base_resp,
            "analysis_summary": {
                "analysis_id": analysis.id if analysis else req.analysis_id,
                "view": analysis.view if analysis else "Frontal",
                "image": analysis.image_path if analysis else None,
                "findings": analysis.findings_raw if analysis else {},
                "detected_findings": analysis.detected_findings if analysis else [],
                "heatmaps": analysis.heatmaps if analysis else {},
                "patient_explanations": analysis.patient_explanations if analysis else [],
            },
            "ai_report": ai_report,
            "professional": base_resp.get("professional"),
            "professional_review": base_resp.get("professional_review"),
        }

    @staticmethod
    def get_professional_case_workspace(
        db: Session,
        review_id: str,
        professional: User
    ) -> Dict[str, Any]:
        """
        Retrieve full case details for a verified professional on an assigned, PAID review request.
        Strictly verifies:
        1. Review request exists (raises ValueError if not found)
        2. Case is assigned to this specific professional (raises PermissionError if not)
        3. Case payment_status == 'PAID' (raises PermissionError if not)
        4. Returns safe patient info (no sensitive credentials/tokens)
        5. Returns analysis data with browser-ready URLs, raw AI probabilities/thresholds, heatmaps, and stored report.
        """
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        if not req:
            raise ValueError(f"Review request '{review_id}' was not found.")

        # Professional assignment check (must be assigned to this professional)
        if not req.professional_id or req.professional_id != professional.id:
            raise PermissionError("Access denied: this case is not assigned to you.")

        # Payment status check
        if req.payment_status != "PAID":
            raise PermissionError("Access denied: consultation payment has not been completed.")

        # Fetch patient info (safe subset)
        patient = db.query(User).filter(User.id == req.patient_id).first()
        pat_disp_name = patient.get_display_name() if (patient and hasattr(patient, "get_display_name")) else (patient.full_name if patient else "Patient")
        patient_info = {
            "id": patient.id if patient else req.patient_id,
            "full_name": patient.full_name if patient else "Patient",
            "username": patient.username if patient else None,
            "display_name": pat_disp_name,
        }

        # Fetch analysis and report
        analysis = db.query(Analysis).filter(Analysis.id == req.analysis_id).first()
        analysis_dict = analysis.to_dict() if analysis else {}

        def format_output_url(path_str: Optional[str]) -> Optional[str]:
            if not path_str:
                return None
            if path_str.startswith("/outputs/") or path_str.startswith("http://") or path_str.startswith("https://"):
                return path_str
            try:
                p = Path(path_str)
                parts = p.parts
                if "outputs" in parts:
                    idx = parts.index("outputs")
                    rel = "/".join(parts[idx + 1:]).replace("\\", "/")
                    return f"/outputs/{rel}"
                return f"/outputs/{p.name}"
            except Exception:
                return path_str

        # Convert heatmaps
        raw_heatmaps = analysis_dict.get("heatmaps", {})
        converted_heatmaps = {}
        for finding, path in raw_heatmaps.items():
            converted_heatmaps[finding] = format_output_url(path)

        # Convert findings
        raw_findings = analysis_dict.get("findings", {})
        converted_findings = {}
        for finding, data in raw_findings.items():
            f_data = dict(data) if isinstance(data, dict) else {"probability": data}
            if finding in converted_heatmaps:
                f_data["heatmap"] = converted_heatmaps[finding]
            elif "heatmap" in f_data:
                f_data["heatmap"] = format_output_url(f_data.get("heatmap"))
            converted_findings[finding] = f_data

        image_url = format_output_url(analysis_dict.get("image"))

        ai_report = analysis_dict.get("report")
        if not ai_report and analysis:
            ai_report = generate_analysis_report(analysis_dict)

        base_resp = ReviewService.build_review_response(db, req)

        return {
            "review_request": base_resp,
            "patient": patient_info,
            "analysis": {
                "analysis_id": analysis.id if analysis else req.analysis_id,
                "view": analysis.view if analysis else "Frontal",
                "image_url": image_url,
                "image": image_url,
                "findings": converted_findings,
                "detected_findings": analysis.detected_findings if analysis else [],
                "heatmaps": converted_heatmaps,
                "patient_explanations": analysis.patient_explanations if analysis else [],
                "created_at": analysis.created_at.isoformat() if (analysis and analysis.created_at) else None,
            },
            "ai_report": ai_report,
            "professional": base_resp.get("professional"),
            "professional_review": base_resp.get("professional_review"),
        }

    # --------------------------------------------------
    # Milestone 3D: Patient Professional Review & Report
    # --------------------------------------------------

    @staticmethod
    def get_patient_professional_review(
        db: Session,
        review_id: str,
        patient: User,
    ) -> Dict[str, Any]:
        """
        Patient-facing logic to retrieve a completed professional second opinion.
        Strictly verifies:
        1. Review request exists.
        2. Authenticated user is the owning patient (or admin).
        3. Review status is COMPLETED and professional review exists (Completion Gate).
        4. Excludes private/internal sensitive credentials and documents.
        """
        req = db.query(ReviewRequest).filter(ReviewRequest.id == review_id).first()
        if not req:
            raise ValueError(f"Review request '{review_id}' was not found.")

        if req.patient_id != patient.id and patient.role != UserRole.ADMIN:
            raise PermissionError("Access denied: you do not have permission to access this professional review.")

        if req.status != ReviewStatus.COMPLETED or not req.professional_review:
            raise ValueError("Professional review is not yet completed.")

        pro_user = db.query(User).filter(User.id == req.professional_id).first() if req.professional_id else None
        pro_prof = db.query(ProfessionalProfile).filter(ProfessionalProfile.user_id == pro_user.id).first() if pro_user else None

        pro_info = None
        if pro_user:
            pro_info = {
                "id": pro_user.id,
                "full_name": pro_user.full_name,
                "specialty": pro_prof.specialty if pro_prof else "Radiology",
                "specialization": pro_prof.specialty if pro_prof else "Radiology",
                "qualification": pro_prof.qualification if pro_prof else "Board Certified",
                "hospital_or_clinic": pro_prof.hospital_or_clinic if pro_prof else None,
                "location_city": pro_prof.location_city if pro_prof else None,
                "location_state": pro_prof.location_state if pro_prof else None,
                "location_country": pro_prof.location_country if pro_prof else None,
                "verified": True,
                "verification_status": "VERIFIED",
            }

        analysis = db.query(Analysis).filter(Analysis.id == req.analysis_id).first()
        analysis_dict = analysis.to_dict() if analysis else {}
        ai_report = analysis_dict.get("report")
        if not ai_report and analysis:
            ai_report = generate_analysis_report(analysis_dict)

        prof_rev_dict = req.professional_review.to_dict() if req.professional_review else {}

        # AI decision support section (clearly distinct from professional review)
        ai_support = {
            "analysis_id": analysis.id if analysis else req.analysis_id,
            "view": analysis.view if analysis else "Frontal",
            "findings": analysis.findings_raw if analysis else {},
            "detected_findings": analysis.detected_findings if analysis else [],
            "overall_summary": ai_report.get("overall_summary") if ai_report else "Automated DenseNet121 radiograph analysis.",
            "patient_interpretation": ai_report.get("patient_interpretation", {}) if ai_report else {},
        }

        return {
            "review_id": req.id,
            "analysis_id": req.analysis_id,
            "status": req.status.value,
            "completed_at": req.completed_at,
            "professional": pro_info,
            "professional_review": prof_rev_dict,
            "ai_decision_support": ai_support,
            "clinical_notice": (
                "This professional review is provided as part of the HC-XCDSS clinical decision-support platform. "
                "It should be considered together with comprehensive clinical evaluation by your primary healthcare provider."
            ),
        }

    @staticmethod
    def generate_professional_review_report(
        db: Session,
        review_id: str,
        patient: User,
    ) -> Dict[str, Any]:
        """
        Generates combined structured report data for downloading/printing.
        """
        patient_review = ReviewService.get_patient_professional_review(db, review_id, patient)

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return {
            "report_id": f"REP-REV-{review_id[:8].upper()}",
            "generated_at": now_str,
            "case_information": {
                "review_id": patient_review["review_id"],
                "analysis_id": patient_review["analysis_id"],
                "completed_at": patient_review["completed_at"].isoformat() if patient_review.get("completed_at") else now_str,
                "status": "COMPLETED",
            },
            "professional": patient_review["professional"],
            "professional_review": patient_review["professional_review"],
            "ai_decision_support": patient_review["ai_decision_support"],
            "clinical_disclaimer": (
                "HC-XCDSS Clinical Governance: This document contains an independent human clinical evaluation "
                "provided by a verified healthcare professional alongside automated AI decision support findings. "
                "It does not replace an in-person clinical examination or emergency medical care."
            ),
        }

    @staticmethod
    def render_professional_review_html_report(
        db: Session,
        review_id: str,
        patient: User,
    ) -> str:
        """
        Renders a clean, standalone printable HTML document for downloading.
        """
        report_data = ReviewService.generate_professional_review_report(db, review_id, patient)
        doc = report_data.get("professional") or {}
        rev = report_data.get("professional_review") or {}
        ai = report_data.get("ai_decision_support") or {}
        case = report_data.get("case_information") or {}

        doc_name = doc.get("full_name", "Verified Clinical Specialist")
        doc_spec = doc.get("specialty", "Radiology / Pulmonary Medicine")
        doc_qual = doc.get("qualification", "Board Certified")
        doc_clinic = doc.get("hospital_or_clinic", "HC-XCDSS Clinical Network")
        completed_at = case.get("completed_at", "N/A")

        obs = rev.get("clinical_observations") or rev.get("clinical_summary") or "None noted."
        imp = rev.get("professional_impression") or rev.get("clinical_impression") or "None noted."
        recs = rev.get("recommendations") or "Routine follow-up."
        urgency = rev.get("urgency", "ROUTINE")
        follow_up = "Yes" if rev.get("follow_up") or rev.get("follow_up_required") else "No"
        notes = rev.get("message_to_patient") or rev.get("additional_notes") or ""

        detected_findings = ", ".join(ai.get("detected_findings", [])) or "No acute findings detected."

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>HC-XCDSS Professional Review — Request #{case.get('review_id', '')[:8]}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      line-height: 1.5;
      margin: 0;
      padding: 40px;
      background: #f8fafc;
    }}
    .report-card {{
      max-width: 800px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 36px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid #0284c7;
      padding-bottom: 16px;
      margin-bottom: 24px;
    }}
    .brand {{
      font-size: 24px;
      font-weight: 800;
      color: #0284c7;
      letter-spacing: -0.5px;
    }}
    .brand-sub {{
      font-size: 12px;
      color: #64748b;
      font-weight: 600;
      text-transform: uppercase;
    }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 700;
      background: #ecfdf5;
      color: #059669;
      border: 1px solid #a7f3d0;
    }}
    .section-title {{
      font-size: 16px;
      font-weight: 700;
      color: #1e293b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-top: 24px;
      margin-bottom: 12px;
      padding-bottom: 6px;
      border-bottom: 1px solid #f1f5f9;
    }}
    .doctor-box {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 20px;
    }}
    .field {{
      margin-bottom: 14px;
    }}
    .field-label {{
      font-size: 11px;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: block;
      margin-bottom: 4px;
    }}
    .field-value {{
      font-size: 14px;
      color: #1e293b;
      white-space: pre-wrap;
    }}
    .ai-box {{
      background: #f0f9ff;
      border: 1px solid #bae6fd;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 20px;
    }}
    .disclaimer {{
      margin-top: 32px;
      padding-top: 16px;
      border-top: 1px solid #e2e8f0;
      font-size: 11px;
      color: #94a3b8;
      line-height: 1.4;
    }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      .report-card {{ border: none; box-shadow: none; padding: 0; }}
    }}
  </style>
</head>
<body>
  <div class="report-card">
    <div class="header">
      <div>
        <div class="brand">HC-XCDSS</div>
        <div class="brand-sub">Independent Professional Review Report</div>
      </div>
      <div>
        <span class="badge">VERIFIED SECOND OPINION</span>
      </div>
    </div>

    <!-- CASE REFERENCE -->
    <div class="field">
      <span class="field-label">Case Reference</span>
      <div class="field-value">Review ID: <strong>{case.get('review_id', '')}</strong> | Analysis ID: <strong>{case.get('analysis_id', '')}</strong> | Completed: <strong>{completed_at}</strong></div>
    </div>

    <!-- SECTION 1: PROFESSIONAL HUMAN REVIEW -->
    <div class="section-title">Verified Professional Assessment</div>
    <div class="doctor-box">
      <strong>{doc_name}</strong> &bull; {doc_spec} ({doc_qual})<br>
      <span style="color: #64748b; font-size: 13px;">{doc_clinic} &bull; Verified Specialist</span>
    </div>

    <div class="field">
      <span class="field-label">Clinical Observations & Radiological Findings</span>
      <div class="field-value">{obs}</div>
    </div>

    <div class="field">
      <span class="field-label">Professional Impression / Synthesis</span>
      <div class="field-value">{imp}</div>
    </div>

    <div class="field">
      <span class="field-label">Clinical Recommendations & Next Steps</span>
      <div class="field-value">{recs}</div>
    </div>

    <div style="display: flex; gap: 24px; margin-bottom: 14px;">
      <div>
        <span class="field-label">Urgency</span>
        <span class="field-value"><strong>{urgency}</strong></span>
      </div>
      <div>
        <span class="field-label">Formal Follow-up Recommended</span>
        <span class="field-value"><strong>{follow_up}</strong></span>
      </div>
    </div>

    {f'<div class="field"><span class="field-label">Patient Notes / Instructions</span><div class="field-value">{notes}</div></div>' if notes else ''}

    <!-- SECTION 2: AI DECISION SUPPORT -->
    <div class="section-title">AI Decision Support (DenseNet121 Inference)</div>
    <div class="ai-box">
      <div class="field">
        <span class="field-label">Detected AI Pathologies</span>
        <div class="field-value">{detected_findings}</div>
      </div>
      <div class="field">
        <span class="field-label">Automated Model Summary</span>
        <div class="field-value">{ai.get('overall_summary', '')}</div>
      </div>
    </div>

    <!-- DISCLAIMER -->
    <div class="disclaimer">
      <strong>Clinical Safety Notice:</strong> {report_data.get('clinical_disclaimer', '')}
    </div>
  </div>
</body>
</html>"""
        return html
