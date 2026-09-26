"""
HC-XCDSS AI Safety & Validation Layer
"""

import re
from dataclasses import dataclass
from typing import List, Optional


MAX_QUESTION_LENGTH = 1000
MIN_QUESTION_LENGTH = 2


@dataclass
class SafetyValidationResult:
    is_valid: bool
    status: str  # "ok", "empty", "too_long", "diagnosis_request", "treatment_request", "emergency"
    user_message: Optional[str] = None
    disclaimer_required: bool = True
    matched_flags: Optional[List[str]] = None


# Emergency / Acute danger patterns
EMERGENCY_PATTERNS = [
    r"\bam i having a heart attack\b",
    r"\bcan't breathe\b",
    r"\bcannot breathe\b",
    r"\bsevere chest pain\b",
    r"\bcoughing up blood\b",
    r"\bpass out\b",
    r"\blosing consciousness\b",
]

# Patterns demanding definitive diagnosis
DIAGNOSIS_SEEKING_PATTERNS = [
    r"\bdo i have\b",
    r"\bdo i definitely have\b",
    r"\bam i sick\b",
    r"\bdiagnose me\b",
    r"\bwhat is my diagnosis\b",
    r"\bdo i have cancer\b",
    r"\bdo i have pneumonia\b",
    r"\bdo i have covid\b",
    r"\bdo i have heart failure\b",
    r"\bam i dying\b",
    r"\btell me if i have\b",
    r"\bis this definitely\b",
    r"\bgive me a diagnosis\b",
]

# Patterns demanding drug prescriptions or medical treatment
TREATMENT_SEEKING_PATTERNS = [
    r"\bwhat medication should i take\b",
    r"\bwhat medication\b",
    r"\bwhat pills should i take\b",
    r"\bwhat pills\b",
    r"\bwhat drug should i take\b",
    r"\bwhat drug\b",
    r"\bprescribe me\b",
    r"\bshould i take antibiotics\b",
    r"\bhow should i treat\b",
    r"\bwhat is the treatment for my\b",
    r"\bwhat dosage\b",
    r"\bhow many mg\b",
    r"\bcan i take aspirin\b",
    r"\bshould i stop taking\b",
]


def validate_user_question(question: Optional[str], role: str = "patient") -> SafetyValidationResult:
    """
    Validates a question against length, structural, and safety criteria.
    """
    if question is None or not question.strip():
        return SafetyValidationResult(
            is_valid=False,
            status="empty",
            user_message="Please provide a question about this X-ray analysis.",
            disclaimer_required=True,
            matched_flags=["empty_query"],
        )

    cleaned = question.strip()

    if len(cleaned) < MIN_QUESTION_LENGTH:
        return SafetyValidationResult(
            is_valid=False,
            status="empty",
            user_message="The question is too short. Please provide more detail.",
            disclaimer_required=True,
            matched_flags=["too_short"],
        )

    if len(cleaned) > MAX_QUESTION_LENGTH:
        return SafetyValidationResult(
            is_valid=False,
            status="too_long",
            user_message=f"Question exceeds maximum allowed length of {MAX_QUESTION_LENGTH} characters. Please shorten your query.",
            disclaimer_required=True,
            matched_flags=["length_exceeded"],
        )

    lower_query = cleaned.lower()

    # Emergency check
    for pattern in EMERGENCY_PATTERNS:
        if re.search(pattern, lower_query):
            return SafetyValidationResult(
                is_valid=True,
                status="emergency",
                user_message=(
                    "If you are experiencing severe symptoms such as acute chest pain, difficulty breathing, or coughing blood, "
                    "please call emergency services (e.g. 911 / 112) or go to the nearest emergency room immediately."
                ),
                disclaimer_required=True,
                matched_flags=["emergency_alert"],
            )

    # If role is patient, check for diagnosis / prescription seeking
    if (role or "patient").lower() == "patient":
        for pattern in DIAGNOSIS_SEEKING_PATTERNS:
            if re.search(pattern, lower_query):
                return SafetyValidationResult(
                    is_valid=True,
                    status="diagnosis_request",
                    user_message=(
                        "I cannot provide a definitive medical diagnosis. "
                        "HC-XCDSS identifies radiographic patterns that suggest findings for clinical review. "
                        "Please consult a licensed healthcare professional for a clinical diagnosis."
                    ),
                    disclaimer_required=True,
                    matched_flags=["diagnosis_seeking"],
                )

        for pattern in TREATMENT_SEEKING_PATTERNS:
            if re.search(pattern, lower_query):
                return SafetyValidationResult(
                    is_valid=True,
                    status="treatment_request",
                    user_message=(
                        "I cannot prescribe medications or recommend specific medical treatments. "
                        "Treatment decisions require full clinical evaluation by a licensed doctor."
                    ),
                    disclaimer_required=True,
                    matched_flags=["treatment_seeking"],
                )

    return SafetyValidationResult(
        is_valid=True,
        status="ok",
        user_message=None,
        disclaimer_required=True,
        matched_flags=[],
    )


# Patterns indicating dangerous model output claims
UNSAFE_OUTPUT_PATTERNS = [
    (r"\bi prescribe\b", "prescription_claim"),
    (r"\btake \d+\s*mg\b", "dosage_instruction"),
    (r"\byou definitely have\b", "definitive_diagnosis_claim"),
    (r"\bi diagnose you with\b", "doctor_impersonation"),
    (r"\bas your doctor\b", "doctor_impersonation"),
    (r"\byou do not need a doctor\b", "medical_bypass_advice"),
]


def validate_model_response(response_text: str, role: str = "patient") -> SafetyValidationResult:
    """
    Post-generation safety verification of the model's text response.
    Catches hallucinations or safety filter bypasses (e.g. prescribing medication, claiming to be a doctor).
    """
    if not response_text or not response_text.strip():
        return SafetyValidationResult(
            is_valid=False,
            status="empty_response",
            user_message="I apologize, but I could not generate an answer for this question. Please try asking again.",
            disclaimer_required=True,
            matched_flags=["empty_output"],
        )

    lower_resp = response_text.lower()

    for pattern, flag in UNSAFE_OUTPUT_PATTERNS:
        if re.search(pattern, lower_resp):
            safe_fallback = (
                "Based on the analysis report, HC-XCDSS identifies radiographic visual patterns for clinical decision support. "
                "AI observations are probabilistic and cannot provide a definitive diagnosis or medical prescription. "
                "Please discuss these findings with a licensed healthcare professional."
            )
            return SafetyValidationResult(
                is_valid=False,
                status="unsafe_model_output",
                user_message=safe_fallback,
                disclaimer_required=True,
                matched_flags=[flag],
            )

    return SafetyValidationResult(
        is_valid=True,
        status="ok",
        user_message=response_text.strip(),
        disclaimer_required=True,
        matched_flags=[],
    )

