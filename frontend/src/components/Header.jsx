import { useState, useEffect } from "react";
import { getUnreadCount } from "../services/api";
import NotificationCenter from "./NotificationCenter";
import {
  Activity,
  Plus,
  Clock,
  Stethoscope,
  Shield,
  Bell,
  LogOut,
  User,
  CheckCircle2,
} from "lucide-react";

/**
 * Application Header component.
 * Displays brand, navigation triggers, authenticated user account status, and Activity/Notification Center.
 */
export default function Header({
  activeScreen,
  onNavigate,
  loading,
  currentUser,
  onOpenAuth,
  onLogout,
  onNavigateToEntity,
}) {
  const [showNotifs, setShowNotifs] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const isProfessional =
    currentUser?.role === "PROFESSIONAL" &&
    currentUser?.professional_profile?.verification_status === "VERIFIED";

  // Fetch unread count when user is logged in
  const fetchUnread = async () => {
    if (!currentUser) {
      setUnreadCount(0);
      return;
    }
    try {
      const data = await getUnreadCount();
      setUnreadCount(data.count || 0);
    } catch {
      // Non-fatal unread count check
    }
  };

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000); // 30s gentle refresh
    return () => clearInterval(interval);
  }, [currentUser]);

  const handleBrandClick = () => {
    if (!currentUser) {
      onNavigate("landing");
    } else if (currentUser.role === "ADMIN") {
      onNavigate("admin-verification");
    } else if (currentUser.role === "PROFESSIONAL") {
      onNavigate(isProfessional ? "pro-dashboard" : "pro-pending");
    } else {
      onNavigate("dashboard");
    }
  };

  return (
    <header className="header">
      <div className="brand" onClick={handleBrandClick} style={{ cursor: "pointer" }}>
        <div className="brand-mark">
          <Activity size={18} />
        </div>
        <div className="brand-title-wrap">
          <h1>HC-XCDSS</h1>
          <p>Clinical Decision Support</p>
        </div>
      </div>

      <div className="header-actions">
        {currentUser && (
          <nav className="header-nav">
            {currentUser.role === "PATIENT" && (
              <>
                <button
                  type="button"
                  className={`nav-link-btn ${activeScreen === "dashboard" ? "active" : ""}`}
                  onClick={() => onNavigate("dashboard")}
                  disabled={loading}
                >
                  <Activity size={14} />
                  <span>Dashboard</span>
                </button>

                <button
                  type="button"
                  className={`nav-link-btn ${activeScreen === "upload" || activeScreen === "result" ? "active" : ""}`}
                  onClick={() => onNavigate("upload")}
                  disabled={loading}
                >
                  <Plus size={14} />
                  <span>New Analysis</span>
                </button>

                <button
                  type="button"
                  className={`nav-link-btn ${activeScreen === "history" ? "active" : ""}`}
                  onClick={() => onNavigate("history")}
                  disabled={loading}
                >
                  <Clock size={14} />
                  <span>History</span>
                </button>

                <button
                  type="button"
                  className={`nav-link-btn ${activeScreen === "reviews" || activeScreen === "review-detail" ? "active" : ""}`}
                  onClick={() => onNavigate("reviews")}
                  disabled={loading}
                >
                  <Stethoscope size={14} />
                  <span>Doctor Reviews</span>
                </button>
              </>
            )}

            {currentUser.role === "ADMIN" && (
              <>
                <button
                  type="button"
                  className={`nav-link-btn ${activeScreen === "admin-verification" ? "active" : ""}`}
                  onClick={() => onNavigate("admin-verification")}
                  disabled={loading}
                  style={{ fontWeight: "600" }}
                >
                  <Shield size={14} />
                  <span>Verification Admin</span>
                </button>
                <button
                  type="button"
                  className={`nav-link-btn ${activeScreen === "upload" || activeScreen === "result" ? "active" : ""}`}
                  onClick={() => onNavigate("upload")}
                  disabled={loading}
                >
                  <Plus size={14} />
                  <span>New Analysis</span>
                </button>
              </>
            )}

            {currentUser.role === "PROFESSIONAL" && (
              isProfessional ? (
                <button
                  type="button"
                  className={`nav-link-btn pro-portal-btn ${activeScreen === "pro-dashboard" || activeScreen === "pro-review" ? "active" : ""}`}
                  onClick={() => onNavigate("pro-dashboard")}
                  disabled={loading}
                >
                  <Stethoscope size={14} />
                  <span>Physician Portal</span>
                </button>
              ) : (
                <button
                  type="button"
                  className={`nav-link-btn ${activeScreen === "pro-pending" ? "active" : ""}`}
                  onClick={() => onNavigate("pro-pending")}
                  disabled={loading}
                  style={{ background: "var(--color-warning-bg)", color: "var(--color-warning-text)", fontWeight: "600", border: "1px solid var(--color-warning-border)" }}
                >
                  <Clock size={14} />
                  <span>Verification Status</span>
                </button>
              )
            )}
          </nav>
        )}

        {/* Activity & Notification Bell */}
        {currentUser && (
          <div className="header-notif-wrapper" style={{ position: "relative" }}>
            <button
              type="button"
              className="btn-notif-bell"
              onClick={() => setShowNotifs((prev) => !prev)}
              title="Notifications & Activity"
            >
              <Bell size={16} />
              {unreadCount > 0 && (
                <span className="notif-badge">{unreadCount > 99 ? "99+" : unreadCount}</span>
              )}
            </button>

            <NotificationCenter
              isOpen={showNotifs}
              onClose={() => setShowNotifs(false)}
              onNavigateToEntity={onNavigateToEntity}
              onUnreadCountChange={(cnt) => setUnreadCount(cnt)}
            />
          </div>
        )}

        <div className="user-auth-controls">
          {currentUser ? (
            <div className="user-badge-menu">
              <div className="user-identity-chip">
                <div className="user-avatar-circle">
                  <User size={12} />
                </div>
                <span className="user-display-name">
                  {currentUser.display_name || currentUser.full_name || (currentUser.role === "PROFESSIONAL" ? "Dr. Specialist" : "Patient")}
                </span>
                {currentUser.username && (
                  <span className="user-username-handle">@{currentUser.username}</span>
                )}
                <span className={`user-role-badge badge-${currentUser.role?.toLowerCase()}`}>
                  {currentUser.role === "PROFESSIONAL" ? "Physician" : currentUser.role === "ADMIN" ? "Admin" : "Patient"}
                </span>
              </div>
              <button
                type="button"
                className="btn-logout"
                onClick={onLogout}
                title="Sign out"
              >
                <LogOut size={14} />
              </button>
            </div>
          ) : (
            <div className="guest-header-buttons">
              <button
                type="button"
                className="btn-header-signin"
                onClick={() => onOpenAuth("login")}
              >
                Sign In
              </button>
              <button
                type="button"
                className="btn-header-register"
                onClick={() => onOpenAuth("register", "PATIENT")}
              >
                Create Account
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
