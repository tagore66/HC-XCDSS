import { useState, useEffect } from "react";
import { getPatientDashboard } from "../services/api";
import {
  Activity,
  Plus,
  Clock,
  Stethoscope,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  ArrowRight,
  ShieldCheck,
  FileText,
  ChevronRight,
} from "lucide-react";

/**
 * Patient-friendly status badge mapping
 */
function getPatientStatusInfo(status) {
  switch (status) {
    case "REQUESTED":
      return {
        label: "Awaiting Specialist",
        className: "patient-status-pill status-requested",
      };
    case "ASSIGNED":
      return {
        label: "Specialist Assigned",
        className: "patient-status-pill status-assigned",
      };
    case "IN_REVIEW":
      return {
        label: "Under Clinical Review",
        className: "patient-status-pill status-in-review",
      };
    case "ACCEPTED":
      return {
        label: "Review Scheduled",
        className: "patient-status-pill status-accepted",
      };
    case "COMPLETED":
      return {
        label: "Review Completed",
        className: "patient-status-pill status-completed",
      };
    case "CANCELLED":
      return {
        label: "Cancelled",
        className: "patient-status-pill status-cancelled",
      };
    case "DECLINED":
      return {
        label: "Reassignment Pending",
        className: "patient-status-pill status-declined",
      };
    default:
      return {
        label: status || "Pending",
        className: "patient-status-pill",
      };
  }
}

function formatDate(isoString) {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    if (Number.isNaN(d.getTime())) return isoString;
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return isoString;
  }
}

