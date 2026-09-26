"""
HC-XCDSS Review Workflow Pydantic Schemas
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, field_validator
from ..db.models.review_request import ReviewStatus


# --------------------------------------------------
# Request Schemas
# --------------------------------------------------

class CreateReviewRequest(BaseModel):
    analysis_id: Optional[str] = Field(None, description="12-character ID of the analysis to review (in body if not in path)")
    patient_message: Optional[str] = Field(None, max_length=2000, description="Optional note or context from patient")
    preferred_professional_id: Optional[str] = Field(None, description="Optional preferred verified professional ID")


class RequestInformationPayload(BaseModel):
    requested_information: str = Field(..., min_length=5, max_length=2000, description="Questions/information requested by professional")


class ProvideInformationPayload(BaseModel):
    patient_additional_info: str = Field(..., min_length=2, max_length=3000, description="Patient's response to requested information")


class ProfessionalReviewSubmitRequest(BaseModel):
    clinical_observations: Optional[str] = Field(None, max_length=5000, description="Detailed radiological/clinical observations")
    professional_impression: Optional[str] = Field(None, max_length=5000, description="Doctor's synthesis / radiological impression")
    recommendations: Optional[Union[str, List[str]]] = Field(None, description="Clinical recommendations or next steps for patient care")
    urgency: Optional[Literal["ROUTINE", "PRIORITY", "URGENT", "EMERGENCY"]] = Field("ROUTINE", description="Clinical urgency level")
    follow_up: Optional[bool] = Field(False, description="Whether formal clinical follow-up is recommended")
    additional_notes: Optional[str] = Field(None, max_length=3000, description="Additional technical or private physician notes")

    # Compatibility aliases
    clinical_summary: Optional[str] = Field(None, description="Professional clinical summary of the radiograph and AI findings")
    clinical_impression: Optional[str] = Field(None, description="Doctor's synthesis / radiological impression")
    finding_validations: Optional[Dict[str, Literal["AGREED", "DISAGREED", "INCONCLUSIVE", "NOT_EVALUATED"]]] = Field(
        default_factory=dict,
        description="Structured validation against evaluated AI findings (AGREED, DISAGREED, INCONCLUSIVE)"
    )
    professional_notes: Optional[str] = Field(None, description="Additional technical observations or radiological notes")
    limitations: Optional[str] = Field(None, description="Technical or patient-positioning limitations noted")
    follow_up_required: Optional[bool] = Field(False, description="Whether formal clinical follow-up is recommended")
    message_to_patient: Optional[str] = Field(None, description="Direct patient-facing message or instructions")
    assessment: Optional[str] = None

    @field_validator("recommendations", mode="before")
    @classmethod
    def format_recommendations(cls, v: Any) -> Any:
        if isinstance(v, list):
            return "\n".join(str(item) for item in v)
        return v


class ProfessionalAssessmentDraftRequest(BaseModel):
    clinical_observations: Optional[str] = Field(None, max_length=5000)
    professional_impression: Optional[str] = Field(None, max_length=5000)
    recommendations: Optional[Union[str, List[str]]] = None
    urgency: Optional[Literal["ROUTINE", "PRIORITY", "URGENT", "EMERGENCY"]] = "ROUTINE"
    follow_up: Optional[bool] = False
    additional_notes: Optional[str] = Field(None, max_length=3000)

    @field_validator("recommendations", mode="before")
    @classmethod
    def format_draft_recommendations(cls, v: Any) -> Any:
        if isinstance(v, list):
            return "\n".join(str(item) for item in v)
        return v

    # Aliases
    clinical_summary: Optional[str] = None
    clinical_impression: Optional[str] = None
    finding_validations: Optional[Dict[str, Literal["AGREED", "DISAGREED", "INCONCLUSIVE", "NOT_EVALUATED"]]] = Field(default_factory=dict)
    professional_notes: Optional[str] = None
    limitations: Optional[str] = None
    follow_up_required: Optional[bool] = False
    message_to_patient: Optional[str] = None
    assessment: Optional[str] = None


# Backward compatibility alias
CompleteReviewRequest = ProfessionalReviewSubmitRequest
ProfessionalAssessmentSubmitRequest = ProfessionalReviewSubmitRequest


# --------------------------------------------------
# Response Schemas
# --------------------------------------------------

class ProfessionalPublicInfo(BaseModel):
    id: str
    full_name: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[str] = None
    specialty: Optional[str] = None
    qualification: Optional[str] = None
    hospital_or_clinic: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_country: Optional[str] = None


class PatientPublicInfo(BaseModel):
    id: str = Field(..., description="Unique patient identifier")
    full_name: Optional[str] = Field(None, description="Patient's full name")
    username: Optional[str] = Field(None, description="Patient's unique username")
    display_name: Optional[str] = Field(None, description="Patient's display name")

    class Config:
        from_attributes = True


class CaseAnalysisWorkspace(BaseModel):
    analysis_id: str
    view: str = "Frontal"
    image_url: Optional[str] = None
    image: Optional[str] = None
    findings: Dict[str, Any] = Field(default_factory=dict)
    detected_findings: List[str] = Field(default_factory=list)
    heatmaps: Dict[str, Optional[str]] = Field(default_factory=dict)
    patient_explanations: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[str] = None




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
    professionals: List[DoctorDirectoryItem] = Field(default_factory=list, description="List of verified healthcare professionals")
    total: int = Field(..., description="Total number of matching verified professionals")


class ProfessionalReviewResponse(BaseModel):
    id: str
    review_request_id: str
    professional_id: str
    clinical_summary: Optional[str] = None
    clinical_observations: Optional[str] = None
    clinical_impression: Optional[str] = None
    professional_impression: Optional[str] = None
    finding_validations: Dict[str, Any] = Field(default_factory=dict)
    professional_notes: Optional[str] = None
    additional_notes: Optional[str] = None
    recommendations: Optional[str] = None
    limitations: Optional[str] = None
    urgency: Optional[str] = "ROUTINE"
    follow_up_required: Optional[bool] = False
    follow_up: Optional[bool] = False
    message_to_patient: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Backward compatibility accessor
    @property
    def assessment(self) -> Optional[str]:
        return self.clinical_observations or self.clinical_summary

    class Config:
        from_attributes = True


class ReviewRequestResponse(BaseModel):
    id: str
    analysis_id: str
    patient_id: str
    professional_id: Optional[str] = None
    status: ReviewStatus
    patient_message: Optional[str] = None
    requested_information: Optional[str] = None
    patient_additional_info: Optional[str] = None
    payment_status: str = "UNPAID"
    requested_at: Optional[datetime] = None
    assigned_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    professional: Optional[ProfessionalPublicInfo] = None
    professional_review: Optional[ProfessionalReviewResponse] = None

    class Config:
        from_attributes = True


class ReviewRequestDetailResponse(BaseModel):
    review_request: ReviewRequestResponse
    analysis_summary: Optional[Dict[str, Any]] = None
    ai_report: Optional[Dict[str, Any]] = None
    professional: Optional[ProfessionalPublicInfo] = None
    professional_review: Optional[ProfessionalReviewResponse] = None


class ProfessionalCaseWorkspaceResponse(BaseModel):
    review_request: ReviewRequestResponse
    patient: PatientPublicInfo
    analysis: CaseAnalysisWorkspace
    ai_report: Optional[Dict[str, Any]] = None
    professional: Optional[ProfessionalPublicInfo] = None
    professional_review: Optional[ProfessionalReviewResponse] = None

    class Config:
        from_attributes = True


class PatientProfessionalReviewResponse(BaseModel):
    review_id: str
    analysis_id: str
    status: str
    completed_at: Optional[datetime] = None
    professional: Optional[ProfessionalPublicInfo] = None
    professional_review: Optional[ProfessionalReviewResponse] = None
    ai_decision_support: Dict[str, Any] = Field(default_factory=dict)
    clinical_notice: str = (
        "This professional review is provided as part of the HC-XCDSS clinical decision-support platform. "
        "It should be considered together with comprehensive clinical evaluation by your primary healthcare provider."
    )

    class Config:
        from_attributes = True


class ProfessionalReviewReportResponse(BaseModel):
    report_id: str
    generated_at: str
    case_information: Dict[str, Any] = Field(default_factory=dict)
    ai_decision_support: Dict[str, Any] = Field(default_factory=dict)
    professional_review: Dict[str, Any] = Field(default_factory=dict)
    clinical_disclaimer: str

