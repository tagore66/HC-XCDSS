"""
HC-XCDSS Deterministic Report Generator

Converts completed chest X-ray analysis results into structured,
deterministic reports without performing inference or calling LLMs.
"""

from typing import Any, Dict, List, Optional


def generate_analysis_report(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a structured, deterministic clinical decision support report
    from a completed analysis result dictionary.

    Args:
        analysis_result: Dictionary containing analysis fields:
            - analysis_id
            - created_at (optional)
            - view
            - image
            - findings
            - detected_findings
            - heatmaps
            - patient_explanations

    Returns:
        Structured report dictionary.
    """
    analysis_id: Optional[str] = analysis_result.get("analysis_id")
    created_at: Optional[str] = analysis_result.get("created_at")
    view: str = analysis_result.get("view", "Frontal")
    image: Optional[str] = analysis_result.get("image")

    raw_findings: Dict[str, Any] = analysis_result.get("findings", {})
    detected_finding_names: List[str] = analysis_result.get("detected_findings", [])
    heatmaps: Dict[str, Any] = analysis_result.get("heatmaps", {})
    patient_explanations: List[Dict[str, Any]] = analysis_result.get("patient_explanations", [])

    # Index existing patient explanations by finding name for fast deterministic lookup
    explanation_map = {
        item.get("finding"): item
        for item in patient_explanations
        if isinstance(item, dict) and "finding" in item
    }

    # Build evaluated findings list (deterministic ordering based on findings dict keys)
    findings_evaluated: List[Dict[str, Any]] = []
    findings_detected: List[Dict[str, Any]] = []

    for name, finding_data in raw_findings.items():
        is_dict = isinstance(finding_data, dict)
        prob = finding_data.get("probability") if is_dict else None
        thresh = finding_data.get("threshold") if is_dict else None
        is_detected = finding_data.get("detected", False) if is_dict else (name in detected_finding_names)
        heatmap_url = heatmaps.get(name) if isinstance(heatmaps, dict) else None
        explanation = explanation_map.get(name)

        evaluated_entry = {
            "name": name,
            "probability": prob,
            "threshold": thresh,
            "detected": is_detected,
            "heatmap": heatmap_url,
        }
        findings_evaluated.append(evaluated_entry)

        if is_detected or name in detected_finding_names:
            detected_entry = {
                "name": name,
                "probability": prob,
                "threshold": thresh,
                "detected": True,
                "heatmap": heatmap_url,
                "explanation": explanation,
            }
            findings_detected.append(detected_entry)

    total_evaluated = len(raw_findings)
    total_detected = len(findings_detected)

    # Build deterministic overall summary
    if total_detected == 0:
        overall_summary = (
            f"No evaluated radiographic findings were detected above their view-specific thresholds "
            f"on this {view} chest radiograph ({total_evaluated} findings evaluated)."
        )
    else:
        detected_names_str = ", ".join(f["name"] for f in findings_detected)
        overall_summary = (
            f"{total_detected} radiographic finding(s) detected on this {view} chest radiograph "
            f"above configured thresholds: {detected_names_str}."
        )

    # Build patient-friendly interpretation based ONLY on existing explanation data
    if total_detected == 0:
        patient_interpretation = {
            "headline": "No specific radiographic abnormalities identified by the model.",
            "details": (
                "None of the evaluated conditions crossed the AI detection thresholds for this X-ray view. "
                "This indicates that patterns associated with the evaluated findings were not prominently detected."
            ),
            "findings_explained": [],
        }
    else:
        findings_explained = []
        for det in findings_detected:
            name = det["name"]
            expl = det.get("explanation")
            if expl:
                findings_explained.append({
                    "finding": name,
                    "title": expl.get("title", name),
                    "simple_explanation": expl.get("simple_explanation"),
                    "what_it_means": expl.get("what_it_means"),
                    "possible_causes": expl.get("possible_causes", []),
                    "important_note": expl.get("important_note"),
                })
            else:
                findings_explained.append({
                    "finding": name,
                    "title": name,
                    "simple_explanation": f"Pattern consistent with {name.lower()} was identified by the model.",
                    "what_it_means": f"{name} was flagged above the detection threshold for this radiograph.",
                    "possible_causes": [],
                    "important_note": "Consult a qualified physician for clinical correlation.",
                })

        patient_interpretation = {
            "headline": f"{total_detected} finding(s) identified for clinical review.",
            "details": (
                "The AI model identified radiographic patterns that crossed detection thresholds. "
                "These descriptions explain the findings in plain language and do not represent a medical diagnosis."
            ),
            "findings_explained": findings_explained,
        }

    # Explainability information
    explainability = {
        "method": "Grad-CAM",
        "description": (
            "Gradient-weighted Class Activation Mapping (Grad-CAM) highlights the spatial image regions "
            "that contributed most strongly to the model's prediction for each detected finding."
        ),
        "visualizations_available": [
            f["name"] for f in findings_detected if f.get("heatmap") is not None
        ],
    }

    # Clinical limitations / disclaimer
    clinical_disclaimer = {
        "disclaimer": (
            "HC-XCDSS is an AI-assisted clinical decision-support system intended solely for assistive evaluation. "
            "It does not provide definitive diagnoses or treatment plans and must not replace professional clinical "
            "judgment by a licensed healthcare provider."
        ),
        "context_notice": (
            "AI predictions must be interpreted in conjunction with complete patient history, physical examination, "
            "and other diagnostic modalities."
        ),
    }

    return {
        "analysis_id": analysis_id,
        "created_at": created_at,
        "view": view,
        "image": image,
        "findings_evaluated": findings_evaluated,
        "findings_detected": findings_detected,
        "total_evaluated": total_evaluated,
        "total_detected": total_detected,
        "overall_summary": overall_summary,
        "patient_interpretation": patient_interpretation,
        "explainability": explainability,
        "clinical_disclaimer": clinical_disclaimer,
    }