function formatCaseId(id) {
  if (!id) return "—";
  const clean = String(id).replace(/^#/, "");
  return `Case #${clean.substring(0, 8).toUpperCase()}`;
}

export default function PatientDashboard({
  currentUser,
  onNewAnalysis,
  onOpenAnalysis,
  onOpenReviewDetail,
  onViewAllHistory,
  onViewAllReviews,
}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const fetchDashboard = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    else setLoading(true);
    setError("");

    try {
      const dashboardData = await getPatientDashboard();
      setData(dashboardData);
    } catch (err) {
      console.error("Patient Dashboard load error:", err);
      setError("Unable to load your dashboard right now. Please check your connection.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const patientName = currentUser?.display_name || currentUser?.full_name || data?.user?.full_name || "Patient";
  const stats = data?.stats || {
    total_analyses: 0,
    active_reviews_count: 0,
    completed_reviews_count: 0,
    unread_notifications_count: 0,
  };
  const recentAnalyses = data?.recent_analyses || [];
  const activeReviews = data?.active_reviews || [];
  const completedReviews = data?.completed_reviews || [];

  return (
    <div className="patient-dashboard-container">
      {/* 1. WELCOME HEADER */}
      <div className="dashboard-welcome-header">
        <div className="welcome-text-block">
          <div className="eyebrow">
            <Activity size={12} />
            <span>PERSONAL CLINICAL WORKSPACE</span>
          </div>
          <h1 className="welcome-title">Good morning, {patientName}</h1>
          <p className="welcome-subtitle">
            Review your recent chest X-ray analyses and verified professional reports.
          </p>
        </div>

        <div className="dashboard-header-actions">
          <button
            type="button"
            className="btn-dashboard-refresh"
            onClick={() => fetchDashboard(true)}
            disabled={loading || refreshing}
            title="Refresh dashboard data"
          >
            <RotateCw size={13} className={refreshing ? "spinner" : ""} />
            <span>{refreshing ? "Refreshing..." : "Refresh"}</span>
          </button>
        </div>
      </div>

      {/* ERROR STATE */}
      {error && (
        <div className="validation-error-card" role="alert" style={{ background: "var(--color-danger-bg)", borderColor: "var(--color-danger-border)", color: "var(--color-danger-text)" }}>
          <div className="val-error-header" style={{ color: "var(--color-danger-text)" }}>
            <AlertTriangle size={16} />
            <strong>Unable to load your dashboard</strong>
          </div>
          <p className="val-error-desc" style={{ color: "var(--color-danger-text)" }}>{error}</p>
          <button
            type="button"
            className="btn-secondary btn-sm"
            onClick={() => fetchDashboard(false)}
            style={{ marginTop: "6px" }}
          >
            Try Again
          </button>
        </div>
      )}

      {/* LOADING SKELETON */}
      {loading && !data && (
        <div className="dashboard-stats-grid">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="stat-card" style={{ height: "80px", opacity: 0.6 }} />
          ))}
        </div>
      )}

      {/* DASHBOARD CONTENT */}
      {!loading && data && (
        <>
          {/* 2. ASYMMETRIC PRIMARY HERO + METRIC SNAPSHOT */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "1.4fr 1fr",
            gap: "16px",
          }}>
            {/* Left: Large New Analysis Hero Card */}
            <div className="patient-hero-card">
              <div>
                <div className="eyebrow" style={{ color: "var(--accent-primary)", marginBottom: "8px" }}>
                  <Plus size={13} />
                  <span>DENSENET121 &amp; GRAD-CAM</span>
                </div>
                <h2 style={{ fontSize: "20px", fontWeight: "700", letterSpacing: "-0.3px", marginBottom: "6px", color: "var(--text-primary)" }}>
                  Analyze a Chest X-Ray
                </h2>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5", maxWidth: "460px" }}>
                  Upload a radiograph to receive automated CheXpert findings, view-specific threshold evaluations, and Grad-CAM visual explainability.
                </p>
              </div>

              <div style={{ marginTop: "20px" }}>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={onNewAnalysis}
                  style={{
                    padding: "10px 20px",
                  }}
                >
                  <Plus size={15} />
                  <span>Start New Analysis</span>
                </button>
              </div>
            </div>

            {/* Right: Compact System Snapshot Grid */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
            }}>
              <div className="stat-card" style={{ flexDirection: "column", alignItems: "flex-start", gap: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
                  <span className="stat-label">Analyses</span>
                  <div className="stat-icon-wrap" style={{ width: "28px", height: "28px", fontSize: "14px" }}>
                    <Activity size={14} />
                  </div>
                </div>
                <span className="stat-value">{stats.total_analyses}</span>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Total completed</span>
              </div>

              <div className="stat-card" style={{ flexDirection: "column", alignItems: "flex-start", gap: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
                  <span className="stat-label">Doctor Reviews</span>
                  <div className="stat-icon-wrap" style={{ width: "28px", height: "28px", fontSize: "14px" }}>
                    <CheckCircle2 size={14} />
                  </div>
                </div>
                <span className="stat-value">{stats.completed_reviews_count}</span>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Verified assessments</span>
              </div>

              <div className="stat-card" style={{ flexDirection: "column", alignItems: "flex-start", gap: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
                  <span className="stat-label">Pending</span>
                  <div className="stat-icon-wrap" style={{ width: "28px", height: "28px", fontSize: "14px" }}>
                    <Clock size={14} />
                  </div>
                </div>
                <span className="stat-value">{stats.active_reviews_count}</span>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>In review queue</span>
              </div>

              <div className="stat-card" style={{ flexDirection: "column", alignItems: "flex-start", gap: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
                  <span className="stat-label">Updates</span>
                  <div className="stat-icon-wrap" style={{ width: "28px", height: "28px", fontSize: "14px" }}>
                    <ShieldCheck size={14} />
                  </div>
                </div>
                <span className="stat-value">{stats.unread_notifications_count}</span>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Unread notices</span>
              </div>
            </div>
          </div>

          {/* 3. ACTIVE PROFESSIONAL REVIEWS */}
          {activeReviews.length > 0 && (
            <section className="dashboard-section">
              <div className="dashboard-section-header">
                <div className="section-title-wrap">
                  <span className="eyebrow" style={{ color: "var(--color-info-text)" }}>ACTIVE CONSULTATIONS</span>
                  <h2>In-Progress Specialist Reviews</h2>
                </div>
                {onViewAllReviews && (
                  <button
                    type="button"
                    className="btn-view-all-link"
                    onClick={onViewAllReviews}
                  >
                    <span>View All Reviews ({stats.active_reviews_count + stats.completed_reviews_count})</span>
                    <ChevronRight size={14} />
                  </button>
                )}
              </div>

              <div className="dashboard-active-reviews-grid">
                {activeReviews.map((rev) => {
                  const statusInfo = getPatientStatusInfo(rev.status);
                  return (
                    <div
                      key={rev.id}
                      className="dashboard-active-review-card"
                      onClick={() => onOpenReviewDetail(rev.id)}
                    >
                      <div className="card-top-row">
                        <span className="review-ref-tag">{formatCaseId(rev.id)}</span>
                        <span className={statusInfo.className}>
                          <span className="pill-dot" />
                          {statusInfo.label}
                        </span>
                      </div>

                      <div className="doctor-matching-info">
                        <div className="doc-avatar-icon">
                          <Stethoscope size={16} />
                        </div>
                        <div className="doc-matching-text">
                          <strong>
                            {rev.professional?.full_name || "Verified Clinical Specialist"}
                          </strong>
                          <p>
                            {rev.professional?.specialty || rev.professional?.specialization || "Radiology"}
                            {rev.professional?.hospital_or_clinic ? ` • ${rev.professional.hospital_or_clinic}` : ""}
                          </p>
                        </div>
                      </div>

                      <div className="review-card-meta-line">
                        <span>{formatCaseId(rev.analysis_id)}</span>
                        <span>Requested {formatDate(rev.requested_at || rev.created_at)}</span>
                      </div>

                      <div className="card-action-footer">
                        <span className="btn-view-active-review">
                          View Status Details →
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* 4. COMPLETED PROFESSIONAL REVIEWS */}
          {completedReviews.length > 0 && (
            <section className="dashboard-section">
              <div className="dashboard-section-header">
                <div className="section-title-wrap">
                  <span className="eyebrow" style={{ color: "var(--color-success)" }}>COMPLETED ASSESSMENTS</span>
                  <h2>Physician Second Opinions</h2>
                </div>
                {onViewAllReviews && (
                  <button
                    type="button"
                    className="btn-view-all-link"
                    onClick={onViewAllReviews}
                  >
                    <span>View All ({stats.completed_reviews_count})</span>
                    <ChevronRight size={14} />
                  </button>
                )}
              </div>

              <div className="dashboard-completed-reviews-grid">
                {completedReviews.map((rev) => {
                  const urgency = rev.professional_review?.urgency || "ROUTINE";
                  return (
                    <div
                      key={rev.id}
                      className="dashboard-completed-card"
                      onClick={() => onOpenReviewDetail(rev.id)}
                    >
                      <div className="card-top-row">
                        <div className="completed-doc-block">
                          <div className="doc-avatar-badge">
                            <Stethoscope size={16} />
                          </div>
                          <div>
                            <div className="doc-name-badge-row">
                              <strong>{rev.professional?.full_name || "Verified Specialist"}</strong>
                            </div>
                            <p className="doc-spec-text">
                              {rev.professional?.specialty || rev.professional?.specialization || "Radiology"}
                            </p>
                          </div>
                        </div>
                        <span className="patient-status-pill status-completed">
                          <CheckCircle2 size={11} />
                          <span>Completed</span>
                        </span>
                      </div>

                      <div className="completed-meta-row">
                        <span>{formatCaseId(rev.analysis_id)}</span>
                        <span>Completed {formatDate(rev.completed_at || rev.updated_at)}</span>
                      </div>

                      <div className="completed-card-footer">
                        <span className={`status-tag status-${urgency.toLowerCase()}`}>
                          Urgency: {urgency}
                        </span>
                        <span className="btn-view-report-link">
                          View Assessment →
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* 5. RECENT ANALYSES (TIMELINE / LIST) */}
          <section className="dashboard-section">
            <div className="dashboard-section-header">
              <div className="section-title-wrap">
                <span className="eyebrow">AI DECISION SUPPORT</span>
                <h2>Recent Chest Radiograph Analyses</h2>
              </div>
              {recentAnalyses.length > 0 && onViewAllHistory && (
                <button
                  type="button"
                  className="btn-view-all-link"
                  onClick={onViewAllHistory}
                >
                  <span>Full History ({stats.total_analyses})</span>
                  <ChevronRight size={14} />
                </button>
              )}
            </div>

            {recentAnalyses.length === 0 ? (
              <div className="dashboard-empty-card">
                <div className="empty-card-icon">
                  <Activity size={22} />
                </div>
                <h3>No chest X-ray analyses yet</h3>
                <p>
                  Upload your first chest radiograph to receive automated DenseNet121 findings and Grad-CAM visual explainability.
                </p>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={onNewAnalysis}
                  style={{ marginTop: "8px" }}
                >
                  <Plus size={14} />
                  <span>Start First Analysis</span>
                </button>
              </div>
            ) : (
              <div className="dashboard-analyses-grid">
                {recentAnalyses.map((analysis) => {
                  const detectedCount = analysis.detected_findings?.length || 0;
                  const reviewStatusInfo = analysis.review_status ? getPatientStatusInfo(analysis.review_status) : null;

                  return (
                    <div
                      key={analysis.analysis_id}
                      className="dashboard-analysis-card"
                      onClick={() => onOpenAnalysis(analysis.analysis_id)}
                    >
                      <div className="analysis-card-top">
                        <span className="analysis-id-tag">{formatCaseId(analysis.analysis_id)}</span>
                        <span className="status-tag" style={{ background: "var(--surface-primary)" }}>
                          {analysis.view || "Frontal"} View
                        </span>
                      </div>

                      <div className="analysis-card-body">
                        <h4 style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)" }}>
                          {analysis.view || "Frontal"} Chest Radiograph
                        </h4>
                        <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                          {formatDate(analysis.created_at)}
                        </p>

                        <div className="findings-summary-box">
                          <span className="findings-count-label">
                            {detectedCount > 0
                              ? `${detectedCount} finding(s) detected`
                              : "No acute findings detected"}
                          </span>
                          {detectedCount > 0 && analysis.detected_findings && (
                            <div className="finding-chips-wrap">
                              {analysis.detected_findings.slice(0, 3).map((f) => (
                                <span key={f} className="finding-chip">{f}</span>
                              ))}
                              {analysis.detected_findings.length > 3 && (
                                <span className="finding-chip-more">
                                  +{analysis.detected_findings.length - 3}
                                </span>
                              )}
                            </div>
                          )}
                        </div>

                        {reviewStatusInfo && (
                          <div style={{ marginTop: "6px" }}>
                            <span className={reviewStatusInfo.className}>
                              <span className="pill-dot" />
                              {reviewStatusInfo.label}
                            </span>
                          </div>
                        )}
                      </div>

                      <div className="analysis-card-action">
                        <span className="btn-open-analysis">
                          View Analysis →
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* 6. CLINICAL DECISION SUPPORT REMINDER */}
          <div className="dashboard-guidance-card">
            <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
              <div style={{
                width: "38px",
                height: "38px",
                borderRadius: "var(--radius-md)",
                background: "var(--accent-light)",
                color: "var(--accent-primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}>
                <ShieldCheck size={20} />
              </div>
              <div className="guidance-text">
                <h4>Clinical Decision Support Reminder</h4>
                <p>
                  HC-XCDSS provides AI-assisted radiographic findings to support clinical evaluation. For diagnostic certainty or personalized care, you can request an independent second opinion from a verified healthcare professional.
                </p>
              </div>
            </div>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={onNewAnalysis}
              style={{ whiteSpace: "nowrap" }}
            >
              <Plus size={13} />
              <span>New Analysis</span>
            </button>
          </div>
        </>
      )}
    </div>
  );
}
