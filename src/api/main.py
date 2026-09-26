import os
import sys
import shutil
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from fastapi import (
    FastAPI,
    Request,
    File,
    UploadFile,
    HTTPException,
    Form,
    Depends,
    status
)

from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, Response, RedirectResponse

from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

from sqlalchemy.orm import Session


# --------------------------------------------------
# Project paths & Environment
# --------------------------------------------------

PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)

env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)
else:
    from dotenv import load_dotenv
    load_dotenv()


# --------------------------------------------------
# Import inference service
# --------------------------------------------------

sys.path.append(
    str(
        PROJECT_ROOT
        / "src"
        / "inference"
    )
)

from service import XRayInferenceService
from validator import xray_validator


from pydantic import BaseModel

# --------------------------------------------------
# Import database & session
# --------------------------------------------------

from ..db.session import get_db
from ..db.models.user import User, UserRole
from ..db.migration import init_db, migrate_json_history

# Initialize database schema and migrate any pending legacy records
init_db()
migrate_json_history()


# --------------------------------------------------
# Import Authentication, Profiles & RBAC
# --------------------------------------------------

from ..auth import (
    AuthService,
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
    get_current_user,
    get_current_user_optional,
    get_current_verified_professional,
    require_role,
)
from ..db.models import (
    AIContext,
    Conversation,
    ConversationMessage,
    ProfessionalVerificationStatus,
)


# --------------------------------------------------
# Import report generator & AI Assistant
# --------------------------------------------------

from ..reporting import generate_analysis_report
from ..ai import (
    AIAssistantService,
    PatientAssistantService,
    AssistantMessageRequest,
    AssistantMessageResponse,
)

ai_assistant_service = AIAssistantService()


# --------------------------------------------------
# Import Review Workflow
# --------------------------------------------------

from ..reviews import (
    ReviewService,
    DoctorMatchingService,
    CreateReviewRequest,
    ProfessionalReviewSubmitRequest,
    ProfessionalAssessmentSubmitRequest,
    ProfessionalAssessmentDraftRequest,
    CompleteReviewRequest,
    RequestInformationPayload,
    ProvideInformationPayload,
    ReviewRequestResponse,
    ReviewRequestDetailResponse,
    ProfessionalCaseWorkspaceResponse,
    ProfessionalReviewResponse,
    PatientProfessionalReviewResponse,
    ProfessionalReviewReportResponse,
)
from ..notifications import (
    NotificationService,
    EmailService,
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
)
from ..payments import (
    PaymentService,
    SERVICE_CATALOG,
    CheckoutRequest,
    CheckoutResponse,
    PaymentStatusResponse,
    VerifySessionPayload,
    WebhookSimulateRequest,
    RefundRequest,
    RefundResponse,
    ProfessionalEarningResponse,
)


# --------------------------------------------------
# Assistant request schema
# --------------------------------------------------

class AssistantQuestionRequest(BaseModel):
    question: str


# --------------------------------------------------
# Import analysis history store
# --------------------------------------------------

from .history_store import (
    get_all_analyses,
    get_analysis,
    save_analysis,
    delete_analysis,
    delete_all_analyses
)


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="HC-XCDSS API",
    description=(
        "AI-assisted chest X-ray analysis "
        "using DenseNet121, view-specific "
        "thresholds and Grad-CAM."
    ),
    version="1.0.0"
)


# --------------------------------------------------
# CORS Configuration
# --------------------------------------------------

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def get_cors_origins() -> List[str]:
    """
    Parse CORS allowed origins from CORS_ORIGINS environment variable.
    Supports comma-separated values. Rejects wildcard '*' and falls back to dev origins.
    """
    cors_env = os.getenv("CORS_ORIGINS", "").strip()
    if cors_env:
        origins = [item.strip() for item in cors_env.split(",") if item.strip()]
        filtered = [orig for orig in origins if orig != "*"]
        if filtered:
            return filtered
    return list(DEFAULT_CORS_ORIGINS)


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Output & Analysis directories
# --------------------------------------------------

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "outputs"
)

OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

ANALYSIS_DIRECTORY = (
    OUTPUT_DIRECTORY
    / "analyses"
)

ANALYSIS_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)


# --------------------------------------------------
# Secure Medical Output File Access Endpoint
# --------------------------------------------------

@app.get(
    "/outputs/analyses/{analysis_id}/{file_name:path}",
    summary="Retrieve Medical Analysis Output File",
    description="Secure medical output file endpoint: requires authentication and ownership/access rights."
)
async def get_medical_output_file(
    analysis_id: str,
    file_name: str,
    request: Request,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    # 1. Resolve auth token from Authorization Header or 'token' query param
    auth_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        auth_token = auth_header[7:].strip()
    elif token:
        auth_token = token.strip()

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided."
        )

    # 2. Decode JWT token
    try:
        from ..auth.security import decode_access_token
        payload = decode_access_token(auth_token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Missing subject identifier")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )

    # 3. Retrieve user
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user or not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive."
        )

    # 4. Verify analysis ownership/access
    analysis_data = get_analysis(analysis_id, current_user=current_user)
    if analysis_data is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to view output files for this analysis."
        )

    # 5. Resolve file path with path traversal protection
    analysis_dir = (ANALYSIS_DIRECTORY / analysis_id).resolve()
    target_file = (analysis_dir / file_name).resolve()

    try:
        target_file.relative_to(analysis_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: invalid file path."
        )

    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requested output file '{file_name}' not found."
        )

    ext = target_file.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".html": "text/html; charset=utf-8",
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".txt": "text/plain; charset=utf-8",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(target_file),
        media_type=media_type,
        filename=target_file.name
    )



# --------------------------------------------------
# Load inference service
# --------------------------------------------------

print()

print(
    "Loading HC-XCDSS inference service..."
)


inference_service = (
    XRayInferenceService()
)


print(
    "HC-XCDSS inference service loaded."
)


# --------------------------------------------------
# Convert filesystem paths to browser URLs
# --------------------------------------------------

def convert_output_paths_to_urls(
    result
):

    # ----------------------------------------------
    # Heatmaps
    # ----------------------------------------------

    heatmaps = result.get(
        "heatmaps",
        {}
    )

    converted_heatmaps = {}

    for finding, path in heatmaps.items():
        if path is None:
            converted_heatmaps[finding] = None
            continue

        path_str = str(path)
        if (
            path_str.startswith("http://")
            or path_str.startswith("https://")
            or path_str.startswith("/outputs/")
        ):
            converted_heatmaps[finding] = path_str
            continue

        try:
            p = Path(path)
            relative_path = p.relative_to(OUTPUT_DIRECTORY)
            url = "/outputs/" + str(relative_path).replace("\\", "/")
            converted_heatmaps[finding] = url
        except ValueError:
            converted_heatmaps[finding] = None

    result["heatmaps"] = converted_heatmaps

    # ----------------------------------------------
    # Update heatmap inside findings
    # ----------------------------------------------

    findings = result.get(
        "findings",
        {}
    )

    for finding, data in findings.items():
        if finding in converted_heatmaps:
            data["heatmap"] = converted_heatmaps[finding]

    # ----------------------------------------------
    # Convert uploaded image path
    # ----------------------------------------------

    image_path = result.get("image")

    if image_path:
        image_str = str(image_path)
        if (
            image_str.startswith("http://")
            or image_str.startswith("https://")
            or image_str.startswith("/outputs/")
        ):
            result["image"] = image_str
        else:
            try:
                p = Path(image_path)
                relative_path = p.relative_to(OUTPUT_DIRECTORY)
                result["image"] = "/outputs/" + str(relative_path).replace("\\", "/")
            except ValueError:
                result["image"] = None

    return result


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/")
def root():

    return {

        "application":
            "HC-XCDSS",

        "status":
            "running",

        "message":
            "Chest X-ray analysis API is running."
    }


