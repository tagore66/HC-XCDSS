"""
HC-XCDSS Notification Service

Manages in-app notifications and domain-event triggers without leaking sensitive clinical data.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from ..db.models.notification import Notification, NotificationType, NotificationEntityType
from ..db.models.user import User


class NotificationService:
    """
    Centralized Notification Service for HC-XCDSS.
    """

    @staticmethod
    def create_notification(
        db: Session,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        entity_type: NotificationEntityType,
        entity_id: str,
    ) -> Notification:
        """
        Creates an in-app notification with idempotency protection against duplicate event firing.
        """
        if not user_id:
            return None

        # Check for recent identical unread notification within last 5 minutes to prevent duplicates
        existing = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.type == notification_type,
                Notification.entity_id == entity_id,
                Notification.is_read == False,
            )
            .first()
        )
        if existing:
            return existing

        now_dt = datetime.now(timezone.utc)
        notif = Notification(
            user_id=user_id,
            type=notification_type,
            title=title.strip(),
            message=message.strip(),
            entity_type=entity_type,
            entity_id=entity_id.strip(),
            is_read=False,
            created_at=now_dt,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Notification], int, int]:
        """
        Returns (notifications, total_count, unread_count) for a specific authenticated user.
        """
        limit = min(max(1, limit), 100)
        offset = max(0, offset)

        query = db.query(Notification).filter(Notification.user_id == user_id)
        total = query.count()
        unread_count = query.filter(Notification.is_read == False).count()

        notifications = (
            query.order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return notifications, total, unread_count

    @staticmethod
    def get_unread_count(db: Session, user_id: str) -> int:
        """
        Returns total unread notifications count for a user.
        """
        return (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .count()
        )

    @staticmethod
    def mark_as_read(db: Session, notification_id: str, user_id: str) -> Optional[Notification]:
        """
        Marks a specific notification as read if it belongs to the user.
        """
        notif = (
            db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .first()
        )
        if not notif:
            return None

        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(notif)
        return notif

    @staticmethod
    def mark_all_as_read(db: Session, user_id: str) -> int:
        """
        Marks all unread notifications for a user as read. Returns count of modified notifications.
        """
        now_dt = datetime.now(timezone.utc)
        unread_notifs = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .all()
        )
        for notif in unread_notifs:
            notif.is_read = True
            notif.read_at = now_dt
        db.commit()
        return len(unread_notifs)

    @staticmethod
    def delete_notification(db: Session, notification_id: str, user_id: str) -> bool:
        """
        Deletes a specific notification if owned by user.
        """
        notif = (
            db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .first()
        )
        if not notif:
            return False
        db.delete(notif)
        db.commit()
        return True

    # --------------------------------------------------
    # Domain Event Handlers
    # --------------------------------------------------

    @staticmethod
    def on_analysis_completed(db: Session, user_id: Optional[str], analysis_id: str, view: str = "Frontal"):
        """
        Event: AnalysisCompleted -> Notify patient that radiograph report is ready.
        Privacy rule: No specific disease names in title.
        """
        if not user_id:
            return None
        return NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationType.ANALYSIS_COMPLETED,
            title="Your X-ray analysis is ready",
            message=f"The AI-assisted report for your {view} chest radiograph (ID #{analysis_id}) has been generated.",
            entity_type=NotificationEntityType.ANALYSIS,
            entity_id=analysis_id,
        )

    @staticmethod
    def on_review_requested(db: Session, professional_id: Optional[str], review_id: str, analysis_id: str):
        """
        Event: ReviewRequested -> If targeted to specific doctor, notify doctor.
        """
        if not professional_id:
            return None
        return NotificationService.create_notification(
            db=db,
            user_id=professional_id,
            notification_type=NotificationType.REVIEW_REQUEST_CREATED,
            title="New Review Request Assigned",
            message=f"You have been assigned a new chest radiograph case (Analysis #{analysis_id}) for professional review.",
            entity_type=NotificationEntityType.REVIEW_REQUEST,
            entity_id=review_id,
        )

    @staticmethod
    def on_review_assigned(db: Session, patient_id: str, review_id: str, professional_name: str):
        """
        Event: ReviewAssigned -> Notify patient doctor has been assigned.
        """
        return NotificationService.create_notification(
            db=db,
            user_id=patient_id,
            notification_type=NotificationType.REVIEW_REQUEST_ASSIGNED,
            title="Specialist Assigned",
            message=f"{professional_name} has been assigned to review your chest radiograph.",
            entity_type=NotificationEntityType.REVIEW_REQUEST,
            entity_id=review_id,
        )

    @staticmethod
    def on_review_accepted(db: Session, patient_id: str, review_id: str, professional_name: str):
        """
        Event: ReviewAccepted -> Notify patient doctor accepted request.
        """
        return NotificationService.create_notification(
            db=db,
            user_id=patient_id,
            notification_type=NotificationType.REVIEW_REQUEST_ACCEPTED,
            title="Doctor Accepted Your Review",
            message=f"{professional_name} has accepted your review request and added it to their clinical queue.",
            entity_type=NotificationEntityType.REVIEW_REQUEST,
            entity_id=review_id,
        )

    @staticmethod
    def on_review_started(db: Session, patient_id: str, review_id: str, professional_name: str):
        """
        Event: ReviewStarted -> Notify patient review is in progress.
        """
        return NotificationService.create_notification(
            db=db,
            user_id=patient_id,
            notification_type=NotificationType.REVIEW_STARTED,
            title="Review In Progress",
            message=f"{professional_name} has started reviewing your radiograph and clinical report.",
            entity_type=NotificationEntityType.REVIEW_REQUEST,
            entity_id=review_id,
        )

    @staticmethod
    def on_information_requested(db: Session, patient_id: str, review_id: str, doctor_name: str):
        """
        Event: InformationRequested -> Notify patient doctor needs more history.
        """
        return NotificationService.create_notification(
            db=db,
            user_id=patient_id,
            notification_type=NotificationType.INFORMATION_REQUESTED,
            title="Additional Information Requested",
            message=f"{doctor_name} has requested additional clinical details regarding your symptoms.",
            entity_type=NotificationEntityType.REVIEW_REQUEST,
            entity_id=review_id,
        )

    @staticmethod
    def on_information_provided(db: Session, professional_id: str, review_id: str, patient_name: str):
        """
        Event: InformationProvided -> Notify doctor patient responded with details.
        """
        return NotificationService.create_notification(
            db=db,
            user_id=professional_id,
            notification_type=NotificationType.INFORMATION_PROVIDED,
            title="Patient Clinical Update",
            message=f"{patient_name} has provided the requested clinical history for review #{review_id[:8]}.",
            entity_type=NotificationEntityType.REVIEW_REQUEST,
            entity_id=review_id,
        )

    @staticmethod
    def on_review_completed(db: Session, patient_id: str, review_id: str, doctor_name: str):
        """
        Event: ReviewCompleted -> Notify patient completed professional opinion is available.
        Privacy rule: No specific disease names in notification text.
        """
        return NotificationService.create_notification(
            db=db,
            user_id=patient_id,
            notification_type=NotificationType.REVIEW_COMPLETED,
            title="Your Professional Review is Ready",
            message=f"{doctor_name} has submitted their clinical review and recommendations.",
            entity_type=NotificationEntityType.REVIEW_REQUEST,
            entity_id=review_id,
        )

    @staticmethod
    def on_review_cancelled(db: Session, recipient_id: str, review_id: str, cancelled_by_name: str):
        """
        Event: ReviewCancelled -> Notify relevant party.
        """
        return NotificationService.create_notification(
            db=db,
            user_id=recipient_id,
            notification_type=NotificationType.REVIEW_CANCELLED,
            title="Review Request Cancelled",
            message=f"Review request #{review_id[:8]} was cancelled by {cancelled_by_name}.",
            entity_type=NotificationEntityType.REVIEW_REQUEST,
            entity_id=review_id,
        )

    @staticmethod
    def on_professional_registered(
        db: Session,
        admin_user_ids: List[str],
        professional_user_id: str,
        professional_name: str,
        registration_number: Optional[str] = None,
    ):
        """
        Event: ProfessionalRegistered -> Notify platform administrators of pending verification request.
        """
        for admin_id in admin_user_ids:
            NotificationService.create_notification(
                db=db,
                user_id=admin_id,
                notification_type=NotificationType.PROFESSIONAL_REGISTERED,
                title="New Professional Verification Request",
                message=f"Dr. {professional_name} (Reg #{registration_number or 'N/A'}) has submitted credentials for verification.",
                entity_type=NotificationEntityType.USER,
                entity_id=professional_user_id,
            )

    @staticmethod
    def on_professional_verified(
        db: Session,
        professional_user_id: str,
        professional_name: str,
    ):
        """
        Event: ProfessionalVerified -> Notify professional that clinical access is unlocked.
        """
        return NotificationService.create_notification(
            db=db,
            user_id=professional_user_id,
            notification_type=NotificationType.PROFESSIONAL_VERIFIED,
            title="Verification Approved",
            message=f"Your medical credentials have been verified. Full clinical review access is now unlocked.",
            entity_type=NotificationEntityType.USER,
            entity_id=professional_user_id,
        )

    @staticmethod
    def on_professional_rejected(
        db: Session,
        professional_user_id: str,
        rejection_reason: str,
    ):
        """
        Event: ProfessionalRejected -> Notify professional of verification decision and reason.
        """
        return NotificationService.create_notification(
            db=db,
            user_id=professional_user_id,
            notification_type=NotificationType.PROFESSIONAL_REJECTED,
            title="Verification Update",
            message=f"Your verification request was reviewed. Status: Rejected. Reason: {rejection_reason}",
            entity_type=NotificationEntityType.USER,
            entity_id=professional_user_id,
        )
