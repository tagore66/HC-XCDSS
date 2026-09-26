"""
HC-XCDSS Notification Channels (In-App, Email, Push abstraction)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..db.models.notification import Notification


class NotificationChannel(ABC):
    """
    Abstract notification delivery channel.
    """

    @abstractmethod
    def deliver(self, notification: Notification) -> bool:
        """
        Deliver notification to destination channel.
        """
        pass


class InAppNotificationChannel(NotificationChannel):
    """
    In-App persistence channel (default active channel).
    """

    def deliver(self, notification: Notification) -> bool:
        # In-app notifications are stored directly in SQLite
        return True


class EmailNotificationChannel(NotificationChannel):
    """
    Future email notification provider (stub for future SMTP/SendGrid integration).
    """

    def deliver(self, notification: Notification) -> bool:
        # Non-blocking stub
        return True
