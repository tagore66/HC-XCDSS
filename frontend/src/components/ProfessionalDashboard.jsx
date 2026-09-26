import { useState, useEffect } from "react";
import { acceptReview } from "../services/api";
import {
  Stethoscope,
  RotateCw,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  User,
  Inbox,
  FileCheck,
} from "lucide-react";

export default function ProfessionalDashboard({
  currentUser,
  reviews = [],
  loading,
  error,
  onOpenReview,
  onRefresh,
}) {
  const [activeTab, setActiveTab] = useState("available"); // "available" or "assigned"
  const [acceptingId, setAcceptingId] = useState(null);
  const [actionError, setActionError] = useState("");

  // Automatically refresh server queue whenever dashboard mounts or returns to view
  useEffect(() => {
    if (onRefresh) {
      onRefresh();
    }
  }, []);

  // Available Requests: genuinely unassigned pool requests where professional_id is null/absent and status is REQUESTED or MATCHING
  const availableRequests = (reviews || []).filter(
    (r) => !r.professional_id && ["REQUESTED", "MATCHING"].includes(r.status)
  );

  // My Active & Completed Reviews: requests assigned to the logged-in professional with ASSIGNED, ACCEPTED, IN_REVIEW, or COMPLETED
  const myReviews = (reviews || []).filter(
    (r) =>
      Boolean(r.professional_id) &&
      (currentUser?.id ? r.professional_id === currentUser.id : true) &&
      ["ASSIGNED", "ACCEPTED", "IN_REVIEW", "COMPLETED"].includes(r.status)
  );

  const handleAcceptAndOpen = async (reviewId) => {
    setAcceptingId(reviewId);
    setActionError("");
    try {
      await acceptReview(reviewId);
      if (onRefresh) {
        await onRefresh();
      }
      onOpenReview(reviewId);
    } catch (err) {
      console.error("Failed to accept review:", err);
      setActionError(err.message || "Failed to accept review request.");
    } finally {
      setAcceptingId(null);
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case "COMPLETED":
        return "status-tag status-completed";
      case "IN_REVIEW":
        return "status-tag status-in-review";
      case "ACCEPTED":
      case "ASSIGNED":
        return "status-tag status-accepted";
      case "REQUESTED":
      case "MATCHING":
        return "status-tag status-requested";
      default:
        return "status-tag status-cancelled";
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return "—";
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  function formatCaseId(id) {
    if (!id) return "—";
    const clean = String(id).replace(/^#/, "");
    return `Case #${clean.substring(0, 8).toUpperCase()}`;
  }

  const doctorName = currentUser?.display_name || currentUser?.full_name || "Specialist";

  return (
    <div className="patient-dashboard-container">
      {/* HEADER */}
      <div className="dashboard-welcome-header">
        <div className="welcome-text-block">
          <div className="eyebrow" style={{ color: "var(--accent-primary)" }}>
            <Stethoscope size={12} />
            <span>PHYSICIAN CLINICAL CONSOLE</span>
          </div>
          <h1 className="welcome-title">Good morning, Dr. {doctorName}</h1>
          <p className="welcome-subtitle">
            Review chest radiograph queues, inspect DenseNet121 inferences, and author verified clinical second opinions.
          </p>
        </div>

        <div className="dashboard-header-actions">
          <button
            type="button"
            className="btn-dashboard-refresh"
            onClick={onRefresh}
            disabled={loading || !!acceptingId}
          >
            <RotateCw size={13} className={loading ? "spinner" : ""} />
            <span>{loading ? "Refreshing..." : "Refresh Queue"}</span>
          </button>
        </div>
      </div>

      {actionError && (
        <div className="validation-error-card" role="alert">
          <div className="val-error-header">
            <AlertTriangle size={15} />
            <span>{actionError}</span>
          </div>
        </div>
      )}

      {error && (
        <div className="validation-error-card" role="alert">
          <div className="val-error-header">
            <AlertTriangle size={15} />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Segmented Tab Bar */}
      <div className="portal-tab-bar">
        <button
          type="button"
          className={`portal-tab ${activeTab === "available" ? "active" : ""}`}
          onClick={() => setActiveTab("available")}
        >
          <Inbox size={14} style={{ display: "inline-block", marginRight: "6px" }} />
          <span>Available Requests ({availableRequests.length})</span>
        </button>
        <button
          type="button"
          className={`portal-tab ${activeTab === "assigned" ? "active" : ""}`}
          onClick={() => setActiveTab("assigned")}
        >
          <FileCheck size={14} style={{ display: "inline-block", marginRight: "6px" }} />
          <span>My Active & Completed Reviews ({myReviews.length})</span>
        </button>
      </div>

      {loading && reviews.length === 0 && (
        <div className="dashboard-stats-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="stat-card" style={{ height: "100px", opacity: 0.6 }} />
          ))}
        </div>
      )}

      {/* Available Requests Tab */}
      {activeTab === "available" && (
        <div className="reviews-queue-container">
          {!loading && availableRequests.length === 0 && (
            <div className="dashboard-empty-card">
              <div className="empty-card-icon">
                <CheckCircle2 size={24} />
              </div>
              <h3>No Pending Available Requests</h3>
              <p>All open review requests are currently assigned or completed.</p>
            </div>
          )}

          {availableRequests.length > 0 && (
            <div className="dashboard-active-reviews-grid">
              {availableRequests.map((req) => {
                const isAccepting = acceptingId === req.id;
                return (
                  <div
                    key={req.id}
                    className="dashboard-active-review-card"
                    onClick={() => !acceptingId && handleAcceptAndOpen(req.id)}
                  >
                    <div className="card-top-row">
                      <span className="review-ref-tag">{formatCaseId(req.id)}</span>
                      <span className={getStatusBadgeClass(req.status)}>{req.status}</span>
                    </div>

                    <div style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                      <span style={{ color: "var(--text-muted)" }}>Radiograph: </span>
                      <strong>{formatCaseId(req.analysis_id)}</strong>
                    </div>

                    {req.patient_message && (
                      <div style={{
                        padding: "8px 10px",
                        background: "var(--surface-primary)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: "12px",
                        color: "var(--text-secondary)",
                      }}>
                        <span style={{ fontWeight: "600", display: "block", fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" }}>
                          Patient Note:
                        </span>
                        <p style={{ fontStyle: "italic", marginTop: "2px" }}>"{req.patient_message}"</p>
                      </div>
                    )}

                    <div className="review-card-meta-line">
                      <span>Requested {formatDate(req.requested_at || req.created_at)}</span>
                    </div>

                    <div className="card-action-footer">
                      <button
                        type="button"
                        className="btn-primary btn-sm"
                        style={{ width: "100%" }}
                        disabled={!!acceptingId}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAcceptAndOpen(req.id);
                        }}
                      >
                        {isAccepting ? (
                          <>
                            <span className="spinner" />
                            <span>Accepting Case...</span>
                          </>
                        ) : (
                          <>
                            <span>Accept Case & Open Workspace</span>
                            <ArrowRight size={13} />
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* My Reviews Tab */}
      {activeTab === "assigned" && (
        <div className="reviews-queue-container">
          {!loading && myReviews.length === 0 && (
            <div className="dashboard-empty-card">
              <div className="empty-card-icon">
                <FileCheck size={24} />
              </div>
              <h3>No Assigned Reviews</h3>
              <p>Accept an open request from the Available Requests tab to start an evaluation.</p>
            </div>
          )}

          {myReviews.length > 0 && (
            <div className="dashboard-active-reviews-grid">
              {myReviews.map((req) => (
                <div
                  key={req.id}
                  className="dashboard-active-review-card"
                  onClick={() => onOpenReview(req.id)}
                >
                  <div className="card-top-row">
                    <span className="review-ref-tag">{formatCaseId(req.id)}</span>
                    <span className={getStatusBadgeClass(req.status)}>{req.status}</span>
                  </div>

                  <div style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                    <span style={{ color: "var(--text-muted)" }}>Radiograph: </span>
                    <strong>{formatCaseId(req.analysis_id)}</strong>
                  </div>

                  {req.patient_message && (
                    <div style={{
                      padding: "8px 10px",
                      background: "var(--surface-primary)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "var(--radius-sm)",
                      fontSize: "12px",
                      color: "var(--text-secondary)",
                    }}>
                      <span style={{ fontWeight: "600", display: "block", fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" }}>
                        Patient Note:
                      </span>
                      <p style={{ fontStyle: "italic", marginTop: "2px" }}>"{req.patient_message}"</p>
                    </div>
                  )}

                  <div className="review-card-meta-line">
                    <span>Updated {formatDate(req.updated_at || req.created_at)}</span>
                    {req.completed_at && (
                      <span style={{ color: "var(--color-success)", fontWeight: "600" }}>
                        Completed {formatDate(req.completed_at)}
                      </span>
                    )}
                  </div>

                  <div className="card-action-footer">
                    <button type="button" className="btn-secondary btn-sm" style={{ width: "100%" }}>
                      <span>Open Workspace</span>
                      <ArrowRight size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
