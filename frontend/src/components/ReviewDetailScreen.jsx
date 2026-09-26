import { useState } from "react";
import { getHeatmapUrl, cancelReview, downloadProfessionalReviewReport } from "../services/api";
import FindingsGrid from "./FindingsGrid";
import PatientExplanations from "./PatientExplanations";
import HeatmapSection from "./HeatmapSection";
import ClinicalNotice from "./ClinicalNotice";
import {
  Stethoscope,
  ArrowLeft,
  Download,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Activity,
  FileText,
  User,
} from "lucide-react";

function formatDateTime(isoString) {
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
}

function formatCaseId(id) {
  if (!id) return "—";
  const clean = String(id).replace(/^#/, "");
  return `Case #${clean.substring(0, 8).toUpperCase()}`;
}

export default function ReviewDetailScreen({
  reviewData,
  loading,
  error,
  onBack,
  onRefresh,
}) {
  const [cancelling, setCancelling] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [actionError, setActionError] = useState("");
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  if (loading) {
    return (
      <div className="dashboard-empty-card" style={{ padding: "60px 20px" }}>
        <span className="spinner" style={{ width: "24px", height: "24px", borderWidth: "3px" }} />
        <h3>Loading Review Case...</h3>
        <p>Retrieving independent professional assessment and AI findings.</p>
      </div>
    );
  }

  if (error || !reviewData) {
    return (
      <div className="validation-error-card" style={{ padding: "28px", margin: "30px auto", maxWidth: "600px" }}>
        <div className="val-error-header">
          <AlertTriangle size={20} />
          <h3 style={{ margin: 0 }}>Unable to load review</h3>
        </div>
        <p className="val-error-desc">{error || "Review request not found."}</p>
        <button type="button" className="btn-secondary btn-sm" onClick={onBack} style={{ marginTop: "10px" }}>
          <ArrowLeft size={13} />
          <span>Back to Reviews</span>
        </button>
      </div>
    );
  }

  const { review_request, analysis_summary, ai_report, professional, professional_review } = reviewData;
  const originalImage = analysis_summary?.image ? getHeatmapUrl(analysis_summary.image) : null;
  const isCompleted = review_request.status === "COMPLETED";
  const canCancel = ["REQUESTED", "ASSIGNED"].includes(review_request.status);

  const handleCancel = async () => {
    if (!window.confirm("Are you sure you want to cancel this active review request?")) {
      return;
    }

    setCancelling(true);
    setActionError("");

    try {
      await cancelReview(review_request.id);
      if (onRefresh) {
        onRefresh();
      }
    } catch (err) {
      console.error("Cancellation error:", err);
      setActionError(err.message || "Failed to cancel review request.");
    } finally {
      setCancelling(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    setActionError("");
    setDownloadSuccess(false);

    try {
      await downloadProfessionalReviewReport(review_request.id);
      setDownloadSuccess(true);
      setTimeout(() => setDownloadSuccess(false), 4000);
    } catch (err) {
      console.error("Report download error:", err);
      setActionError(err.message || "Unable to generate report download. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  const observations = professional_review?.clinical_observations || professional_review?.clinical_summary || professional_review?.assessment;
  const impression = professional_review?.professional_impression || professional_review?.clinical_impression || observations;
  const recommendations = professional_review?.recommendations;
  const urgency = professional_review?.urgency || "ROUTINE";
  const followUp = professional_review?.follow_up || professional_review?.follow_up_required;
  const additionalNotes = professional_review?.additional_notes || professional_review?.message_to_patient || professional_review?.professional_notes;

  return (
    <section className="results-screen-container">
      {/* HEADER */}
      <div className="results-top-bar">
        <div>
          <div className="eyebrow" style={{ color: "var(--accent-primary)" }}>
            <Stethoscope size={12} />
            <span>CLINICAL SECOND OPINION REPORT</span>
          </div>
          <h2>{formatCaseId(review_request.id)}</h2>
          <div className="results-case-meta">
            <span>Radiograph: <strong>{formatCaseId(analysis_summary?.analysis_id || review_request.analysis_id)}</strong></span>
            <span>•</span>
            <span>Requested: {formatDateTime(review_request.requested_at || review_request.created_at)}</span>
          </div>
        </div>

        <div className="results-actions-group">
          <button type="button" className="btn-secondary btn-sm" onClick={onBack}>
            <ArrowLeft size={13} />
            <span>Back</span>
          </button>

          {isCompleted && (
            <button
              type="button"
              className="btn-primary btn-sm"
              onClick={handleDownload}
              disabled={downloading}
            >
              <Download size={13} />
              <span>{downloading ? "Preparing..." : "Download Report"}</span>
            </button>
          )}

          <span className={`status-tag status-${review_request.status?.toLowerCase()}`}>
            {review_request.status}
          </span>
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

      {downloadSuccess && (
        <div style={{
          padding: "10px 14px",
          background: "var(--color-success-bg)",
          border: "1px solid var(--color-success-border)",
          borderRadius: "var(--radius-md)",
          color: "var(--color-success-text)",
          fontSize: "13px",
          fontWeight: "600",
          display: "flex",
          alignItems: "center",
          gap: "6px",
        }}>
          <CheckCircle2 size={16} />
          <span>Professional review report downloaded successfully.</span>
        </div>
      )}

      {/* =========================================================
          SECTION 1: VERIFIED PROFESSIONAL REVIEW (HUMAN REVIEW FOCUS)
          ========================================================= */}
      <div className="pro-card" style={{ padding: "24px", border: "1.5px solid var(--accent-light-border)" }}>
        <div className="pro-card-header" style={{ padding: "0 0 14px 0", marginBottom: "16px" }}>
          <div>
            <div className="eyebrow" style={{ color: "var(--color-success)" }}>
              <ShieldCheck size={12} />
              <span>VERIFIED PHYSICIAN SECOND OPINION</span>
            </div>
            <h3 style={{ fontSize: "17px", fontWeight: "700" }}>Independent Healthcare Professional Assessment</h3>
          </div>

          {isCompleted && (
            <span className="badge-verified-pro">
              <CheckCircle2 size={11} />
              <span>Verified Specialist Assessment</span>
            </span>
          )}
        </div>

        {isCompleted && professional_review ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            {/* Physician Profile Card */}
            <div style={{
              background: "var(--surface-secondary)",
              border: "1px solid var(--border-main)",
              borderRadius: "var(--radius-lg)",
              padding: "14px 18px",
              display: "flex",
              alignItems: "center",
              gap: "14px",
            }}>
              <div className="doc-avatar-icon">
                <Stethoscope size={18} />
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <strong style={{ fontSize: "15px", color: "var(--text-primary)" }}>
                    {professional?.full_name || "Verified Clinical Specialist"}
                  </strong>
                  <span className="badge-verified-pro">✓ Verified</span>
                </div>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                  {professional?.specialty || professional?.specialization || "Radiology"}
                  {professional?.hospital_or_clinic ? ` • ${professional.hospital_or_clinic}` : ""}
                </p>
                <p style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                  Completed {formatDateTime(professional_review.completed_at || review_request.completed_at)}
                </p>
              </div>
            </div>

            {/* Assessment Findings Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
              <div style={{
                background: "var(--surface-secondary)",
                border: "1px solid var(--border-main)",
                borderRadius: "var(--radius-md)",
                padding: "14px",
              }}>
                <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  Clinical Observations
                </span>
                <p style={{ fontSize: "13px", color: "var(--text-primary)", lineHeight: "1.5", marginTop: "6px" }}>
                  {observations || "No specific radiographic observations reported."}
                </p>
              </div>

              <div style={{
                background: "var(--surface-secondary)",
                border: "1px solid var(--border-main)",
                borderRadius: "var(--radius-md)",
                padding: "14px",
              }}>
                <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  Professional Impression
                </span>
                <p style={{ fontSize: "13px", color: "var(--text-primary)", lineHeight: "1.5", marginTop: "6px" }}>
                  {impression || "No acute diagnostic impression specified."}
                </p>
              </div>

              {recommendations && (
                <div style={{
                  gridColumn: "1 / -1",
                  background: "var(--surface-secondary)",
                  border: "1px solid var(--border-main)",
                  borderRadius: "var(--radius-md)",
                  padding: "14px",
                }}>
                  <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                    Recommendations & Next Steps
                  </span>
                  <p style={{ fontSize: "13px", color: "var(--text-primary)", lineHeight: "1.5", marginTop: "6px" }}>
                    {recommendations}
                  </p>
                </div>
              )}

              <div style={{
                gridColumn: "1 / -1",
                display: "flex",
                alignItems: "center",
                gap: "16px",
                padding: "10px 14px",
                background: "var(--surface-primary)",
                border: "1px solid var(--border-main)",
                borderRadius: "var(--radius-md)",
                fontSize: "12px",
              }}>
                <span className={`status-tag status-${urgency.toLowerCase()}`}>
                  Urgency: {urgency}
                </span>
                <span style={{ color: "var(--text-secondary)" }}>
                  Formal Physician Follow-up: <strong>{followUp ? "Recommended" : "Routine Care"}</strong>
                </span>
              </div>

              {additionalNotes && (
                <div style={{
                  gridColumn: "1 / -1",
                  padding: "12px 14px",
                  background: "var(--surface-primary)",
                  border: "1px solid var(--border-main)",
                  borderRadius: "var(--radius-md)",
                  fontSize: "12px",
                  color: "var(--text-secondary)",
                }}>
                  <strong style={{ color: "var(--text-primary)", display: "block", marginBottom: "4px" }}>
                    Additional Clinical Notes:
                  </strong>
                  {additionalNotes}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: "32px 20px" }}>
            <div style={{
              width: "44px",
              height: "44px",
              borderRadius: "var(--radius-full)",
              background: "var(--color-warning-bg)",
              color: "var(--color-warning-text)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 12px",
            }}>
              <Clock size={20} />
            </div>
            <h4 style={{ fontSize: "16px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "4px" }}>
              Professional Review In Progress ({review_request.status})
            </h4>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", maxWidth: "460px", margin: "0 auto 18px", lineHeight: "1.5" }}>
              {review_request.status === "REQUESTED" &&
                "Your review request has been registered in the verified specialist queue and is awaiting physician acceptance."}
              {review_request.status === "ASSIGNED" &&
                `Your case is assigned to ${professional?.full_name || "a verified physician"} and awaiting review confirmation.`}
              {review_request.status === "ACCEPTED" &&
                `Accepted by ${professional?.full_name || "a verified physician"}. Your X-ray review has been scheduled.`}
              {review_request.status === "IN_REVIEW" &&
                `Your case is currently being actively analyzed by ${professional?.full_name || "the attending physician"}. You will receive a notification once finalized.`}
            </p>

            {canCancel && (
              <button
                type="button"
                className="btn-danger btn-sm"
                onClick={handleCancel}
                disabled={cancelling}
              >
                {cancelling ? "Cancelling..." : "Cancel Review Request"}
              </button>
            )}
          </div>
        )}
      </div>

      {/* =========================================================
          SECTION 2: AI DECISION SUPPORT INFERENCES
          ========================================================= */}
      {analysis_summary?.findings && (
        <FindingsGrid findings={analysis_summary.findings} view={analysis_summary.view || "Frontal"} />
      )}

      {analysis_summary?.heatmaps && (
        <HeatmapSection
          heatmaps={analysis_summary.heatmaps}
          findings={analysis_summary.findings}
          originalImage={originalImage}
        />
      )}

      <ClinicalNotice />
    </section>
  );
}
