"""
HC-XCDSS Patient AI Safety & Validation Guardrails

Provides deterministic safety validation for patient queries before LLM invocation,
detecting empty prompts, length violations, diagnosis requests, and medication/treatment queries.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

MAX_QUESTION_LENGTH = 500
MIN_QUESTION_LENGTH = 2


@dataclass
class SafetyValidationResult:
    is_valid: bool
    status: str  # "ok", "empty", "too_long", "diagnosis_request", "treatment_request", "inappropriate"
    user_message: Optional[str] = None
    disclaimer_required: bool = True
    matched_flags: Optional[List[str]] = None


# Patterns indicating direct demands for a definitive medical diagnosis
DIAGNOSIS_SEEKING_PATTERNS = [
    r"\bdo i have\b",
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

# Patterns asking for prescription, medication, or medical treatment advice
TREATMENT_SEEKING_PATTERNS = [
    r"\bwhat medication should i take\b",
    r"\bwhat pills should i take\b",
    r"\bwhat drug should i take\b",
    r"\bprescribe me\b",
    r"\bshould i take antibiotics\b",
    r"\bhow should i treat\b",
    r"\bwhat is the treatment for my\b",
    r"\bwhat dosage\b",
    r"\bhow many mg\b",
    r"\bcan i take aspirin\b",
    r"\bshould i stop taking\b",
]


def validate_patient_question(question: Optional[str]) -> SafetyValidationResult:
    """
    Deterministically validates a patient question against safety criteria.

    Args:
        question: The user input query string.

    Returns:
        SafetyValidationResult with validation flag, status reason, and contextual guidance.
    """
    if question is None or not question.strip():
        return SafetyValidationResult(
            is_valid=False,
            status="empty",
            user_message="Please provide a question about your X-ray report.",
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

    # Check for diagnosis seeking
    for pattern in DIAGNOSIS_SEEKING_PATTERNS:
        if re.search(pattern, lower_query):
            return SafetyValidationResult(
                is_valid=True,
                status="diagnosis_request",
                user_message=(
                    "I cannot provide a definitive medical diagnosis. "
                    "HC-XCDSS identifies radiographic patterns that suggest findings for clinical review. "
                    "Please consult your healthcare provider for a clinical diagnosis."
                ),
                disclaimer_required=True,
                matched_flags=["diagnosis_seeking"],
            )

    # Check for medication or treatment advice seeking
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

    # Valid query passed guardrails
    return SafetyValidationResult(
        is_valid=True,
        status="ok",
        user_message=None,
        disclaimer_required=True,
        matched_flags=[],
    )
