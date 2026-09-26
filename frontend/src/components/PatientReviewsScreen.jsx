import { useState } from "react";
import { cancelReview } from "../services/api";
import {
  Stethoscope,
  RotateCw,
  Plus,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";

export default function PatientReviewsScreen({
  reviews,
  loading,
  error,
  onOpenReviewDetail,
  onRefreshReviews,
  onNewAnalysis,
}) {
  const [cancellingId, setCancellingId] = useState(null);
  const [actionError, setActionError] = useState("");

  const handleCancel = async (e, reviewId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to cancel this review request?")) {
      return;
    }

    setCancellingId(reviewId);
    setActionError("");

    try {
      await cancelReview(reviewId);
      if (onRefreshReviews) {
        onRefreshReviews();
      }
    } catch (err) {
      console.error("Cancel review error:", err);
      setActionError(err.message || "Failed to cancel review request.");
    } finally {
      setCancellingId(null);
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
        return "status-tag status-requested";
      case "CANCELLED":
      case "DECLINED":
      case "EXPIRED":
        return "status-tag status-cancelled";
      default:
        return "status-tag";
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

  return (
    <section className="results-screen-container">
      {/* HEADER */}
      <div className="results-top-bar">
        <div>
          <div className="eyebrow" style={{ color: "var(--accent-primary)" }}>
            <Stethoscope size={12} />
            <span>PATIENT CONSULTATIONS</span>
          </div>
          <h2>My Doctor Reviews</h2>
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "2px" }}>
            Track and view independent clinical second opinions provided by verified healthcare professionals.
          </p>
        </div>

        <div className="results-actions-group">
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={onRefreshReviews}
            disabled={loading}
          >
            <RotateCw size={13} className={loading ? "spinner" : ""} />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            className="btn-primary btn-sm"
            onClick={onNewAnalysis}
          >
            <Plus size={13} />
            <span>New Analysis</span>
          </button>
        </div>
      </div>

      {actionError && (
        <div className="validation-error-card">
          <div className="val-error-header">
            <AlertTriangle size={15} />
            <span>{actionError}</span>
          </div>
        </div>
      )}

      {error && (
        <div className="validation-error-card">
          <div className="val-error-header">
            <AlertTriangle size={15} />
            <span>{error}</span>
          </div>
        </div>
      )}

      {loading && reviews.length === 0 && (
        <div className="dashboard-stats-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="stat-card" style={{ height: "100px", opacity: 0.6 }} />
          ))}
        </div>
      )}

      {!loading && reviews.length === 0 && !error && (
        <div className="dashboard-empty-card">
          <div className="empty-card-icon">
            <Stethoscope size={24} />
          </div>
          <h3>No Review Requests Yet</h3>
          <p>
            When you request a professional second opinion from an X-ray analysis result, it will appear here.
          </p>
          <button
            type="button"
            className="btn-primary"
            onClick={onNewAnalysis}
            style={{ marginTop: "8px" }}
          >
            <Plus size={14} />
            <span>Start an Analysis</span>
          </button>
        </div>
      )}

      {reviews.length > 0 && (
        <div className="dashboard-active-reviews-grid">
          {reviews.map((rev) => {
            const canCancel = ["REQUESTED", "ASSIGNED", "ACCEPTED", "IN_REVIEW"].includes(rev.status);

            return (
              <div
                key={rev.id}
                className="dashboard-active-review-card"
                onClick={() => onOpenReviewDetail(rev.id)}
              >
                <div className="card-top-row">
                  <span className="review-ref-tag">{formatCaseId(rev.id)}</span>
                  <span className={getStatusBadgeClass(rev.status)}>{rev.status}</span>
                </div>

                <div className="doctor-matching-info">
                  <div className="doc-avatar-icon">
                    <Stethoscope size={16} />
                  </div>
                  <div className="doc-matching-text">
                    <strong>
                      {rev.professional?.full_name || "Assigned Specialist (In Queue)"}
                    </strong>
                    <p>
                      {rev.professional?.specialty || "General / Thoracic Radiology"}
                      {rev.professional?.location_city ? ` • ${rev.professional.location_city}` : ""}
                    </p>
                  </div>
                </div>

                {rev.patient_message && (
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
                    <p style={{ fontStyle: "italic", marginTop: "2px" }}>"{rev.patient_message}"</p>
                  </div>
                )}

                <div className="review-card-meta-line">
                  <span>Requested {formatDate(rev.requested_at || rev.created_at)}</span>
                  {rev.completed_at && (
                    <span style={{ color: "var(--color-success)", fontWeight: "600" }}>
                      Completed {formatDate(rev.completed_at)}
                    </span>
                  )}
                </div>

                <div className="card-action-footer">
                  <span className="btn-view-active-review">
                    {rev.status === "COMPLETED" ? "View Assessment →" : "View Details →"}
                  </span>

                  {canCancel && (
                    <button
                      type="button"
                      className="btn-danger btn-sm"
                      onClick={(e) => handleCancel(e, rev.id)}
                      disabled={cancellingId === rev.id}
                    >
                      {cancellingId === rev.id ? "Cancelling..." : "Cancel"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
