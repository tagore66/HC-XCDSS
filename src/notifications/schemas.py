"""
HC-XCDSS Notification Pydantic Schemas
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from ..db.models.notification import NotificationType, NotificationEntityType


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: NotificationType
    title: str
    message: str
    entity_type: NotificationEntityType
    entity_id: str
    is_read: bool
    created_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    notifications: List[NotificationResponse]


class UnreadCountResponse(BaseModel):
    count: int
