"""
HC-XCDSS Context-Aware AI Assistant Service

Orchestrates prompt building, deterministic safety guardrails, context extraction,
and provider-agnostic generation (Gemini with fallback mock).
"""

from typing import Any, Dict, List, Optional
from .context_builder import build_patient_ai_context
from .prompt_builder import build_system_instruction, build_user_prompt
from .safety_validator import validate_user_question, validate_model_response, SafetyValidationResult
from .providers.base import BaseLLMProvider
from .providers import get_llm_provider


class AIAssistantService:
    """
    Unified, role-aware AI Assistant Service for HC-XCDSS.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or get_llm_provider()

    def answer_question(
        self,
        report_or_analysis: Dict[str, Any],
        question: str,
        role: str = "patient",
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a user question regarding a completed analysis report.

        Args:
            report_or_analysis: Analysis dict containing 'report' or report dictionary itself.
            question: The user query string.
            role: Audience role ('patient' or 'professional').
            conversation_history: List of preceding turns [{"role": "user"|"model", "content": "..."}].
            context: Optional pre-loaded sanitized AIContext dictionary.

        Returns:
            Dict matching AssistantMessageResponse schema.
        """
        # Extract report data if context not supplied
        if not context:
            report = report_or_analysis.get("report") if "report" in report_or_analysis else report_or_analysis
            if not report or not isinstance(report, dict):
                report = report_or_analysis
            context = build_patient_ai_context(report)

        analysis_id = context.get("analysis_id") or report_or_analysis.get("analysis_id", "N/A")
        role_clean = (role or "patient").lower().strip()

        # 1. Deterministic Safety Validation
        val: SafetyValidationResult = validate_user_question(question, role=role_clean)

        if not val.is_valid or val.user_message:
            return {
                "analysis_id": analysis_id,
                "role": role_clean,
                "answer": val.user_message or "Invalid question.",
                "safety_notice": "AI decision-support only. Not a medical diagnosis.",
                "provider": "safety_guardrail",
                "model": "deterministic_filter",
                "safety_status": val.status,
                "flags": val.matched_flags or [],
            }

        # 2. Construct Role-Specific System Instruction and Prompt
        system_instruction = build_system_instruction(role=role_clean)
        user_prompt = build_user_prompt(context, question.strip())

        # 3. Attempt Generation with Configured Provider (or Graceful Mock Fallback)
        try:
            if hasattr(self.provider, "is_configured") and not self.provider.is_configured:
                # API key is not configured -> return deterministic development answer
                answer = self._generate_fallback_response(context, question.strip(), role=role_clean)
                return {
                    "analysis_id": analysis_id,
                    "role": role_clean,
                    "answer": answer,
                    "safety_notice": "AI decision-support only. Not a medical diagnosis.",
                    "provider": "development_gateway",
                    "model": "mock_explainer_v1",
                    "safety_status": "ok",
                    "flags": [],
                }

            result = self.provider.generate_response(
                system_instruction=system_instruction,
                prompt=user_prompt,
                conversation_history=conversation_history,
            )

            raw_text = result.get("text", "").strip()

            # 4. Post-Generation Safety Validation
            post_val = validate_model_response(raw_text, role=role_clean)
            final_text = post_val.user_message if not post_val.is_valid else raw_text
            safety_status = post_val.status if not post_val.is_valid else "ok"
            flags = post_val.matched_flags if not post_val.is_valid else []

            return {
                "analysis_id": analysis_id,
                "role": role_clean,
                "answer": final_text,
                "safety_notice": "AI decision-support only. Not a medical diagnosis.",
                "provider": result.get("provider", self.provider.provider_name),
                "model": result.get("model", self.provider.model_name),
                "safety_status": safety_status,
                "flags": flags,
            }

        except Exception as e:
            # On provider network or runtime failure, degrade gracefully
            fallback_answer = self._generate_fallback_response(context, question.strip(), role=role_clean)
            return {
                "analysis_id": analysis_id,
                "role": role_clean,
                "answer": fallback_answer,
                "safety_notice": "AI decision-support only. Not a medical diagnosis.",
                "provider": "fallback_gateway",
                "model": "deterministic_explainer",
                "safety_status": "provider_fallback",
                "flags": [f"provider_error: {str(e)}"],
            }

    def _generate_fallback_response(
        self, context: Dict[str, Any], question: str, role: str = "patient"
    ) -> str:
        """
        Deterministic, context-aware fallback response generation.
        """
        view = context.get("view", "Frontal")
        detected_count = context.get("findings_detected_count", 0)
        detected_findings = context.get("detected_findings", [])
        q_lower = question.lower()

        # Grad-CAM / heatmap
        if any(w in q_lower for w in ["grad-cam", "heatmap", "highlight", "visual", "colors"]):
            if role in ["professional", "doctor"]:
                return (
                    f"Grad-CAM on this {view} projection highlights model attention via the final convolutional layer (norm5). "
                    "Regions with peak gradients contributed most significantly to the classification logit for detected findings. "
                    "These activation heatmaps indicate model visual saliency rather than histological or pathological margins."
                )
            return (
                "Grad-CAM creates the visual color overlays on your X-ray. The highlighted regions show which areas of the image "
                "most influenced the AI's detection for flagged findings. These heatmaps explain what the AI noticed and are not diagnostic pathology maps."
            )

        # Finding explanations
        for f in detected_findings:
            fname = f["finding"].lower()
            if fname in q_lower:
                if role in ["professional", "doctor"]:
                    prob_pct = round((f.get("probability") or 0) * 100, 1)
                    thresh_pct = round((f.get("threshold") or 0) * 100, 1)
                    return (
                        f"Finding: {f['finding']}. Model probability: {prob_pct}% against view threshold {thresh_pct}%. "
                        f"Radiological definition: {f.get('what_it_means', '')} "
                        f"Known etiologies: {', '.join(f.get('possible_causes', []))}. "
                        "Recommendation: Correlate with clinical history and physical examination."
                    )
                return (
                    f"{f['title']}: {f.get('simple_explanation', '')} "
                    f"What this means: {f.get('what_it_means', '')} "
                    f"Common causes: {', '.join(f.get('possible_causes', []))}. "
                    f"Important note: {f.get('important_note', 'Please consult your doctor for medical interpretation.')}"
                )

        # General summary / meaning
        if detected_count == 0:
            if role in ["professional", "doctor"]:
                return (
                    f"For this {view} chest radiograph, 0 of {context.get('findings_evaluated_count', 5)} evaluated findings "
                    "exceeded configured view-specific operating thresholds. The study is negative for evaluated acute findings."
                )
            return (
                f"On this {view} chest X-ray, all {context.get('findings_evaluated_count', 5)} evaluated conditions were below their detection thresholds. "
                "In simple terms, the AI did not identify prominent abnormal visual patterns for the evaluated findings."
            )

        detected_names = ", ".join(f["finding"] for f in detected_findings)
        if role in ["professional", "doctor"]:
            return (
                f"Analysis ({view} view) identified {detected_count} positive finding(s): {detected_names}. "
                "Probabilities are computed using DenseNet121 trained on CheXpert with view-specific tuned thresholds."
            )

        return (
            f"Based on your {view} chest X-ray analysis, {detected_count} finding(s) were flagged: {detected_names}. "
            "Remember that AI detections indicate visual patterns for doctor review and are not confirmed medical diagnoses."
        )


# Backward-compatible alias
PatientAssistantService = AIAssistantService
