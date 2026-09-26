"""
HC-XCDSS Authentication & Profile Service Layer
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from ..db.models.user import User, UserRole
from ..db.models.patient_profile import PatientProfile
from ..db.models.professional_profile import ProfessionalProfile, ProfessionalVerificationStatus
from .security import get_password_hash, verify_password, create_access_token, JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from .schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    PatientProfileUpdate,
    ProfessionalProfileUpdate,
)

import re

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS_STORAGE_DIR = PROJECT_ROOT / "outputs" / "verification_documents"
DOCUMENTS_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class AuthService:
    """
    Handles user registration, profile initialization, credential verification, and token issuance.
    """

    @staticmethod
    def generate_unique_username(db: Session, base_candidate: str) -> str:
        """
        Generates a unique, alphanumeric sanitized username from a candidate string.
        """
        cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '', base_candidate).lower().strip('._-')
        base = cleaned[:30] if len(cleaned) >= 3 else "user"
        candidate = base
        counter = 1
        while db.query(User).filter(User.username == candidate).first():
            candidate = f"{base[:25]}{counter}"
            counter += 1
        return candidate

    @staticmethod
    def register_user(db: Session, request: UserRegisterRequest) -> User:
        """
        Register a new user with safety checks on roles and unique username.
        Automatically provisions the corresponding PatientProfile or ProfessionalProfile.
        """
        normalized_email = request.email.strip().lower()

        # Disallow public registration as ADMIN
        if request.role == UserRole.ADMIN:
            raise ValueError("ADMIN accounts cannot be registered through public registration.")

        # Check for existing email
        existing_user = db.query(User).filter(User.email == normalized_email).first()
        if existing_user:
            raise ValueError("An account with this email already exists.")

        # Validate or generate username
        if request.username and request.username.strip():
            clean_username = request.username.strip().lower()
            if not re.match(r'^[a-zA-Z0-9_.-]{3,50}$', clean_username):
                raise ValueError("Username must be 3-50 characters containing only letters, numbers, '.', '_', or '-'.")
            existing_un = db.query(User).filter(User.username == clean_username).first()
            if existing_un:
                raise ValueError(f"Username '{clean_username}' is already taken.")
            final_username = clean_username
        else:
            base_cand = request.full_name or normalized_email.split('@')[0]
            final_username = AuthService.generate_unique_username(db, base_cand)

        assigned_role = request.role or UserRole.PATIENT
        now_dt = datetime.now(timezone.utc)

        user = User(
            email=normalized_email,
            username=final_username,
            hashed_password=get_password_hash(request.password),
            full_name=request.full_name.strip() if request.full_name else None,
            role=assigned_role,
            is_active=True,
        )

        db.add(user)
        db.flush()

        # Provision profile according to role
        if assigned_role == UserRole.PATIENT:
            patient_profile = PatientProfile(user_id=user.id)
            db.add(patient_profile)
        elif assigned_role == UserRole.PROFESSIONAL:
            professional_profile = ProfessionalProfile(
                user_id=user.id,
                verification_status=ProfessionalVerificationStatus.PENDING,
                verification_submitted_at=now_dt,
            )
            db.add(professional_profile)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def register_professional_with_credentials(
        db: Session,
        full_name: str,
        email: str,
        password: str,
        registration_number: str,
        state_medical_council: str,
        registration_year: Optional[str] = None,
        specialty: Optional[str] = None,
        qualification: Optional[str] = None,
        hospital_or_clinic: Optional[str] = None,
        location_city: Optional[str] = None,
        location_state: Optional[str] = None,
        location_country: Optional[str] = None,
        bio: Optional[str] = None,
        consultation_fee: Optional[float] = None,
        reg_cert_bytes: Optional[bytes] = None,
        reg_cert_filename: Optional[str] = None,
        id_doc_bytes: Optional[bytes] = None,
        id_doc_filename: Optional[str] = None,
        supp_doc_bytes: Optional[bytes] = None,
        supp_doc_filename: Optional[str] = None,
    ) -> User:
        """
        Registers a new Healthcare Professional with mandatory verification credentials and documents.
        """
        normalized_email = email.strip().lower()

        existing_user = db.query(User).filter(User.email == normalized_email).first()
        if existing_user:
            raise ValueError("An account with this email already exists.")

        if not registration_number or not registration_number.strip():
            raise ValueError("Medical Council Registration Number is required.")

        if not state_medical_council or not state_medical_council.strip():
            raise ValueError("State Medical Council / Licensing Authority is required.")

        now_dt = datetime.now(timezone.utc)
        username_candidate = full_name or normalized_email.split('@')[0]
        final_username = AuthService.generate_unique_username(db, username_candidate)

        user = User(
            email=normalized_email,
            username=final_username,
            hashed_password=get_password_hash(password),
            full_name=full_name.strip() if full_name else None,
            role=UserRole.PROFESSIONAL,
            is_active=True,
        )
        db.add(user)
        db.flush()

        # Save verification documents via storage provider (local or cloud)
        from ..storage import get_storage_provider
        storage = get_storage_provider()

        reg_cert_path = None
        if reg_cert_bytes and reg_cert_filename:
            reg_cert_path = storage.save_verification_document(
                user.id, "reg_cert", reg_cert_bytes, reg_cert_filename
            )

        id_doc_path = None
        if id_doc_bytes and id_doc_filename:
            id_doc_path = storage.save_verification_document(
                user.id, "id_doc", id_doc_bytes, id_doc_filename
            )

        supp_doc_path = None
        if supp_doc_bytes and supp_doc_filename:
            supp_doc_path = storage.save_verification_document(
                user.id, "supp_doc", supp_doc_bytes, supp_doc_filename
            )

        profile = ProfessionalProfile(
            user_id=user.id,
            registration_number=registration_number.strip(),
            license_number=registration_number.strip(),
            state_medical_council=state_medical_council.strip(),
            license_country_or_state=state_medical_council.strip(),
            registration_year=registration_year.strip() if registration_year else None,
            specialty=specialty.strip() if specialty else "General Medicine",
            qualification=qualification.strip() if qualification else None,
            hospital_or_clinic=hospital_or_clinic.strip() if hospital_or_clinic else None,
            location_city=location_city.strip() if location_city else None,
            location_state=location_state.strip() if location_state else None,
            location_country=location_country.strip() if location_country else "India",
            bio=bio.strip() if bio else None,
            consultation_fee=consultation_fee if consultation_fee is not None else 0.0,
            verification_status=ProfessionalVerificationStatus.PENDING,
            verification_submitted_at=now_dt,
            registration_certificate_path=reg_cert_path,
            registration_certificate_filename=reg_cert_filename,
            identity_document_path=id_doc_path,
            identity_document_filename=id_doc_filename,
            supporting_document_path=supp_doc_path,
            supporting_document_filename=supp_doc_filename,
        )
        db.add(profile)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, request: UserLoginRequest) -> Optional[User]:
        """
        Authenticate user by email and password.
        """
        normalized_email = request.email.strip().lower()
        user = db.query(User).filter(User.email == normalized_email).first()
        if not user:
            return None

        if not verify_password(request.password, user.hashed_password):
            return None

        return user

    @staticmethod
    def create_user_token(user: User) -> Dict[str, Any]:
        """
        Generate JWT token payload for an authenticated user.
        """
        token_data = {
            "sub": user.id,
            "email": user.email,
            "role": user.role.value if isinstance(user.role, UserRole) else str(user.role),
        }
        access_token = create_access_token(data=token_data)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in_minutes": JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
            "user": user,
        }

    # --------------------------------------------------
    # Profile Management
    # --------------------------------------------------

    @staticmethod
    def get_or_create_patient_profile(db: Session, user: User) -> PatientProfile:
        """
        Retrieves the PatientProfile for the user or creates one if missing.
        """
        profile = db.query(PatientProfile).filter(PatientProfile.user_id == user.id).first()
        if not profile:
            profile = PatientProfile(user_id=user.id)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return profile

    @staticmethod
    def update_patient_profile(db: Session, user: User, update_data: PatientProfileUpdate) -> PatientProfile:
        """
        Updates fields of the PatientProfile.
        """
        profile = AuthService.get_or_create_patient_profile(db, user)

        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(profile, key, value)

        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_or_create_professional_profile(db: Session, user: User) -> ProfessionalProfile:
        """
        Retrieves the ProfessionalProfile for the user or creates one with PENDING status.
        """
        profile = db.query(ProfessionalProfile).filter(ProfessionalProfile.user_id == user.id).first()
        if not profile:
            profile = ProfessionalProfile(
                user_id=user.id,
                verification_status=ProfessionalVerificationStatus.PENDING,
                verification_submitted_at=datetime.now(timezone.utc),
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return profile

    @staticmethod
    def update_professional_profile(db: Session, user: User, update_data: ProfessionalProfileUpdate) -> ProfessionalProfile:
        """
        Updates fields of the ProfessionalProfile (does NOT allow self-verification).
        """
        profile = AuthService.get_or_create_professional_profile(db, user)

        for key, value in update_data.model_dump(exclude_unset=True).items():
            # Disallow updating verification_status from public update endpoint
            if key != "verification_status":
                setattr(profile, key, value)

        db.commit()
        db.refresh(profile)
        return profile

    # --------------------------------------------------
    # Admin Verification Management
    # --------------------------------------------------

    @staticmethod
    def list_all_professionals(
        db: Session,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lists professional accounts along with profile and verification status, optionally filtered.
        """
        query = db.query(User).filter(User.role == UserRole.PROFESSIONAL)
        professionals = query.order_by(User.created_at.desc()).all()
        results = []

        for user in professionals:
            profile = db.query(ProfessionalProfile).filter(ProfessionalProfile.user_id == user.id).first()
            if status_filter and status_filter.upper() != "ALL":
                prof_status = profile.verification_status.value if profile and profile.verification_status else "PENDING"
                if prof_status != status_filter.upper():
                    continue

            results.append({
                "user": user,
                "profile": profile,
            })
        return results

    @staticmethod
    def get_professional_details(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves details of a professional by user_id for administrative inspection.
        """
        user = db.query(User).filter(User.id == user_id, User.role == UserRole.PROFESSIONAL).first()
        if not user:
            return None
        profile = db.query(ProfessionalProfile).filter(ProfessionalProfile.user_id == user.id).first()
        return {
            "user": user,
            "profile": profile,
        }

    @staticmethod
    def approve_professional(
        db: Session,
        user_id: str,
        admin_id: str,
    ) -> ProfessionalProfile:
        """
        Admin action: Approves a professional and unlocks clinical review capabilities.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.role != UserRole.PROFESSIONAL:
            raise ValueError(f"Professional user with ID '{user_id}' was not found.")

        profile = AuthService.get_or_create_professional_profile(db, user)
        profile.verification_status = ProfessionalVerificationStatus.VERIFIED
        profile.verified_at = datetime.now(timezone.utc)
        profile.verified_by = admin_id
        profile.rejection_reason = None

        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def reject_professional(
        db: Session,
        user_id: str,
        admin_id: str,
        rejection_reason: str,
    ) -> ProfessionalProfile:
        """
        Admin action: Rejects a professional registration with a clear mandatory reason.
        """
        if not rejection_reason or not rejection_reason.strip():
            raise ValueError("A clear rejection reason must be provided.")

        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.role != UserRole.PROFESSIONAL:
            raise ValueError(f"Professional user with ID '{user_id}' was not found.")

        profile = AuthService.get_or_create_professional_profile(db, user)
        profile.verification_status = ProfessionalVerificationStatus.REJECTED
        profile.verified_at = None
        profile.verified_by = admin_id
        profile.rejection_reason = rejection_reason.strip()

        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def set_professional_verification_status(
        db: Session,
        user_id: str,
        new_status: ProfessionalVerificationStatus
    ) -> ProfessionalProfile:
        """
        Updates the verification status of a professional account (Admin only).
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.role != UserRole.PROFESSIONAL:
            raise ValueError(f"Professional user with ID '{user_id}' was not found.")

        profile = AuthService.get_or_create_professional_profile(db, user)
        profile.verification_status = new_status
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_document_file_path(
        db: Session,
        user_id: str,
        doc_type: str,
    ) -> Optional[str]:
        """
        Returns the absolute local file path for a requested verification document.
        doc_type can be: 'registration_certificate', 'identity_document', 'supporting_document'
        """
        profile = db.query(ProfessionalProfile).filter(ProfessionalProfile.user_id == user_id).first()
        if not profile:
            return None

        if doc_type in ("registration_certificate", "registration_cert", "reg_cert"):
            return profile.registration_certificate_path
        elif doc_type in ("identity_document", "id_doc", "identity"):
            return profile.identity_document_path
        elif doc_type in ("supporting_document", "supp_doc", "supporting"):
            return profile.supporting_document_path

        return None

