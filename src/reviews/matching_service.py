"""
HC-XCDSS Doctor Matching Foundation Service

Provides criteria-based matching for finding active, verified healthcare professionals
for second-opinion reviews. Extensible for ranking algorithms in future milestones.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import or_
from sqlalchemy.orm import Session
from ..db.models.user import User, UserRole
from ..db.models.professional_profile import ProfessionalProfile, ProfessionalVerificationStatus


class DoctorMatchingService:
    """
    Matching and directory engine for finding active, verified healthcare professionals.
    """

    @staticmethod
    def get_verified_directory(
        db: Session,
        city: Optional[str] = None,
        region: Optional[str] = None,
        specialty: Optional[str] = None,
        specialization: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves public discovery profile of active, verified professionals.
        PENDING, REJECTED, SUSPENDED, and deactivated users are strictly excluded at database level.
        """
        query = (
            db.query(User, ProfessionalProfile)
            .join(ProfessionalProfile, User.id == ProfessionalProfile.user_id)
            .filter(
                User.role == UserRole.PROFESSIONAL,
                User.is_active == True,
                ProfessionalProfile.verification_status == ProfessionalVerificationStatus.VERIFIED,
            )
        )

        city_param = city or region
        if city_param and city_param.strip():
            c = city_param.strip()
            query = query.filter(
                or_(
                    ProfessionalProfile.location_city.ilike(f"%{c}%"),
                    ProfessionalProfile.location_state.ilike(f"%{c}%"),
                )
            )

        spec_param = specialization or specialty
        if spec_param and spec_param.strip():
            s = spec_param.strip()
            query = query.filter(ProfessionalProfile.specialty.ilike(f"%{s}%"))

        query = query.order_by(User.full_name.asc())
        results = query.all()

        directory_list = []
        for user, profile in results:
            disp_name = user.get_display_name() if hasattr(user, "get_display_name") else (user.full_name or "Doctor")
            directory_list.append({
                "id": user.id,
                "user_id": user.id,
                "name": disp_name,
                "full_name": user.full_name,
                "username": user.username,
                "display_name": disp_name,
                "specialization": profile.specialty,
                "specialty": profile.specialty,
                "qualification": profile.qualification,
                "hospital_or_clinic": profile.hospital_or_clinic,
                "city": profile.location_city,
                "state": profile.location_state,
                "location_city": profile.location_city,
                "location_state": profile.location_state,
                "location_country": profile.location_country,
                "bio": profile.bio,
                "consultation_fee": profile.consultation_fee,
                "verified": True,
                "verification_status": (
                    profile.verification_status.value
                    if isinstance(profile.verification_status, ProfessionalVerificationStatus)
                    else str(profile.verification_status)
                ),
            })

        return directory_list

    @staticmethod
    def find_suitable_professionals(
        db: Session,
        specialty: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find active, verified healthcare professionals matching optional geographic or specialty filters.
        """
        query = (
            db.query(User, ProfessionalProfile)
            .join(ProfessionalProfile, User.id == ProfessionalProfile.user_id)
            .filter(
                User.role == UserRole.PROFESSIONAL,
                User.is_active == True,
                ProfessionalProfile.verification_status == ProfessionalVerificationStatus.VERIFIED,
            )
        )

        if specialty and specialty.strip():
            query = query.filter(ProfessionalProfile.specialty.ilike(f"%{specialty.strip()}%"))

        if city and city.strip():
            query = query.filter(ProfessionalProfile.location_city.ilike(f"%{city.strip()}%"))

        if state and state.strip():
            query = query.filter(ProfessionalProfile.location_state.ilike(f"%{state.strip()}%"))

        if country and country.strip():
            query = query.filter(ProfessionalProfile.location_country.ilike(f"%{country.strip()}%"))

        results = query.order_by(User.full_name.asc()).all()
        matched_list = []

        for user, profile in results:
            matched_list.append({
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "specialty": profile.specialty,
                "qualification": profile.qualification,
                "license_number": profile.license_number,
                "hospital_or_clinic": profile.hospital_or_clinic,
                "location_city": profile.location_city,
                "location_state": profile.location_state,
                "location_country": profile.location_country,
                "consultation_fee": profile.consultation_fee,
                "bio": profile.bio,
            })

        return matched_list

