"""
HC-XCDSS Authentication Package
"""

from .security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
)
from .schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    PatientProfileUpdate,
    PatientProfileResponse,
    ProfessionalProfileUpdate,
    ProfessionalProfileResponse,
    AdminProfessionalItemResponse,
    ProfessionalRejectRequest,
    UnifiedProfileResponse,
    DoctorDirectoryItem,
    DoctorDirectoryResponse,
)
from .service import AuthService
from .dependencies import (
    get_current_user,
    get_current_user_optional,
    get_current_verified_professional,
    require_role,
    require_patient,
    require_professional,
    require_admin,
)

__all__ = [
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_access_token",
    "JWT_SECRET_KEY",
    "JWT_ALGORITHM",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "UserResponse",
    "PatientProfileUpdate",
    "PatientProfileResponse",
    "ProfessionalProfileUpdate",
    "ProfessionalProfileResponse",
    "AdminProfessionalItemResponse",
    "ProfessionalRejectRequest",
    "UnifiedProfileResponse",
    "DoctorDirectoryItem",
    "DoctorDirectoryResponse",
    "AuthService",
    "get_current_user",
    "get_current_user_optional",
    "get_current_verified_professional",
    "require_role",
    "require_patient",
    "require_professional",
    "require_admin",
]
