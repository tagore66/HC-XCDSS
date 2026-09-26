"""
HC-XCDSS Authentication, User & Profile Pydantic Schemas
"""

from datetime import datetime, date
from typing import Optional, Union, Any, Dict
from pydantic import BaseModel, EmailStr, Field
from ..db.models.user import UserRole
from ..db.models.professional_profile import ProfessionalVerificationStatus


# --------------------------------------------------
# Auth Requests / Responses
# --------------------------------------------------

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password with minimum 6 characters")
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = Field(UserRole.PATIENT, description="Requested role: PATIENT or PROFESSIONAL. ADMIN is disallowed.")


class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: Optional[str] = Field(None, max_length=255)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    display_name: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --------------------------------------------------
# Patient Profile Schemas
# --------------------------------------------------

class PatientProfileUpdate(BaseModel):
    phone: Optional[str] = Field(None, max_length=32)
    location_city: Optional[str] = Field(None, max_length=100)
    location_state: Optional[str] = Field(None, max_length=100)
    location_country: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[date] = None


class PatientProfileResponse(BaseModel):
    id: str
    user_id: str
    phone: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_country: Optional[str] = None
    date_of_birth: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --------------------------------------------------
# Professional Profile Schemas
# --------------------------------------------------

class ProfessionalProfileUpdate(BaseModel):
    specialty: Optional[str] = Field(None, max_length=100)
    qualification: Optional[str] = Field(None, max_length=255)
    license_number: Optional[str] = Field(None, max_length=100)
    license_country_or_state: Optional[str] = Field(None, max_length=100)
    hospital_or_clinic: Optional[str] = Field(None, max_length=255)
    location_city: Optional[str] = Field(None, max_length=100)
    location_state: Optional[str] = Field(None, max_length=100)
    location_country: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = None
    consultation_fee: Optional[float] = Field(None, ge=0.0)


class ProfessionalProfileResponse(BaseModel):
    id: str
    user_id: str
    specialty: Optional[str] = None
    qualification: Optional[str] = None
    license_number: Optional[str] = None
    license_country_or_state: Optional[str] = None
    registration_number: Optional[str] = None
    state_medical_council: Optional[str] = None
    registration_year: Optional[str] = None
    has_registration_certificate: bool = False
    registration_certificate_filename: Optional[str] = None
    has_identity_document: bool = False
    identity_document_filename: Optional[str] = None
    has_supporting_document: bool = False
    supporting_document_filename: Optional[str] = None
    hospital_or_clinic: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_country: Optional[str] = None
    bio: Optional[str] = None
    consultation_fee: Optional[float] = None
    verification_status: ProfessionalVerificationStatus
    verification_submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdminProfessionalItemResponse(BaseModel):
    user: UserResponse
    profile: Optional[ProfessionalProfileResponse] = None


class ProfessionalRejectRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000, description="Detailed reason for administrative rejection")


class UnifiedProfileResponse(BaseModel):
    user: UserResponse
    patient_profile: Optional[PatientProfileResponse] = None
    professional_profile: Optional[ProfessionalProfileResponse] = None


# --------------------------------------------------
# Doctor Directory Discovery Schemas (Milestone 2A)
# --------------------------------------------------

class DoctorDirectoryItem(BaseModel):
    id: str = Field(..., description="Unique professional identifier (user ID)")
    user_id: str = Field(..., description="Unique user ID of the professional")
    name: str = Field(..., description="Doctor's full name")
    full_name: Optional[str] = Field(None, description="Doctor's full name")
    username: Optional[str] = Field(None, description="Doctor's unique username")
    display_name: Optional[str] = Field(None, description="Doctor's clinical display name")
    specialization: Optional[str] = Field(None, description="Clinical specialization / medical department")
    specialty: Optional[str] = Field(None, description="Clinical specialty (alias)")
    qualification: Optional[str] = Field(None, description="Medical degrees and qualifications")
    hospital_or_clinic: Optional[str] = Field(None, description="Primary clinic or hospital affiliation")
    city: Optional[str] = Field(None, description="Practice city location")
    state: Optional[str] = Field(None, description="Practice state or region")
    location_city: Optional[str] = Field(None, description="Practice city location (alias)")
    location_state: Optional[str] = Field(None, description="Practice state location (alias)")
    location_country: Optional[str] = Field(None, description="Practice country location")
    bio: Optional[str] = Field(None, description="Professional biography and clinical background")
    consultation_fee: Optional[float] = Field(None, description="Consultation fee for specialist review")
    verified: bool = Field(True, description="Verification badge status")
    verification_status: str = Field("VERIFIED", description="Official verification status")

    class Config:
        from_attributes = True


class DoctorDirectoryResponse(BaseModel):
    professionals: list[DoctorDirectoryItem] = Field(default_factory=list, description="List of verified healthcare professionals")
    total: int = Field(..., description="Total number of matching verified professionals")


TokenResponse.model_rebuild()