# --------------------------------------------------
# Health endpoint
# --------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


# ==================================================
# Authentication & User Endpoints
# ==================================================

# ==================================================
# Authentication & User Endpoints
# ==================================================

ALLOWED_DOC_EXTS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_DOC_SIZE = 10 * 1024 * 1024  # 10MB


async def validate_and_read_doc(
    file: Optional[UploadFile],
    required: bool = False,
    label: str = "Document"
) -> Tuple[Optional[bytes], Optional[str]]:
    if not file or not file.filename:
        if required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{label} is required for professional registration."
            )
        return None, None
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_DOC_EXTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} has unsupported file type '{ext}'. Allowed types: PDF, PNG, JPG, JPEG."
        )
    content = await file.read()
    if len(content) > MAX_DOC_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} exceeds maximum allowed size of 10MB."
        )
    return content, file.filename


@app.post(
    "/api/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    try:
        user = AuthService.register_user(db=db, request=payload)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post(
    "/api/auth/register-professional",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def register_professional(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    registration_number: str = Form(...),
    state_medical_council: str = Form(...),
    registration_year: Optional[str] = Form(None),
    specialty: Optional[str] = Form("General Medicine"),
    qualification: Optional[str] = Form(None),
    hospital_or_clinic: Optional[str] = Form(None),
    location_city: Optional[str] = Form(None),
    location_state: Optional[str] = Form(None),
    location_country: Optional[str] = Form("India"),
    bio: Optional[str] = Form(None),
    consultation_fee: Optional[float] = Form(0.0),
    registration_certificate: UploadFile = File(...),
    identity_document: UploadFile = File(...),
    supporting_document: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long."
        )

    reg_cert_bytes, reg_cert_filename = await validate_and_read_doc(
        registration_certificate, required=True, label="Registration Certificate"
    )
    id_doc_bytes, id_doc_filename = await validate_and_read_doc(
        identity_document, required=True, label="Identity Document / Medical ID"
    )
    supp_doc_bytes, supp_doc_filename = await validate_and_read_doc(
        supporting_document, required=False, label="Supporting Document"
    )

    try:
        user = AuthService.register_professional_with_credentials(
            db=db,
            full_name=full_name,
            email=email,
            password=password,
            registration_number=registration_number,
            state_medical_council=state_medical_council,
            registration_year=registration_year,
            specialty=specialty,
            qualification=qualification,
            hospital_or_clinic=hospital_or_clinic,
            location_city=location_city,
            location_state=location_state,
            location_country=location_country,
            bio=bio,
            consultation_fee=consultation_fee,
            reg_cert_bytes=reg_cert_bytes,
            reg_cert_filename=reg_cert_filename,
            id_doc_bytes=id_doc_bytes,
            id_doc_filename=id_doc_filename,
            supp_doc_bytes=supp_doc_bytes,
            supp_doc_filename=supp_doc_filename,
        )

        # Notify admins
        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        admin_ids = [a.id for a in admins]
        NotificationService.on_professional_registered(
            db=db,
            admin_user_ids=admin_ids,
            professional_user_id=user.id,
            professional_name=user.full_name or "Doctor",
            registration_number=registration_number,
        )
        EmailService.notify_admin_new_professional_registration(
            professional_name=user.full_name or "Doctor",
            professional_email=user.email,
            registration_number=registration_number,
            state_medical_council=state_medical_council,
            registration_year=registration_year,
            specialty=specialty,
            location_city=location_city,
            location_state=location_state,
            submission_timestamp=datetime.now(timezone.utc),
        )

        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post(
    "/api/auth/login",
    response_model=TokenResponse
)
def login(
    payload: UserLoginRequest,
    db: Session = Depends(get_db)
):
    user = AuthService.authenticate_user(db=db, request=payload)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support.",
        )

    token_data = AuthService.create_user_token(user=user)
    return token_data


@app.get(
    "/api/auth/me",
    response_model=UserResponse
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


# ==================================================
# Profile Endpoints (Role-Adaptive)
# ==================================================

@app.get(
    "/api/profile",
    response_model=UnifiedProfileResponse
)
def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the user profile and role-specific profile details.
    """
    pat_profile = None
    pro_profile = None

    if current_user.role == UserRole.PATIENT:
        pat_profile = AuthService.get_or_create_patient_profile(db, current_user)
    elif current_user.role == UserRole.PROFESSIONAL:
        pro_profile = AuthService.get_or_create_professional_profile(db, current_user)

    return {
        "user": current_user,
        "patient_profile": pat_profile,
        "professional_profile": pro_profile,
    }


@app.put(
    "/api/profile"
)
def update_user_profile(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the authenticated user's role-specific profile.
    """
    if current_user.role == UserRole.PATIENT:
        update_data = PatientProfileUpdate(**payload)
        updated_profile = AuthService.update_patient_profile(db, current_user, update_data)
        return {
            "user": current_user.to_dict(),
            "patient_profile": updated_profile.to_dict(),
        }
    elif current_user.role == UserRole.PROFESSIONAL:
        update_data = ProfessionalProfileUpdate(**payload)
        updated_profile = AuthService.update_professional_profile(db, current_user, update_data)
        return {
            "user": current_user.to_dict(),
            "professional_profile": updated_profile.to_dict(),
        }
    else:
        # Admin or other role with no extended profile
        return {
            "user": current_user.to_dict(),
            "message": "Admin user profile updated.",
        }


# ==================================================
# Admin Professional Verification Endpoints
# ==================================================

@app.get(
    "/api/admin/professionals",
    response_model=List[AdminProfessionalItemResponse],
    dependencies=[Depends(require_role([UserRole.ADMIN]))]
)
@app.get(
    "/api/admin/professionals/verification-requests",
    response_model=List[AdminProfessionalItemResponse],
    dependencies=[Depends(require_role([UserRole.ADMIN]))]
)
def list_professionals_for_admin(
    status: Optional[str] = "ALL",
    db: Session = Depends(get_db)
):
    """
    Admin: Lists all professional accounts filtered by verification status (PENDING, VERIFIED, REJECTED, ALL).
    """
    items = AuthService.list_all_professionals(db, status_filter=status)
    return items


@app.get(
    "/api/admin/professionals/{user_id}",
    response_model=AdminProfessionalItemResponse,
    dependencies=[Depends(require_role([UserRole.ADMIN]))]
)
@app.get(
    "/api/admin/professionals/{user_id}/verification-details",
    response_model=AdminProfessionalItemResponse,
    dependencies=[Depends(require_role([UserRole.ADMIN]))]
)
def get_professional_for_admin(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Admin: Get single professional details and submission credentials.
    """
    item = AuthService.get_professional_details(db, user_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Professional user with ID '{user_id}' was not found.",
        )
    return item


@app.post(
    "/api/admin/professionals/{user_id}/approve",
    response_model=ProfessionalProfileResponse
)
@app.post(
    "/api/admin/professionals/{user_id}/verify",
    response_model=ProfessionalProfileResponse
)
def approve_professional_verification(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Admin: Approve professional verification, unlock clinical review capabilities, and notify user.
    """
    try:
        profile = AuthService.approve_professional(
            db=db, user_id=user_id, admin_id=current_user.id
        )
        pro_user = db.query(User).filter(User.id == user_id).first()
        pro_name = pro_user.full_name or "Doctor" if pro_user else "Doctor"
        pro_email = pro_user.email if pro_user else ""

        NotificationService.on_professional_verified(
            db=db, professional_user_id=user_id, professional_name=pro_name
        )
        if pro_email:
            EmailService.notify_professional_verified(
                professional_email=pro_email, professional_name=pro_name
            )

        return profile
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@app.post(
    "/api/admin/professionals/{user_id}/reject",
    response_model=ProfessionalProfileResponse
)
def reject_professional_verification(
    user_id: str,
    payload: ProfessionalRejectRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Admin: Reject professional verification with a mandatory reason, notify user.
    """
    try:
        profile = AuthService.reject_professional(
            db=db, user_id=user_id, admin_id=current_user.id, rejection_reason=payload.reason
        )
        pro_user = db.query(User).filter(User.id == user_id).first()
        pro_name = pro_user.full_name or "Doctor" if pro_user else "Doctor"
        pro_email = pro_user.email if pro_user else ""

        NotificationService.on_professional_rejected(
            db=db, professional_user_id=user_id, rejection_reason=payload.reason
        )
        if pro_email:
            EmailService.notify_professional_rejected(
                professional_email=pro_email, professional_name=pro_name, rejection_reason=payload.reason
            )

        return profile
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post(
    "/api/admin/professionals/{user_id}/suspend",
    response_model=ProfessionalProfileResponse,
    dependencies=[Depends(require_role([UserRole.ADMIN]))]
)
def suspend_professional(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Admin: Suspend a professional account.
    """
    try:
        profile = AuthService.set_professional_verification_status(
            db, user_id, ProfessionalVerificationStatus.SUSPENDED
        )
        return profile
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@app.get(
    "/api/admin/professionals/{user_id}/documents/{doc_type}"
)
def get_professional_document(
    user_id: str,
    doc_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Secure document endpoint: Only ADMIN or the owning professional can access.
    """
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to view this verification document."
        )

    file_path_str = AuthService.get_document_file_path(db, user_id, doc_type)
    if not file_path_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification document '{doc_type}' was not found for this professional."
        )

    if file_path_str.startswith("http://") or file_path_str.startswith("https://"):
        return RedirectResponse(
            url=file_path_str,
            status_code=status.HTTP_302_FOUND
        )

    file_path = Path(file_path_str)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification document '{doc_type}' was not found for this professional."
        )

    ext = file_path.suffix.lower()
    media_type = "application/pdf" if ext == ".pdf" else f"image/{ext.replace('.', '')}"
    if ext == ".jpg":
        media_type = "image/jpeg"

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=media_type
    )


# ==================================================
# Doctor Directory Endpoints (Milestone 2A)
# ==================================================

@app.get(
    "/api/professionals/directory",
    response_model=DoctorDirectoryResponse,
    tags=["Doctor Directory"],
    summary="Discover Verified Healthcare Professionals",
    description=(
        "Patient-facing discovery directory for verified healthcare professionals. "
        "Supports optional filtering by city/region and specialization/specialty. "
        "PENDING, REJECTED, and SUSPENDED professionals are strictly excluded at database level. "
        "Excludes sensitive credentials, verification documents, and administrative notes."
    ),
)
@app.get(
    "/api/professional/directory",
    response_model=DoctorDirectoryResponse,
    include_in_schema=False,
)
def get_professional_directory(
    city: Optional[str] = None,
    region: Optional[str] = None,
    specialty: Optional[str] = None,
    specialization: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Returns public list of active, verified healthcare professionals matching optional filters.
    """
    professionals = DoctorMatchingService.get_verified_directory(
        db=db,
        city=city,
        region=region,
        specialty=specialty,
        specialization=specialization,
    )
    return {
        "professionals": professionals,
        "total": len(professionals),
    }


# ==================================================
# Doctor Matching Endpoint
# ==================================================

@app.get(
    "/api/professionals/search",
    description="Search verified healthcare professionals for second-opinion review."
)
def search_professionals(
    specialty: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Search active, verified healthcare professionals available for review.
    """
    return DoctorMatchingService.find_suitable_professionals(
        db=db,
        specialty=specialty,
        city=city,
        state=state,
        country=country,
    )


# ==================================================
# Patient Review Request Endpoints (Milestone 8B)
# ==================================================

@app.post(
    "/api/analyses/{analysis_id}/review-request",
    response_model=ReviewRequestResponse,
    status_code=status.HTTP_201_CREATED,
    description="Patient requests a professional second-opinion review for a specific analysis."
)
def create_analysis_review_request(
    analysis_id: str,
    payload: CreateReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        review_req = ReviewService.create_review_request(
            db=db,
            patient=current_user,
            analysis_id=analysis_id,
            patient_message=payload.patient_message,
            preferred_professional_id=payload.preferred_professional_id,
        )
        return ReviewService.build_review_response(db, review_req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post(
    "/api/reviews",
    response_model=ReviewRequestResponse,
    status_code=status.HTTP_201_CREATED,
    description="Backward-compatible review request creation endpoint."
)
def create_review(
    payload: CreateReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not payload.analysis_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="analysis_id is required in request body."
        )
    try:
        review_req = ReviewService.create_review_request(
            db=db,
            patient=current_user,
            analysis_id=payload.analysis_id,
            patient_message=payload.patient_message,
            preferred_professional_id=payload.preferred_professional_id,
        )
        return ReviewService.build_review_response(db, review_req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get(
    "/api/review-requests/my",
    response_model=List[ReviewRequestResponse],
    description="Retrieve all review requests created by the authenticated patient."
)
@app.get(
    "/api/reviews/my",
    response_model=List[ReviewRequestResponse],
    description="Retrieve all review requests created by the authenticated patient (alias)."
)
def get_my_review_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    requests = ReviewService.get_patient_review_requests(db=db, patient=current_user)
    return [ReviewService.build_review_response(db, r) for r in requests]


@app.get(
    "/api/analyses/{analysis_id}/review",
    response_model=ReviewRequestDetailResponse,
    description="Get detailed professional review and AI report for a specific analysis."
)
def get_analysis_review(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    detail = ReviewService.get_analysis_review(db=db, analysis_id=analysis_id, current_user=current_user)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No review found for analysis '{analysis_id}' or access denied."
        )
    return detail


@app.get(
    "/api/review-requests/{review_id}",
    response_model=ReviewRequestDetailResponse,
    description="Get detailed review request information by review ID."
)
@app.get(
    "/api/reviews/{review_id}",
    response_model=ReviewRequestDetailResponse,
    description="Get detailed review request information by review ID (alias)."
)
def get_review_detail(
    review_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    req = ReviewService.get_review_request_by_id(db=db, review_id=review_id, current_user=current_user)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review request '{review_id}' was not found or access is denied.",
        )
    return ReviewService.build_review_detail_response(db, req)


@app.post(
    "/api/review-requests/{review_id}/cancel",
    response_model=ReviewRequestResponse,
    description="Patient cancels an active review request before acceptance."
)
@app.post(
    "/api/reviews/{review_id}/cancel",
    response_model=ReviewRequestResponse,
    description="Patient cancels an active review request before acceptance (alias)."
)
def cancel_review(
    review_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        cancelled_req = ReviewService.cancel_review_request(
            db=db,
            review_id=review_id,
            patient=current_user
        )
        return ReviewService.build_review_response(db, cancelled_req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================================================
# Patient Professional Review & Report Endpoints (Milestone 3D)
# ==================================================

@app.get(
    "/api/patient/review-requests/{review_id}/professional-review",
    response_model=PatientProfessionalReviewResponse,
    tags=["Patient Reviews"],
    summary="Get Completed Professional Review for Patient",
    description="Allows owning patient to view the completed independent physician review and AI decision support summary."
)
@app.get(
    "/api/reviews/{review_id}/professional-review",
    response_model=PatientProfessionalReviewResponse,
    include_in_schema=False,
)
def get_patient_professional_review(
    review_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        return ReviewService.get_patient_professional_review(
            db=db,
            review_id=review_id,
            patient=current_user
        )
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except ValueError as ve:
        err_msg = str(ve)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in err_msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=err_msg
        )


@app.get(
    "/api/patient/review-requests/{review_id}/report",
    response_model=ProfessionalReviewReportResponse,
    tags=["Patient Reviews"],
    summary="Get Structured Professional Review Report Data",
    description="Returns combined structured report data for completed review."
)
@app.get(
    "/api/reviews/{review_id}/report",
    response_model=ProfessionalReviewReportResponse,
    include_in_schema=False,
)
def get_professional_review_report(
    review_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        return ReviewService.generate_professional_review_report(
            db=db,
            review_id=review_id,
            patient=current_user
        )
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except ValueError as ve:
        err_msg = str(ve)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in err_msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=err_msg
        )


@app.get(
    "/api/patient/review-requests/{review_id}/report/download",
    tags=["Patient Reviews"],
    summary="Download Professional Review Report Document",
    description="Serves downloadable printable HTML medical report for completed review."
)
@app.get(
    "/api/reviews/{review_id}/report/download",
    include_in_schema=False,
)
def download_professional_review_report(
    review_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        html_content = ReviewService.render_professional_review_html_report(
            db=db,
            review_id=review_id,
            patient=current_user
        )
        filename = f"HC-XCDSS-Professional-Review-{review_id[:8]}.html"
        return Response(
            content=html_content,
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe)
        )
    except ValueError as ve:
        err_msg = str(ve)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in err_msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=err_msg
        )



# ==================================================
# Professional Review Workflow Endpoints (Verified Only)
# ==================================================

@app.get(
    "/api/professional/review-requests",
    response_model=List[ReviewRequestResponse],
    description="List review requests available to or assigned to the verified professional."
)
@app.get(
    "/api/professional/reviews",
    response_model=List[ReviewRequestResponse],
    description="List review requests available to or assigned to the verified professional (alias)."
)
def list_professional_reviews(
    filter: Optional[str] = "all",
    current_user: User = Depends(get_current_verified_professional),
    db: Session = Depends(get_db)
):
    requests = ReviewService.get_filtered_for_professional(
        db=db,
        professional=current_user,
        filter_type=filter or "all"
    )
    return [ReviewService.build_review_response(db, r) for r in requests]


@app.get(
    "/api/professional/review-requests/{review_id}/case",
    response_model=ProfessionalCaseWorkspaceResponse,
    description="Retrieve complete clinical and AI case information for a verified professional on an assigned, PAID review request."
)
@app.get(
    "/api/professional/reviews/{review_id}/case",
    response_model=ProfessionalCaseWorkspaceResponse,
    description="Retrieve complete clinical and AI case information for a verified professional on an assigned, PAID review request (alias)."
)
def get_professional_case_workspace(
    review_id: str,
    current_user: User = Depends(get_current_verified_professional),
    db: Session = Depends(get_db)
):
    try:
        case_data = ReviewService.get_professional_case_workspace(
            db=db,
            review_id=review_id,
            professional=current_user
        )
        return case_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load case workspace: {str(e)}"
        )


@app.post(
    "/api/professional/review-requests/{review_id}/accept",
    response_model=ReviewRequestResponse,
    description="Verified professional accepts a review request."
)
@app.post(
    "/api/professional/reviews/{review_id}/accept",
    response_model=ReviewRequestResponse,
    description="Verified professional accepts a review request (alias)."
)
def accept_review(
    review_id: str,
    current_user: User = Depends(get_current_verified_professional),
    db: Session = Depends(get_db)
):
    try:
        req = ReviewService.accept_review_request(
            db=db,
            review_id=review_id,
            professional=current_user
        )
        return ReviewService.build_review_response(db, req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@app.post(
    "/api/professional/review-requests/{review_id}/start",
    response_model=ReviewRequestResponse,
    description="Assigned professional marks a review request as in review."
)
@app.post(
    "/api/professional/reviews/{review_id}/start",
    response_model=ReviewRequestResponse,
    description="Assigned professional marks a review request as in review (alias)."
)
def start_review(
    review_id: str,
    current_user: User = Depends(get_current_verified_professional),
    db: Session = Depends(get_db)
):
    try:
        req = ReviewService.start_review(
            db=db,
            review_id=review_id,
            professional=current_user
        )
        return ReviewService.build_review_response(db, req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get(
    "/api/professional/review-requests/{review_id}/assessment",
    response_model=Optional[ProfessionalReviewResponse],
    description="Retrieve existing professional assessment draft or submitted review."
)
def get_assessment(
    review_id: str,
    current_user: User = Depends(get_current_verified_professional),
    db: Session = Depends(get_db)
):
    try:
        prof_review = ReviewService.get_assessment(
            db=db,
            review_id=review_id,
            professional=current_user
        )
        return prof_review
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load assessment: {str(e)}"
        )


@app.post(
    "/api/professional/review-requests/{review_id}/assessment/draft",
    response_model=ProfessionalReviewResponse,
    description="Save draft clinical observations and impressions without completing the review."
)
@app.put(
    "/api/professional/review-requests/{review_id}/assessment",
    response_model=ProfessionalReviewResponse,
    description="Save draft clinical assessment (alias)."
)
def save_assessment_draft(
    review_id: str,
    payload: ProfessionalAssessmentDraftRequest,
    current_user: User = Depends(get_current_verified_professional),
    db: Session = Depends(get_db)
):
    try:
        prof_review = ReviewService.save_assessment_draft(
            db=db,
            review_id=review_id,
            professional=current_user,
            payload=payload
        )
        return prof_review
    except ValueError as e:
        is_completed = "already completed" in str(e).lower()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT if is_completed else (
                status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST
            ),
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save assessment draft: {str(e)}"
        )


@app.post(
    "/api/professional/review-requests/{review_id}/assessment/submit",
    response_model=ProfessionalReviewResponse,
    description="Submit final professional assessment and mark review request as COMPLETED."
)
@app.post(
    "/api/professional/review-requests/{review_id}/assessment",
    response_model=ProfessionalReviewResponse,
    description="Submit final professional assessment (alias)."
)
@app.post(
    "/api/professional/review-requests/{review_id}/review",
    response_model=ProfessionalReviewResponse,
    description="Assigned professional completes review by submitting clinical assessment."
)
@app.post(
    "/api/professional/review-requests/{review_id}/respond",
    response_model=ProfessionalReviewResponse,
    description="Assigned professional responds to review request (alias)."
)
@app.post(
    "/api/professional/reviews/{review_id}/complete",
    response_model=ProfessionalReviewResponse,
    description="Assigned professional completes review (alias)."
)
def complete_review(
    review_id: str,
    payload: ProfessionalReviewSubmitRequest,
    current_user: User = Depends(get_current_verified_professional),
    db: Session = Depends(get_db)
):
    try:
        prof_review = ReviewService.complete_review(
            db=db,
            review_id=review_id,
            professional=current_user,
            review_input=payload
        )
        return prof_review
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in str(e).lower() else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit assessment: {str(e)}"
        )


@app.post(
    "/api/professional/review-requests/{review_id}/request-information",
    response_model=ReviewRequestResponse,
    description="Assigned professional requests additional clinical information from patient."
)
def request_information(
    review_id: str,
    payload: RequestInformationPayload,
    current_user: User = Depends(get_current_verified_professional),
    db: Session = Depends(get_db)
):
    try:
        req = ReviewService.request_information(
            db=db,
            review_id=review_id,
            professional=current_user,
            questions=payload.requested_information
        )
        return ReviewService.build_review_response(db, req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post(
    "/api/review-requests/{review_id}/provide-information",
    response_model=ReviewRequestResponse,
    description="Patient provides requested clinical information to assigned professional."
)
def provide_information(
    review_id: str,
    payload: ProvideInformationPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        req = ReviewService.provide_additional_info(
            db=db,
            review_id=review_id,
            patient=current_user,
            info=payload.patient_additional_info
        )
        return ReviewService.build_review_response(db, req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post(
    "/api/professional/review-requests/{review_id}/decline",
    response_model=ReviewRequestResponse,
    description="Assigned professional declines a review request, returning it to pool."
)
@app.post(
    "/api/professional/reviews/{review_id}/decline",
    response_model=ReviewRequestResponse,
    description="Assigned professional declines a review request (alias)."
)
def decline_review(
    review_id: str,
    current_user: User = Depends(get_current_verified_professional),
    db: Session = Depends(get_db)
):
    try:
        req = ReviewService.decline_review_request(
            db=db,
            review_id=review_id,
            professional=current_user
        )
        return ReviewService.build_review_response(db, req)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================================================
# Notifications & Activity Center Endpoints (Milestone 12)
# ==================================================

@app.get(
    "/api/notifications",
    response_model=NotificationListResponse,
    description="Retrieve paginated notifications for the authenticated user."
)
def get_user_notifications(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notifs, total, unread = NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )
    return {
        "total": total,
        "unread_count": unread,
        "notifications": notifs,
    }


@app.get(
    "/api/notifications/unread-count",
    response_model=UnreadCountResponse,
    description="Get unread notification count for the authenticated user."
)
def get_unread_notification_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = NotificationService.get_unread_count(db=db, user_id=current_user.id)
    return {"count": count}


@app.post(
    "/api/notifications/{notification_id}/read",
    response_model=NotificationResponse,
    description="Mark a specific notification as read."
)
def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notif = NotificationService.mark_as_read(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied."
        )
    return notif


@app.post(
    "/api/notifications/read-all",
    description="Mark all notifications as read for the authenticated user."
)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = NotificationService.mark_all_as_read(db=db, user_id=current_user.id)
    return {"success": True, "marked_read_count": count}


@app.delete(
    "/api/notifications/{notification_id}",
    description="Delete/dismiss a notification belonging to the authenticated user."
)
def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = NotificationService.delete_notification(
        db=db,
        notification_id=notification_id,
        user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied."
        )
# ==================================================
# Payments & Checkout Engine Endpoints (Milestone 13)
# ==================================================

@app.get(
    "/api/payments/catalog",
    description="Get available consultation and review service catalog."
)
def get_payment_catalog():
    return {
        "services": [service.dict() for service in SERVICE_CATALOG.values()]
    }


@app.post(
    "/api/payments/checkout",
    response_model=CheckoutResponse,
    description="Create a consultation checkout session for a patient review request."
)
def create_payment_checkout(
    payload: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        payment = PaymentService.create_checkout(
            db=db,
            patient=current_user,
            review_request_id=payload.review_request_id,
            service_id=payload.service_id,
            idempotency_key=payload.idempotency_key,
        )
        return payment.to_dict()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get(
    "/api/payments/{payment_id}/status",
    response_model=PaymentStatusResponse,
    description="Get current payment status."
)
def get_payment_status(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from ..db.models.payment import Payment
    pay_obj = db.query(Payment).filter(Payment.id == payment_id).first()
    if not pay_obj:
        raise HTTPException(status_code=404, detail="Payment record not found.")

    if pay_obj.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied: You do not own this payment record.")

    return pay_obj.to_dict()


@app.post(
    "/api/payments/verify-session",
    description="Verify and synchronize payment status directly with payment provider after checkout return."
)
def verify_payment_session(
    payload: VerifySessionPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session_id = payload.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")

    from ..db.models.payment import Payment, PaymentStatus
    from ..db.models.review_request import ReviewRequest
    from ..payments.providers import get_payment_provider, StripePaymentProvider
    from ..reviews.service import ReviewService

    # Find payment record by provider_payment_id or ID
    payment = db.query(Payment).filter(
        (Payment.provider_payment_id == session_id) |
        (Payment.id == session_id)
    ).first()

    provider = get_payment_provider()

    # If payment was not found directly by provider_payment_id and provider is Stripe, retrieve session from Stripe
    if not payment and isinstance(provider, StripePaymentProvider) and provider.is_configured:
        import stripe
        stripe.api_key = provider.api_key
        try:
            stripe_session = stripe.checkout.Session.retrieve(session_id)
            pay_id = stripe_session.client_reference_id or stripe_session.metadata.get("payment_id")
            if pay_id:
                payment = db.query(Payment).filter(Payment.id == pay_id).first()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to retrieve Stripe session: {str(e)}")

    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found for this session.")

    if payment.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access denied: You do not own this payment record.")

    # If not already marked PAID, check with provider
    if payment.status != PaymentStatus.PAID:
        if isinstance(provider, StripePaymentProvider) and provider.is_configured:
            import stripe
            stripe.api_key = provider.api_key
            try:
                stripe_session = stripe.checkout.Session.retrieve(
                    session_id if session_id.startswith("cs_") else payment.provider_payment_id
                )
                if stripe_session.payment_status == "paid":
                    payment = PaymentService.process_payment_success(
                        db=db,
                        payment_id=payment.id,
                        provider_payment_id=stripe_session.id
                    )
                elif stripe_session.status == "expired":
                    payment = PaymentService.process_payment_failure(
                        db=db,
                        payment_id=payment.id,
                        reason="Stripe checkout session expired."
                    )
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Stripe session verification error: {str(e)}")
        elif getattr(provider, "provider_name", "mock") == "mock":
            payment = PaymentService.process_payment_success(
                db=db,
                payment_id=payment.id,
                provider_payment_id=payment.provider_payment_id or session_id
            )

    # Fetch corresponding review request
    review = db.query(ReviewRequest).filter(ReviewRequest.id == payment.review_request_id).first()
    review_dict = ReviewService.build_review_response(db, review) if review else None

    return {
        "success": payment.status == PaymentStatus.PAID,
        "payment": payment.to_dict(),
        "review_request": review_dict,
        "status": payment.status.value,
        "message": "Payment verified successfully." if payment.status == PaymentStatus.PAID else f"Payment status is {payment.status.value}."
    }


@app.post(
    "/api/payments/webhook/{provider}",
    description="Payment provider webhook receiver / simulator."
)
async def payment_webhook(
    provider: str,
    request: Request,
    db: Session = Depends(get_db)
):
    provider_clean = provider.strip().lower()

    if provider_clean == "stripe":
        payload_bytes = await request.body()
        sig_header = request.headers.get("stripe-signature")
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()

        event = None
        if webhook_secret:
            if not sig_header:
                raise HTTPException(status_code=400, detail="Missing stripe-signature header.")
            import stripe
            stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
            try:
                event = stripe.Webhook.construct_event(
                    payload=payload_bytes,
                    sig_header=sig_header,
                    secret=webhook_secret,
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid Stripe webhook signature: {str(e)}")
        else:
            try:
                import json
                event = json.loads(payload_bytes.decode("utf-8"))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid Stripe event payload")

        if hasattr(event, "to_dict"):
            event_dict = event.to_dict()
        elif isinstance(event, dict):
            event_dict = event
        else:
            event_dict = dict(event)

        event_type = event_dict.get("type", "")
        data_object = event_dict.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            payment_id = data_object.get("client_reference_id") or data_object.get("metadata", {}).get("payment_id")
            provider_payment_id = data_object.get("id")
            if payment_id:
                try:
                    PaymentService.process_payment_success(
                        db=db,
                        payment_id=payment_id,
                        provider_payment_id=provider_payment_id,
                    )
                except ValueError:
                    pass
        elif event_type in ["checkout.session.async_payment_failed", "payment_intent.payment_failed"]:
            payment_id = data_object.get("client_reference_id") or data_object.get("metadata", {}).get("payment_id")
            if payment_id:
                try:
                    PaymentService.process_payment_failure(
                        db=db,
                        payment_id=payment_id,
                        reason="Stripe payment failed.",
                    )
                except ValueError:
                    pass

        return {"received": True, "event_type": event_type}

    # Mock / Simulator Provider
    try:
        body_json = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    payment_id = body_json.get("payment_id")
    if not payment_id:
        raise HTTPException(status_code=400, detail="Field 'payment_id' is required.")

    action = body_json.get("action", "success")
    try:
        if action == "fail":
            payment = PaymentService.process_payment_failure(
                db=db,
                payment_id=payment_id,
                reason="Payment declined by provider simulation.",
            )
        else:
            payment = PaymentService.process_payment_success(
                db=db,
                payment_id=payment_id,
                provider_payment_id=f"prov_{provider_clean}_{payment_id[:8]}",
            )
        return {
            "success": True,
            "payment_id": payment.id,
            "status": payment.status.value,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/api/payments/{payment_id}/refund",
    response_model=RefundResponse,
    description="Issue refund for a consultation payment (Admin only)."
)
def refund_payment(
    payment_id: str,
    payload: RefundRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    try:
        refunded_pay = PaymentService.process_refund(
            db=db,
            payment_id=payment_id,
            actor=current_user,
            reason=payload.reason,
        )
        return {
            "success": True,
            "payment_id": refunded_pay.id,
            "status": refunded_pay.status,
            "refund_amount_minor": refunded_pay.amount_minor,
            "message": "Refund processed successfully.",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/api/professional/earnings",
    response_model=List[ProfessionalEarningResponse],
    description="List allocated earnings for authenticated verified professional."
)
def get_professional_earnings(
    current_user: User = Depends(get_current_verified_professional),
    db: Session = Depends(get_db)
):
    from ..db.models.payment import ProfessionalEarning
    earnings = (
        db.query(ProfessionalEarning)
        .filter(ProfessionalEarning.professional_id == current_user.id)
        .order_by(ProfessionalEarning.created_at.desc())
        .all()
    )
    return [e.to_dict() for e in earnings]


# ==================================================
# Analysis History Endpoints (RBAC & User-Scoped)
# ==================================================

@app.get("/api/analyses")
def list_analyses(
    current_user: User = Depends(get_current_user)
):

    analyses = (
        get_all_analyses(
            current_user=current_user
        )
    )


    return {

        "count":
            len(analyses),

        "analyses":
            analyses
    }


# --------------------------------------------------
# Unified Patient Dashboard Overview
# --------------------------------------------------

@app.get(
    "/api/patient/dashboard",
    description="Retrieve unified dashboard overview for authenticated patient."
)
def get_patient_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.PATIENT and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Patient dashboard is only accessible to patient accounts."
        )

    # 1. Fetch patient's analyses
    analyses = get_all_analyses(current_user=current_user)

    # 2. Fetch patient's reviews
    raw_reviews = ReviewService.get_patient_review_requests(db, current_user)
    reviews_formatted = [ReviewService.build_review_response(db, r) for r in raw_reviews]

    # Map reviews by analysis_id for quick status lookup
    review_by_analysis = {}
    for r in reviews_formatted:
        aid = r.get("analysis_id")
        if aid and aid not in review_by_analysis:
            review_by_analysis[aid] = r

    # Attach review status to recent analyses
    recent_analyses = []
    for a in analyses[:6]:
        analysis_item = dict(a)
        linked_rev = review_by_analysis.get(a.get("analysis_id"))
        if linked_rev:
            analysis_item["review_status"] = linked_rev.get("status")
            analysis_item["review_id"] = linked_rev.get("id")
            analysis_item["review_doctor_name"] = linked_rev.get("professional", {}).get("full_name") if linked_rev.get("professional") else None
        recent_analyses.append(analysis_item)

    # Filter active and completed reviews
    active_statuses = ["REQUESTED", "ASSIGNED", "ACCEPTED", "IN_REVIEW"]
    active_reviews = [r for r in reviews_formatted if r.get("status") in active_statuses]
    completed_reviews = [r for r in reviews_formatted if r.get("status") == "COMPLETED"]

    # 3. Notification unread count
    unread_notifs = NotificationService.get_unread_count(db, current_user.id)

    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name or "Patient",
            "role": current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        },
        "stats": {
            "total_analyses": len(analyses),
            "active_reviews_count": len(active_reviews),
            "completed_reviews_count": len(completed_reviews),
            "unread_notifications_count": unread_notifs,
        },
        "recent_analyses": recent_analyses,
        "active_reviews": active_reviews[:5],
        "completed_reviews": completed_reviews[:5],
    }


# --------------------------------------------------
# Get specific analysis
# --------------------------------------------------

@app.get(
    "/api/analyses/{analysis_id}"
)
def get_analysis_by_id(
    analysis_id: str,
    current_user: User = Depends(get_current_user)
):

    analysis = (
        get_analysis(
            analysis_id,
            current_user=current_user
        )
    )


    if analysis is None:

        raise HTTPException(

            status_code=404,

            detail=(
                f"Analysis "
                f"'{analysis_id}' "
                f"was not found or you do not have permission to access it."
            )
        )


    return analysis


# --------------------------------------------------
# Context-Aware AI Assistant Endpoints
# --------------------------------------------------

@app.post(
    "/api/assistant/{analysis_id}",
    response_model=AssistantMessageResponse,
    description="Context-Aware AI Assistant for querying a specific X-ray analysis and structured report."
)
def ask_ai_assistant(
    analysis_id: str,
    payload: AssistantMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis_dict = get_analysis(
        analysis_id,
        current_user=current_user
    )

    if analysis_dict is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Analysis '{analysis_id}' was not found or you do not have permission to access it."
            )
        )

    # 1. STRICT BACKEND RBAC ROLE DERIVATION
    # Never trust frontend-supplied role for authenticated users.
    if current_user.role == UserRole.PROFESSIONAL:
        effective_role = "professional"
    elif current_user.role == UserRole.PATIENT:
        effective_role = "patient"
    elif current_user.role == UserRole.ADMIN:
        # Admins are not clinical users by default; allow role requested if specified, else patient
        effective_role = "professional" if (payload.role or "").lower() == "professional" else "patient"
    else:
        effective_role = "patient"

    # 2. Retrieve or build persisted AIContext
    ai_context_record = db.query(AIContext).filter(AIContext.analysis_id == analysis_id).first()
    if ai_context_record and ai_context_record.context_data:
        context_data = ai_context_record.context_data
    else:
        # Build and persist context
        report = analysis_dict.get("report") or generate_analysis_report(analysis_dict)
        from ..ai.context_builder import build_patient_ai_context
        context_data = build_patient_ai_context(report)
        new_ai_ctx = AIContext(analysis_id=analysis_id, context_data=context_data)
        db.add(new_ai_ctx)
        db.commit()

    # 3. Retrieve or create Conversation thread
    conversation = None
    if payload.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == payload.conversation_id,
            Conversation.analysis_id == analysis_id
        ).first()

    if not conversation:
        # Check if user already has an active conversation for this analysis
        conversation = db.query(Conversation).filter(
            Conversation.analysis_id == analysis_id,
            Conversation.user_id == current_user.id,
            Conversation.role == effective_role
        ).first()

    if not conversation:
        conversation = Conversation(
            analysis_id=analysis_id,
            user_id=current_user.id,
            role=effective_role,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 4. Load Conversation History
    history_turns: List[Dict[str, str]] = []
    if conversation.messages:
        for msg in conversation.messages:
            history_turns.append({
                "role": "user" if msg.sender in ["user", "patient", "professional"] else "model",
                "content": msg.content,
            })
    elif payload.conversation_history:
        history_turns = [
            {"role": "user" if m.role in ["user", "patient", "professional"] else "model", "content": m.content}
            for m in payload.conversation_history
        ]

    # 5. Process Question through AI Assistant Service
    response_dict = ai_assistant_service.answer_question(
        report_or_analysis=analysis_dict,
        question=payload.message,
        role=effective_role,
        conversation_history=history_turns,
        context=context_data,
    )

    # 6. Persist User Message & Model Response in Conversation Thread
    try:
        user_msg = ConversationMessage(
            conversation_id=conversation.id,
            sender="user",
            content=payload.message.strip(),
        )
        db.add(user_msg)

        ai_msg = ConversationMessage(
            conversation_id=conversation.id,
            sender="model",
            content=response_dict["answer"],
            provider=response_dict.get("provider"),
            model=response_dict.get("model"),
            safety_status=response_dict.get("safety_status", "ok"),
        )
        db.add(ai_msg)
        db.commit()
    except Exception as e:
        db.rollback()
        # Non-fatal persistence logging to avoid failing the user request
        print(f"Conversation persistence warning: {e}")

    response_dict["conversation_id"] = conversation.id
    response_dict["role"] = effective_role
    return response_dict


@app.post(
    "/api/assistant/{analysis_id}/chat",
    response_model=AssistantMessageResponse,
    description="Context-Aware AI Assistant chat turn (alias for /api/assistant/{analysis_id})."
)
def chat_ai_assistant_alias(
    analysis_id: str,
    payload: AssistantMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ask_ai_assistant(
        analysis_id=analysis_id,
        payload=payload,
        current_user=current_user,
        db=db,
    )


@app.get(
    "/api/assistant/{analysis_id}/conversation",
    description="Retrieve persisted conversation messages for a specific analysis and authenticated user."
)
def get_analysis_conversation(
    analysis_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    analysis_dict = get_analysis(analysis_id, current_user=current_user)
    if analysis_dict is None:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis '{analysis_id}' was not found or access denied."
        )

    user_id = current_user.id if current_user else None
    query = db.query(Conversation).filter(Conversation.analysis_id == analysis_id)
    if user_id:
        query = query.filter(Conversation.user_id == user_id)
    else:
        query = query.filter(Conversation.user_id.is_(None))

    conv = query.first()
    if not conv:
        return {"analysis_id": analysis_id, "conversation_id": None, "messages": []}

    return conv.to_dict()


# Backward-compatible route for /api/analyses/{analysis_id}/assistant
@app.post(
    "/api/analyses/{analysis_id}/assistant"
)
def ask_patient_assistant_legacy(
    analysis_id: str,
    payload: AssistantQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msg_req = AssistantMessageRequest(
        message=payload.question,
        role="patient",
    )
    return ask_ai_assistant(
        analysis_id=analysis_id,
        payload=msg_req,
        current_user=current_user,
        db=db,
    )


# --------------------------------------------------
# Delete specific analysis
# --------------------------------------------------

@app.delete(
    "/api/analyses/{analysis_id}"
)
def delete_analysis_by_id(
    analysis_id: str,
    current_user: User = Depends(get_current_user)
):

    # ----------------------------------------------
    # Check whether analysis exists and accessible
    # ----------------------------------------------

    analysis = get_analysis(
        analysis_id,
        current_user=current_user
    )


    if analysis is None:

        raise HTTPException(

            status_code=404,

            detail=(
                f"Analysis "
                f"'{analysis_id}' "
                f"was not found or you do not have permission to delete it."
            )
        )


    # ----------------------------------------------
    # Delete analysis directory
    # ----------------------------------------------

    # ----------------------------------------------
    # Delete analysis directory & artifacts
    # ----------------------------------------------

    from ..storage import get_storage_provider
    storage = get_storage_provider()
    storage.delete_analysis_artifacts(analysis_id)

    # ----------------------------------------------
    # Delete from history
    # ----------------------------------------------

    deleted = delete_analysis(
        analysis_id,
        current_user=current_user
    )


    if not deleted:

        raise HTTPException(

            status_code=500,

            detail=(
                "Analysis files were deleted "
                "but history could not be updated."
            )
        )


    # ----------------------------------------------
    # Response
    # ----------------------------------------------

    return {

        "success": True,

        "message": (
            f"Analysis '{analysis_id}' "
            "deleted successfully."
        ),

        "analysis_id":
            analysis_id
    }


# --------------------------------------------------
# Delete all analyses (Admin only)
# --------------------------------------------------

@app.delete(
    "/api/analyses",
    dependencies=[Depends(require_role([UserRole.ADMIN]))]
)
def delete_all_analysis_history():

    # ----------------------------------------------
    # Delete analysis directories & artifacts
    # ----------------------------------------------

    from ..storage import get_storage_provider
    storage = get_storage_provider()
    storage.delete_all_analysis_artifacts()

    # ----------------------------------------------
    # Clear history
    # ----------------------------------------------

    delete_all_analyses()


    # ----------------------------------------------
    # Response
    # ----------------------------------------------

    return {

        "success": True,

        "message": (
            "All analysis history "
            "deleted successfully."
        )
    }


# --------------------------------------------------
# X-ray analysis endpoint
# --------------------------------------------------

@app.post("/api/analyze")
async def analyze_xray(

    file: UploadFile = File(...),

    view: str = Form("Frontal"),

    current_user: User = Depends(get_current_user)

):

    # ----------------------------------------------
    # Validate view
    # ----------------------------------------------

    view = (
        view
        .strip()
        .capitalize()
    )


    if view not in {
        "Frontal",
        "Lateral"
    }:

        raise HTTPException(

            status_code=400,

            detail=(
                "View must be either "
                "'Frontal' or 'Lateral'."
            )
        )


    # ----------------------------------------------
    # Validate file extension
    # ----------------------------------------------

    allowed_extensions = {
        ".jpg",
        ".jpeg",
        ".png"
    }


    file_extension = (
        Path(
            file.filename or ""
        ).suffix.lower()
    )


    if file_extension not in (
        allowed_extensions
    ):

        raise HTTPException(

            status_code=400,

            detail=(
                "Only JPG, JPEG and PNG "
                "X-ray images are supported."
            )
        )


    # ----------------------------------------------
    # Validate file size limit (15MB)
    # ----------------------------------------------

    MAX_XRAY_UPLOAD_SIZE = 15 * 1024 * 1024  # 15MB

    if file.size and file.size > MAX_XRAY_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file exceeds maximum allowed size of 15MB."
        )

    # ----------------------------------------------
    # Read upload contents for validation
    # ----------------------------------------------

    file_bytes = await file.read(MAX_XRAY_UPLOAD_SIZE + 1)

    if len(file_bytes) > MAX_XRAY_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file exceeds maximum allowed size of 15MB."
        )


    # ----------------------------------------------
    # Pre-Inference Chest X-Ray Validation Gate
    # ----------------------------------------------

    is_valid, rejection_reason, validation_details = xray_validator.validate(
        file_bytes,
        view=view
    )

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_XRAY",
                "message": (
                    "The uploaded image does not appear to be a valid chest X-ray. "
                    "Please upload a clear frontal or lateral chest radiograph."
                ),
                "reason": rejection_reason,
            }
        )

    from ..storage import get_storage_provider, CloudinaryStorageProvider
    storage = get_storage_provider()
    is_cloud = isinstance(storage, CloudinaryStorageProvider)

    # ----------------------------------------------
    # Create unique analysis ID
    # ----------------------------------------------

    analysis_id = (
        uuid.uuid4().hex[:12]
    )

    analysis_directory = (
        ANALYSIS_DIRECTORY
        / analysis_id
    )

    analysis_directory.mkdir(
        parents=True,
        exist_ok=False
    )

    # ----------------------------------------------
    # Safe uploaded filename
    # ----------------------------------------------

    safe_filename = Path(
        file.filename
        or "uploaded_xray.jpg"
    ).name

    uploaded_image_path = (
        analysis_directory
        / safe_filename
    )

    try:

        # ------------------------------------------
        # Save uploaded image locally for ML inference
        # ------------------------------------------

        with open(
            uploaded_image_path,
            "wb"
        ) as buffer:

            buffer.write(file_bytes)

        print()
        print("=" * 75)
        print("NEW X-RAY ANALYSIS")
        print("=" * 75)
        print("Analysis ID:", analysis_id)
        print("View:", view)
        print("Image:", uploaded_image_path)

        # ------------------------------------------
        # Run ML + XAI pipeline
        # ------------------------------------------

        result = (
            inference_service.analyze(
                uploaded_image_path,
                view=view,
                output_directory=analysis_directory
            )
        )

        result["analysis_id"] = (
            analysis_id
        )

        # ------------------------------------------
        # Upload or convert artifact paths
        # ------------------------------------------

        if is_cloud:
            # Upload original X-ray to cloud storage
            cloud_image_url = storage.save_analysis_artifact(
                analysis_id,
                uploaded_image_path,
                safe_filename
            )
            result["image"] = cloud_image_url

            # Upload generated Grad-CAM heatmaps
            uploaded_heatmaps = {}
            for finding, h_path in result.get("heatmaps", {}).items():
                if h_path and Path(h_path).exists():
                    h_file = Path(h_path)
                    cloud_h_url = storage.save_analysis_artifact(
                        analysis_id,
                        h_path,
                        h_file.name
                    )
                    uploaded_heatmaps[finding] = cloud_h_url
                else:
                    uploaded_heatmaps[finding] = None
            result["heatmaps"] = uploaded_heatmaps

            # Update findings heatmap URLs
            findings = result.get("findings", {})
            for finding, data in findings.items():
                if finding in uploaded_heatmaps:
                    data["heatmap"] = uploaded_heatmaps[finding]
        else:
            # Local filesystem mode: convert paths to /outputs/
            result = (
                convert_output_paths_to_urls(
                    result
                )
            )

        # ------------------------------------------
        # Generate structured report
        # ------------------------------------------

        result["report"] = (
            generate_analysis_report(
                result
            )
        )

        # ------------------------------------------
        # Save analysis history
        # ------------------------------------------

        save_analysis(
            result,
            user_id=current_user.id if current_user else None
        )

        # ------------------------------------------
        # Return JSON
        # ------------------------------------------

        return JSONResponse(
            content=result
        )

    except Exception as error:

        # Cleanup analysis directory on failure
        if analysis_directory.exists():
            try:
                shutil.rmtree(analysis_directory)
            except Exception:
                pass

        print()
        print("ERROR during X-ray analysis:", error)

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:

        # If in cloud storage mode, purge local ephemeral scratch directory
        if is_cloud and analysis_directory.exists():
            try:
                shutil.rmtree(analysis_directory)
            except Exception:
                pass

        await file.close()