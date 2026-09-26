"""
HC-XCDSS AI Context & Conversation Database Models
"""

import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..base import Base


class AIContext(Base):
    __tablename__ = "ai_contexts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    analysis_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    context_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis = relationship(
        "Analysis",
        back_populates="ai_context",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "context_data": self.context_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    analysis_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="patient",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis = relationship(
        "Analysis",
        back_populates="conversations",
    )
    user = relationship(
        "User",
        back_populates="conversations",
    )
    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at.asc()",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "user_id": self.user_id,
            "role": self.role,
            "messages": [m.to_dict() for m in self.messages] if self.messages else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender: Mapped[str] = mapped_column(
        String(16),  # 'user' or 'model'
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    provider: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    safety_status: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        default="ok",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    conversation = relationship(
        "Conversation",
        back_populates="messages",
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender": self.sender,
            "content": self.content,
            "provider": self.provider,
            "model": self.model,
            "safety_status": self.safety_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
