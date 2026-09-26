"""
HC-XCDSS Authentication & RBAC FastAPI Dependencies
"""

from typing import Optional, List
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models.user import User, UserRole
from ..db.models.professional_profile import ProfessionalProfile, ProfessionalVerificationStatus
from .security import decode_access_token

# Bearer token extractor (auto_error=False allows optional authentication)
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Extracts the user if a valid bearer token is provided; returns None if unauthenticated.
    Raises HTTPException for invalid/expired tokens.
    """
    if not credentials or not credentials.credentials:
        return None

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing user identifier.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: token is invalid or malformed.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User belonging to this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account has been deactivated.",
        )

    return user


def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """
    Requires a valid authenticated user.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(allowed_roles: List[UserRole]):
    """
    Dependency factory to enforce role-based access control.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: role '{current_user.role.value}' is not permitted to perform this action.",
            )
        return current_user

    return role_checker


# Specific Role Helpers
require_patient = require_role([UserRole.PATIENT, UserRole.ADMIN])
require_professional = require_role([UserRole.PROFESSIONAL, UserRole.ADMIN])
require_admin = require_role([UserRole.ADMIN])


def get_current_verified_professional(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Ensures the caller is an active PROFESSIONAL with VERIFIED verification_status.
    """
    if current_user.role != UserRole.PROFESSIONAL and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted: user is not a healthcare professional.",
        )

    if current_user.role == UserRole.ADMIN:
        return current_user

    profile = db.query(ProfessionalProfile).filter(ProfessionalProfile.user_id == current_user.id).first()
    if not profile or profile.verification_status != ProfessionalVerificationStatus.VERIFIED:
        status_str = profile.verification_status.value if profile else "PENDING"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access restricted: professional profile is not verified (current status: {status_str}).",
        )

    return current_user
