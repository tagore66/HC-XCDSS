"""
HC-XCDSS AI Prompt Construction System

Builds structured, role-aware system prompts and user payloads
separating system safety directives, role rules, analysis context, and user questions.
"""

from typing import Dict, Any, List, Optional


SYSTEM_BASE_INSTRUCTION = """You are the HC-XCDSS AI Assistant, an AI clinical decision-support explainer for chest radiograph analyses.
You operate strictly on the deterministic analysis data provided in the context below.

CORE SAFETY & FACTUALITY RULES:
1. ONLY discuss findings and facts directly supported by the supplied analysis context.
2. NEVER invent findings, pathologies, or symptoms not present in the report.
3. NEVER alter or contradict model probabilities, thresholds, or detection statuses.
4. Explain clearly that Grad-CAM heatmaps highlight model attention regions, NOT confirmed tissue pathology.
5. NEVER present an AI prediction as a confirmed, definitive medical diagnosis.
6. NEVER prescribe medications, calculate drug dosages, or recommend specific pharmaceutical treatments.
7. If a user asks a question outside the scope of this radiograph analysis, state clearly that the finding or question cannot be determined from this chest X-ray.
8. Maintain a supportive, objective, and clinically responsible tone at all times.
"""

PATIENT_ROLE_INSTRUCTION = """ROLE INSTRUCTIONS (PATIENT AUDIENCE):
- Use clear, empathetic, and human-centred language.
- Explain medical terms and findings in accessible, everyday language.
- Carefully explain what probabilities and visual heatmaps mean without causing undue alarm.
- Clearly emphasize that this is an automated screening/decision-support tool and encourage discussing any concerns with their healthcare professional.
- Never give treatment or medication instructions.
"""

PROFESSIONAL_ROLE_INSTRUCTION = """ROLE INSTRUCTIONS (HEALTHCARE PROFESSIONAL AUDIENCE):
- Use precise clinical, radiological, and statistical terminology.
- Report exact model probabilities, operating thresholds, and view-specific considerations.
- Discuss model attention (Grad-CAM), potential differential considerations based strictly on the flagged visual patterns, and known DenseNet121 limitations.
- Distinguish clearly between raw model activation and clinical interpretation.
"""


def build_system_instruction(role: str = "patient") -> str:
    """
    Constructs the system instruction tailored to the specified user role.
    """
    role_normalized = (role or "patient").lower().strip()
    if role_normalized in ["professional", "doctor", "clinician"]:
        return f"{SYSTEM_BASE_INSTRUCTION}\n{PROFESSIONAL_ROLE_INSTRUCTION}"
    return f"{SYSTEM_BASE_INSTRUCTION}\n{PATIENT_ROLE_INSTRUCTION}"


def format_analysis_context_for_prompt(context: Dict[str, Any]) -> str:
    """
    Formats the sanitized analysis context dictionary into a clean, structured textual block.
    """
    view = context.get("view", "Frontal")
    analysis_id = context.get("analysis_id", "N/A")
    detected_count = context.get("findings_detected_count", 0)
    detected_findings = context.get("detected_findings", [])
    all_findings = context.get("all_evaluated_findings", [])
    summary = context.get("summary", "")
    patient_interp = context.get("patient_interpretation", {})

    lines = [
        "=== RADIOGRAPH ANALYSIS CONTEXT ===",
        f"Analysis ID: {analysis_id}",
        f"Projection View: {view}",
        f"Overall Summary: {summary}",
        f"Detected Findings Count: {detected_count}",
        "",
        "--- DETECTED FINDINGS ---"
    ]

    if not detected_findings:
        lines.append("None. All evaluated findings were below their detection thresholds.")
    else:
        for f in detected_findings:
            prob_pct = f"{round((f.get('probability') or 0) * 100, 1)}%"
            thresh_pct = f"{round((f.get('threshold') or 0) * 100, 1)}%"
            lines.append(
                f"• Finding: {f.get('finding')} (Probability: {prob_pct}, View Threshold: {thresh_pct}, Grad-CAM Available: {f.get('gradcam_available')})"
            )
            if f.get("simple_explanation"):
                lines.append(f"  Explanation: {f.get('simple_explanation')}")
            if f.get("what_it_means"):
                lines.append(f"  Clinical Meaning: {f.get('what_it_means')}")
            if f.get("possible_causes"):
                lines.append(f"  Common Causes: {', '.join(f.get('possible_causes', []))}")

    lines.append("")
    lines.append("--- ALL EVALUATED FINDINGS ---")
    for ef in all_findings:
        status_str = "DETECTED" if ef.get("detected") else "NOT DETECTED"
        prob_val = round((ef.get("probability") or 0) * 100, 1)
        thresh_val = round((ef.get("threshold") or 0) * 100, 1)
        lines.append(f"• {ef.get('finding')}: {prob_val}% (Threshold: {thresh_val}%) -> {status_str}")

    if patient_interp.get("headline"):
        lines.append("")
        lines.append(f"Patient Headline: {patient_interp.get('headline')}")
        lines.append(f"Patient Interpretation Details: {patient_interp.get('details')}")

    lines.append("=== END ANALYSIS CONTEXT ===")
    return "\n".join(lines)


def build_user_prompt(context: Dict[str, Any], user_question: str) -> str:
    """
    Constructs the final prompt incorporating the structured context and user question.
    """
    context_str = format_analysis_context_for_prompt(context)
    return (
        f"{context_str}\n\n"
        f"USER QUESTION: {user_question.strip()}\n\n"
        f"Please provide your response based strictly on the above analysis context."
    )
