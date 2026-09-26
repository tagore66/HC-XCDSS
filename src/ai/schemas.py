"""
HC-XCDSS AI Assistant Schemas
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "model", "assistant", "patient", "professional"]
    content: str


class AssistantMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User question about the analysis")
    role: Optional[str] = Field(None, description="Audience role: 'patient' or 'professional' (overridden by auth identity when authenticated)")
    conversation_id: Optional[str] = Field(None, description="Optional existing conversation ID to continue a thread")
    conversation_history: Optional[List[ChatMessage]] = Field(default_factory=list, description="Optional previous chat turns")


class AssistantMessageResponse(BaseModel):
    analysis_id: str
    conversation_id: Optional[str] = None
    role: str
    answer: str
    safety_notice: str
    provider: str
    model: str
    safety_status: str = "ok"
    flags: List[str] = Field(default_factory=list)
