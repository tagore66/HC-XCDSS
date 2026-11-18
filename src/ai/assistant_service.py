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
        Provides comprehensive, role-tailored explanations for any user query.
        """
        from ..explanation.finding_explanations import FINDING_EXPLANATIONS
        view = context.get("view", "Frontal")
        detected_count = context.get("findings_detected_count", 0)
        detected_findings = context.get("detected_findings", [])
        all_evaluated = context.get("all_evaluated_findings", [])
        q_lower = question.lower()
        is_prof = role in ["professional", "doctor", "clinician"]

        # 1. Questions to ask doctor / clinical follow-up
        if any(w in q_lower for w in ["ask my doctor", "ask doctor", "questions for doctor", "next steps", "follow-up", "follow up"]):
            if is_prof:
                return (
                    f"**Clinical Recommendations for {view} Projection:**\n"
                    f"1. **Clinical Correlation:** Correlate model output scores with presenting symptoms (e.g. dyspnea, cough, fever) and physical exam.\n"
                    f"2. **Differential Evaluation:** Review highlighted visual activation areas against potential differentials.\n"
                    f"3. **Follow-up Imaging:** Consider lateral projection, comparison with prior radiographs, or targeted thoracic CT if clinical suspicion persists."
                )
            if detected_count > 0:
                det_names = ", ".join(f["finding"] for f in detected_findings)
                return (
                    f"**Recommended Questions to Discuss with Your Doctor:**\n\n"
                    f"• *\"The AI analysis flagged potential patterns for **{det_names}**. Does my physical examination or symptoms support this?\"*\n"
                    f"• *\"Do you recommend any additional tests, comparison with past X-rays, or follow-up imaging?\"*\n"
                    f"• *\"What steps or lifestyle adjustments, if any, do you suggest based on these results?\"*\n\n"
                    f"Remember: Your doctor evaluates this result together with your full medical history."
                )
            return (
                f"**Questions to Discuss with Your Doctor:**\n\n"
                f"• *\"The AI did not flag any of the 5 evaluated findings. Do my symptoms require any other evaluations?\"*\n"
                f"• *\"Are there any other aspects of my health or chest symptoms we should review?\"*\n\n"
                f"Your healthcare provider remains your primary guide for personal health decisions."
            )

        # 2. Grad-CAM / Visual attention / Heatmap / Why was this area highlighted
        if any(w in q_lower for w in ["grad-cam", "heatmap", "highlight", "visual", "colors", "focus", "area highlighted", "where did"]):
            if is_prof:
                return (
                    f"**Model Visual Saliency (Grad-CAM):**\n\n"
                    f"On this **{view}** view, Grad-CAM computes gradients with respect to feature maps in the final convolutional layer (`features.norm5`). "
                    f"The resulting heatmaps represent areas of highest spatial activation contributing to the classification score. "
                    f"These heatmaps indicate model visual attention rather than anatomical disease boundaries or histopathological margins."
                )
            return (
                f"**Where Did the AI Focus?**\n\n"
                f"The color overlay on your X-ray is called a **Grad-CAM attention map**. "
                f"It shows the specific regions of the image that the AI looked at most closely when analyzing your scan.\n\n"
                f"• **Highlighted regions:** Show visual patterns that caught the AI's attention.\n"
                f"• **Important context:** The highlight is an attention map explaining the AI's focus — it is not a boundary of disease or proof that an illness is present."
            )

        # 3. Why did the AI flag this / Operating thresholds / Model scores
        if any(w in q_lower for w in ["why did the ai flag", "why flagged", "operating threshold", "threshold", "score", "probability", "model output"]):
            if is_prof:
                lines = [f"**Operating Threshold Breakdown ({view} Projection):**\n"]
                for ef in all_evaluated:
                    prob = ef.get("probability") or 0
                    thresh = ef.get("threshold") or 0.5
                    status = "FLAGGED (Above Threshold)" if ef.get("detected") else "Below Operating Threshold"
                    lines.append(f"• **{ef.get('finding')}**: Score `{prob:.3f}` vs Operating Threshold `{thresh:.3f}` -> *{status}*")
                lines.append("\n*Operating thresholds were selected empirically on Stanford CheXpert validation data to optimize sensitivity/specificity.*")
                return "\n".join(lines)
            
            if detected_count > 0:
                det_list = []
                for df in detected_findings:
                    det_list.append(f"• **{df['finding']}**: The AI identified visual patterns that met its decision threshold for this finding.")
                return (
                    f"**Why Did the AI Flag These Findings?**\n\n"
                    + "\n".join(det_list) + "\n\n"
                    f"The AI evaluates image patterns against operating decision thresholds established during validation. "
                    f"When image characteristics match patterns associated with a condition, it flags the finding for doctor review."
                )
            return (
                f"**Why Were No Findings Flagged?**\n\n"
                f"On this {view} X-ray, the model outputs for all 5 evaluated conditions were below their respective operating decision thresholds. "
                f"No prominent abnormal patterns were identified for those specific findings."
            )

        # 4. Finding-specific explanations (Atelectasis, Cardiomegaly, Consolidation, Edema, Pleural Effusion)
        for name, exp_data in FINDING_EXPLANATIONS.items():
            if name.lower() in q_lower:
                # Check if detected in this case
                matching_det = next((d for d in detected_findings if d["finding"].lower() == name.lower()), None)
                matching_eval = next((e for e in all_evaluated if (e.get("finding") or "").lower() == name.lower()), None)
                
                if is_prof:
                    prob_str = f"`{(matching_eval.get('probability') or 0):.3f}`" if matching_eval else "N/A"
                    thresh_str = f"`{(matching_eval.get('threshold') or 0):.3f}`" if matching_eval else "N/A"
                    status_str = "DETECTED / FLAGGED" if (matching_det or (matching_eval and matching_eval.get("detected"))) else "NOT FLAGGED (Below Threshold)"
                    return (
                        f"**Radiological Summary: {name}**\n\n"
                        f"• **Status on this {view} View:** {status_str}\n"
                        f"• **Model Output Score:** {prob_str} (Operating Decision Threshold: {thresh_str})\n"
                        f"• **Definition:** {exp_data.get('what_it_means')}\n"
                        f"• **Potential Differential Factors:** {', '.join(exp_data.get('possible_causes', []))}\n"
                        f"• **Clinical Note:** {exp_data.get('important')}"
                    )
                
                is_detected_here = bool(matching_det or (matching_eval and matching_eval.get("detected")))
                status_patient = "flagged for attention by the AI" if is_detected_here else "not flagged by the AI on this scan"
                return (
                    f"**{exp_data.get('title', name)}** ({status_patient}):\n\n"
                    f"• **What it means:** {exp_data.get('what_it_means')}\n"
                    f"• **Possible reasons:** {', '.join(exp_data.get('possible_causes', []))}\n"
                    f"• **Key takeaway:** {exp_data.get('important')} Please discuss with your doctor to understand what this means for your individual health."
                )

        # 5. "What did the AI find?" / "What was found?" / "Summary"
        if any(w in q_lower for w in ["what did the ai find", "what did we find", "what did you find", "what was found", "what is found", "summary", "result"]):
            if is_prof:
                if detected_count == 0:
                    return (
                        f"**Case Summary ({view} Radiograph):**\n\n"
                        f"0 of {context.get('findings_evaluated_count', 5)} evaluated acute findings exceeded operating decision thresholds. "
                        f"The study is negative for evaluated findings on this projection."
                    )
                det_summary = []
                for df in detected_findings:
                    p = (df.get("probability") or 0)
                    t = (df.get("threshold") or 0)
                    det_summary.append(f"• **{df['finding']}**: Output score `{p:.3f}` (Threshold `{t:.3f}`)")
                return (
                    f"**Case Summary ({view} Radiograph):**\n\n"
                    f"{detected_count} finding(s) exceeded operating decision thresholds:\n"
                    + "\n".join(det_summary) + "\n\n"
                    f"DenseNet121 feature activations indicate focal visual attention in corresponding anatomical zones."
                )
            
            if detected_count == 0:
                return (
                    f"**What Did the AI Find?**\n\n"
                    f"On your **{view}** chest X-ray, the AI evaluated 5 specific findings: *Atelectasis, Cardiomegaly, Consolidation, Edema, and Pleural Effusion*.\n\n"
                    f"**Result:** None of these 5 findings were flagged by the AI on this scan. "
                    f"No prominent abnormal visual patterns were detected for the evaluated conditions."
                )
            
            items = []
            for df in detected_findings:
                items.append(f"• **{df['finding']}**: {df.get('simple_explanation') or df.get('what_it_means') or 'Visual pattern flagged for clinical attention.'}")
            
            unflagged_names = [ef.get("finding") for ef in all_evaluated if not ef.get("detected") and ef.get("finding")]
            unflagged_text = f"\n\n**Findings Not Flagged ({len(unflagged_names)}):** {', '.join(unflagged_names)} were below detection thresholds." if unflagged_names else ""

            return (
                f"**What Did the AI Find?**\n\n"
                f"The AI flagged **{detected_count} finding(s)** for attention:\n\n"
                + "\n".join(items)
                + unflagged_text
                + "\n\n*Remember: AI detections point out visual patterns for doctor review and are not medical diagnoses.*"
            )

        # 6. Default general explanation
        if is_prof:
            return (
                f"**HC-XCDSS Clinical Context ({view} Projection):**\n\n"
                f"• **Evaluated Findings:** 5 conditions (Atelectasis, Cardiomegaly, Consolidation, Edema, Pleural Effusion)\n"
                f"• **Positive Detections:** {detected_count}\n"
                f"• **Architecture:** DenseNet-121 backbone with final norm5 layer Grad-CAM saliency mapping.\n"
                f"• **Guidance:** Output scores reflect model discriminative confidence and must be evaluated alongside clinical presentation."
            )

        if detected_count > 0:
            det_names = ", ".join(f["finding"] for f in detected_findings)
            return (
                f"Based on your **{view}** chest X-ray, the AI flagged **{det_names}** for your doctor's review. "
                f"You can ask me about specific findings, where the AI focused on the image, or questions to ask your doctor."
            )
        return (
            f"On your **{view}** chest X-ray, no findings were flagged among the 5 conditions evaluated. "
            f"Feel free to ask any questions about what the AI evaluated, how the analysis works, or questions for your doctor."
        )


# Backward-compatible alias
PatientAssistantService = AIAssistantService
