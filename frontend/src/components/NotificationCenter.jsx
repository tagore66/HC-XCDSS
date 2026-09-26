import { useState, useEffect } from "react";
import {
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead,
  deleteNotification,
} from "../services/api";
import {
  Bell,
  CheckCheck,
  X,
  Trash2,
  Inbox,
  Clock,
  CheckCircle2,
} from "lucide-react";

export default function NotificationCenter({
  isOpen,
  onClose,
  onNavigateToEntity,
  onUnreadCountChange,
}) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadNotifications = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getNotifications(30, 0);
      setNotifications(data.notifications || []);
      if (onUnreadCountChange) {
        onUnreadCountChange(data.unread_count || 0);
      }
    } catch (err) {
      setError(err.message || "Failed to load notifications.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadNotifications();
    }
  }, [isOpen]);

  const handleMarkRead = async (e, notif) => {
    e.stopPropagation();
    try {
      await markNotificationRead(notif.id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
      );
      if (onUnreadCountChange) {
        const remaining = notifications.filter((n) => !n.is_read && n.id !== notif.id).length;
        onUnreadCountChange(remaining);
      }
    } catch (err) {
      console.error("Mark read error:", err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      if (onUnreadCountChange) {
        onUnreadCountChange(0);
      }
    } catch (err) {
      console.error("Mark all read error:", err);
    }
  };

  const handleDelete = async (e, notifId) => {
    e.stopPropagation();
    try {
      await deleteNotification(notifId);
      const updated = notifications.filter((n) => n.id !== notifId);
      setNotifications(updated);
      if (onUnreadCountChange) {
        const remaining = updated.filter((n) => !n.is_read).length;
        onUnreadCountChange(remaining);
      }
    } catch (err) {
      console.error("Delete notification error:", err);
    }
  };

  const handleNotificationClick = async (notif) => {
    if (!notif.is_read) {
      try {
        await markNotificationRead(notif.id);
      } catch {}
    }
    if (onNavigateToEntity) {
      onNavigateToEntity(notif.entity_type, notif.entity_id);
    }
    if (onClose) onClose();
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "absolute",
        top: "44px",
        right: "0",
        width: "360px",
        maxHeight: "480px",
        background: "var(--surface-primary)",
        border: "1px solid var(--border-main)",
        borderRadius: "var(--radius-xl)",
        boxShadow: "var(--shadow-modal)",
        zIndex: 150,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        animation: "modalFadeIn 150ms ease",
      }}
      onClick={(e) => e.stopPropagation()}
    >
      <div style={{
        padding: "12px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        borderBottom: "1px solid var(--border-subtle)",
        background: "var(--surface-secondary)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Bell size={14} color="var(--accent-primary)" />
          <h3 style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-primary)" }}>
            Activity & Notifications
          </h3>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {notifications.some((n) => !n.is_read) && (
            <button
              type="button"
              onClick={handleMarkAllRead}
              style={{ fontSize: "11px", fontWeight: "600", color: "var(--accent-primary)" }}
            >
              Mark all read
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            style={{ color: "var(--text-muted)", display: "flex", alignItems: "center" }}
            aria-label="Close notifications"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      <div style={{ overflowY: "auto", maxHeight: "400px", padding: "8px" }}>
        {loading && notifications.length === 0 ? (
          <div style={{ padding: "20px", textAlign: "center", fontSize: "12px", color: "var(--text-muted)" }}>
            Loading activity...
          </div>
        ) : error ? (
          <div style={{ padding: "14px", color: "var(--color-danger-text)", fontSize: "12px" }}>
            {error}
          </div>
        ) : notifications.length === 0 ? (
          <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
            <Inbox size={24} style={{ margin: "0 auto 6px", opacity: 0.5 }} />
            <p>No new notifications.</p>
          </div>
        ) : (
          notifications.map((notif) => (
            <div
              key={notif.id}
              onClick={() => handleNotificationClick(notif)}
              style={{
                padding: "10px 12px",
                borderRadius: "var(--radius-md)",
                background: notif.is_read ? "transparent" : "var(--accent-light)",
                border: "1px solid",
                borderColor: notif.is_read ? "transparent" : "var(--accent-light-border)",
                marginBottom: "4px",
                cursor: "pointer",
                transition: "all var(--transition-fast)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
                <strong style={{ fontSize: "12px", color: "var(--text-primary)" }}>{notif.title}</strong>
                <span style={{ fontSize: "10px", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                  {notif.created_at
                    ? new Date(notif.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                    : ""}
                </span>
              </div>
              <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: "3px 0 6px", lineHeight: "1.4" }}>
                {notif.message}
              </p>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="status-tag" style={{ fontSize: "9px", padding: "1px 6px" }}>
                  {notif.entity_type}
                </span>

                <div style={{ display: "flex", gap: "6px" }}>
                  {!notif.is_read && (
                    <button
                      type="button"
                      onClick={(e) => handleMarkRead(e, notif)}
                      style={{ fontSize: "10px", color: "var(--accent-primary)", fontWeight: "600" }}
                    >
                      Mark read
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={(e) => handleDelete(e, notif.id)}
                    style={{ color: "var(--text-muted)" }}
                    title="Dismiss"
                  >
                    <X size={11} />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
