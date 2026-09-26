"""
HC-XCDSS Mock LLM Provider for Local Development and Testing
"""

from typing import List, Dict, Any, Optional
from .base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic Mock LLM Provider for local development, testing, and CI without external API dependencies.
    """

    def __init__(self, model_name: str = "mock-decision-support-v1"):
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_configured(self) -> bool:
        return True

    def generate_response(
        self,
        system_instruction: str,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Generates deterministic, context-aware responses based on system instruction and prompt.
        """
        is_pro = "HEALTHCARE PROFESSIONAL AUDIENCE" in system_instruction or "PROFESSIONAL" in system_instruction
        
        # Extract user question from prompt (format: "USER QUESTION: <question>\n\n")
        user_question_part = prompt
        if "USER QUESTION:" in prompt:
            user_question_part = prompt.split("USER QUESTION:", 1)[1]
            if "\n\nPlease provide" in user_question_part:
                user_question_part = user_question_part.split("\n\nPlease provide", 1)[0]
        
        q_lower = user_question_part.lower().strip()

        # Parse specific questions from extracted query
        if "is that definitely what i have" in q_lower or "definitely" in q_lower:
            if is_pro:
                text = (
                    "No. DenseNet121 predictions represent probabilistic pattern associations based on CheXpert training. "
                    "Positive findings require direct radiologist or attending physician verification and must not be treated as a definitive diagnosis."
                )
            else:
                text = (
                    "No, this is not a definite diagnosis. The HC-XCDSS AI identifies visual patterns in your chest X-ray "
                    "and calculates probabilities to help healthcare professionals. Only a licensed doctor can provide a medical diagnosis."
                )
        elif "what does pneumonia mean" in q_lower or "pneumonia" in q_lower:
            if is_pro:
                text = (
                    "In this chest radiograph analysis, Pneumonia was evaluated using DenseNet121. "
                    "Radiological presentation typically manifests as airspace opacity, consolidation, or air bronchograms. "
                    "Model activation (Grad-CAM) focuses on areas of localized parenchymal attenuation. "
                    "Clinical correlation with auscultation, inflammatory markers, and patient vitals is advised."
                )
            else:
                text = (
                    "Pneumonia is an infection in one or both lungs where the air sacs may fill with fluid or pus. "
                    "In this X-ray, the AI evaluated visual patterns that can indicate lung inflammation. "
                    "This is an automated finding to assist your doctor, not a definitive diagnosis. "
                    "Please discuss these results with your healthcare provider."
                )
        elif "what should i ask my doctor" in q_lower or "ask my doctor" in q_lower:
            if is_pro:
                text = (
                    "Suggested clinical consultation points: 1. Evaluate correlation between flagged radiological zones and patient physical findings. "
                    "2. Determine if follow-up high-resolution imaging or laboratory cultures are warranted."
                )
            else:
                text = (
                    "Here are helpful questions you can ask your doctor:\n"
                    "1. 'Does the visual pattern flagged on my X-ray match my current symptoms?'\n"
                    "2. 'Do you recommend any additional tests or follow-up imaging?'\n"
                    "3. 'What next steps or treatments are appropriate for my condition?'"
                )
        elif "grad-cam" in q_lower or "heatmap" in q_lower:
            if is_pro:
                text = (
                    "Grad-CAM (Gradient-weighted Class Activation Mapping) computes the gradients of the target class score "
                    "with respect to the final convolutional layer (norm5). The resulting heatmaps visualize regions that most "
                    "strongly influenced the model classification logits."
                )
            else:
                text = (
                    "Grad-CAM heatmaps are color-coded overlays on your chest X-ray. The warmer colors (red and yellow) show "
                    "which areas of the image the AI looked at most when analyzing your scan. They are explanations of the AI's "
                    "focus, not disease maps."
                )
        else:
            if is_pro:
                text = (
                    "Analysis Context Summary: Model evaluated chest radiograph features against view-specific operating thresholds. "
                    "All findings, probabilities, and Grad-CAM activations are intended for clinical decision support."
                )
            else:
                text = (
                    "Based on your chest X-ray report, HC-XCDSS analyzed several common lung and heart conditions. "
                    "If you have specific questions about detected findings or next steps, your doctor can provide personalized guidance."
                )

        return {
            "text": text,
            "provider": self.provider_name,
            "model": self.model_name,
        }
