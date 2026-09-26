import { useState, useEffect } from "react";
import {
  getReview,
  acceptReview,
  startReview,
  declineReview,
  getHeatmapUrl,
} from "../services/api";
import FindingsGrid from "./FindingsGrid";
import PatientExplanations from "./PatientExplanations";
import HeatmapSection from "./HeatmapSection";
import ProfessionalReviewForm from "./ProfessionalReviewForm";
import ClinicalNotice from "./ClinicalNotice";

export default function ProfessionalReviewScreen({
  reviewId,
  onBack,
  onWorkflowComplete,
}) {
  const [reviewData, setReviewData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState("");
  const [showCompleteForm, setShowCompleteForm] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getReview(reviewId);
      setReviewData(data);
    } catch (err) {
      console.error("Load review error:", err);
      setError(err.message || "Failed to load review details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [reviewId]);

  const handleAccept = async () => {
    setActionLoading(true);
    setActionError("");
    try {
      await acceptReview(reviewId);
      await loadData();
    } catch (err) {
      setActionError(err.message || "Failed to accept review.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleStart = async () => {
    setActionLoading(true);
    setActionError("");
    try {
      await startReview(reviewId);
      await loadData();
      setShowCompleteForm(true);
    } catch (err) {
      setActionError(err.message || "Failed to start review.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDecline = async () => {
    if (!window.confirm("Are you sure you want to decline this review request?")) {
      return;
    }
    setActionLoading(true);
    setActionError("");
    try {
      await declineReview(reviewId);
      await loadData();
    } catch (err) {
      setActionError(err.message || "Failed to decline review.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCompleteSuccess = () => {
    setShowCompleteForm(false);
    loadData();
    if (onWorkflowComplete) {
      onWorkflowComplete();
    }
  };

  if (loading) {
    return (
      <div className="history-loading">
        <div className="loading-spinner" />
        <p>Loading patient analysis and clinical review context...</p>
      </div>
    );
  }

  if (error || !reviewData) {
    return (
      <div className="history-error-container">
        <h3>Error Loading Review</h3>
        <p>{error || "Review request not found."}</p>
        <button type="button" className="history-back-button" onClick={onBack}>
          ← Back to Dashboard
        </button>
      </div>
    );
  }

  const { review_request, analysis_summary, ai_report, professional, professional_review } = reviewData;
  const originalImage = analysis_summary?.image ? getHeatmapUrl(analysis_summary.image) : null;
  const currentStatus = review_request.status;

  return (
    <section className="results professional-review-screen">
      {/* HEADER */}
      <div className="results-header">
        <div>
          <div className="eyebrow">PHYSICIAN REVIEW WORKFLOW</div>
          <h2>Clinical Review #{review_request.id.substring(0, 8)}</h2>
          <p>
            Radiograph ID: <strong>{analysis_summary?.analysis_id}</strong>
          </p>
        </div>

        <div className="results-actions">
          <button type="button" className="history-back-button" onClick={onBack}>
            ← Dashboard
          </button>
          <span className={`status-tag status-${currentStatus.toLowerCase().replace("_", "-")}`}>
            {currentStatus}
          </span>
        </div>
      </div>

      {actionError && <div className="error-banner">{actionError}</div>}

      {/* =========================================================
          WORKFLOW STATUS STEPPER & ACTIONS BAR
          ========================================================= */}
      <div className="workflow-stepper-card">
        <div className="stepper-row">
          <div className={`step-node ${currentStatus === "REQUESTED" ? "active" : "done"}`}>
            <span className="step-num">1</span>
            <span className="step-title">REQUESTED</span>
          </div>
          <div className="step-arrow">→</div>
          <div className={`step-node ${currentStatus === "ACCEPTED" ? "active" : ["IN_REVIEW", "COMPLETED"].includes(currentStatus) ? "done" : ""}`}>
            <span className="step-num">2</span>
            <span className="step-title">ACCEPTED</span>
          </div>
          <div className="step-arrow">→</div>
          <div className={`step-node ${currentStatus === "IN_REVIEW" ? "active" : currentStatus === "COMPLETED" ? "done" : ""}`}>
            <span className="step-num">3</span>
            <span className="step-title">IN REVIEW</span>
          </div>
          <div className="step-arrow">→</div>
          <div className={`step-node ${currentStatus === "COMPLETED" ? "done active" : ""}`}>
            <span className="step-num">4</span>
            <span className="step-title">COMPLETED</span>
          </div>
        </div>

        <div className="workflow-actions-bar">
          {currentStatus === "REQUESTED" && (
            <div className="btn-group">
              <button
                type="button"
                className="btn-primary"
                onClick={handleAccept}
                disabled={actionLoading}
              >
                {actionLoading ? "Accepting..." : "✓ Accept Review Request"}
              </button>
              <button
                type="button"
                className="btn-secondary btn-decline"
                onClick={handleDecline}
                disabled={actionLoading}
              >
                Decline
              </button>
            </div>
          )}

          {currentStatus === "ACCEPTED" && (
            <div className="btn-group">
              <button
                type="button"
                className="btn-primary"
                onClick={handleStart}
                disabled={actionLoading}
              >
                {actionLoading ? "Starting..." : "🔬 Start Review"}
              </button>
              <button
                type="button"
                className="btn-secondary btn-decline"
                onClick={handleDecline}
                disabled={actionLoading}
              >
                Decline
              </button>
            </div>
          )}

          {currentStatus === "IN_REVIEW" && (
            <div className="btn-group">
              <button
                type="button"
                className="btn-primary"
                onClick={() => setShowCompleteForm(true)}
              >
                📝 Submit Clinical Review
              </button>
            </div>
          )}

          {currentStatus === "COMPLETED" && (
            <div className="workflow-completed-pill">
              ✓ Clinical review signed & delivered to patient
            </div>
          )}
        </div>
      </div>

      {/* PATIENT NOTE IF PRESENT */}
      {review_request.patient_message && (
        <div className="patient-context-callout">
          <span className="context-kicker">PATIENT INQUIRY / NOTE</span>
          <p>"{review_request.patient_message}"</p>
        </div>
      )}

      {/* IF COMPLETED: DISPLAY COMPLETED REVIEW */}
      {currentStatus === "COMPLETED" && professional_review && (
        <div className="section-container professional-review-section">
          <div className="review-section-header">
            <div className="section-badge doctor-badge">COMPLETED REVIEW</div>
            <h3>Signed Clinical Assessment</h3>
            <p>Delivered to patient on {new Date(professional_review.reviewed_at).toLocaleDateString()}</p>
          </div>

          <div className="review-fields-grid">
            <div className="review-field-card primary-assessment">
              <span className="field-label">CLINICAL SUMMARY</span>
              <p className="field-text">{professional_review.clinical_summary || professional_review.assessment}</p>
            </div>
            {professional_review.finding_validations && Object.keys(professional_review.finding_validations).length > 0 && (
              <div className="review-field-card finding-validations-card">
                <span className="field-label">FINDINGS VALIDATION</span>
                <div className="validations-display-list">
                  {Object.entries(professional_review.finding_validations).map(([finding, status]) => (
                    <div key={finding} className="validation-item-badge">
                      <span className="val-name">{finding}:</span>
                      <span className={`val-status status-${String(status).toLowerCase()}`}>
                        {status === "AGREED" ? "✓ Agreed" : status === "DISAGREED" ? "✗ Disagreed" : "? Inconclusive"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {professional_review.recommendations && (
              <div className="review-field-card recommendations">
                <span className="field-label">RECOMMENDATIONS</span>
                <p className="field-text">{professional_review.recommendations}</p>
              </div>
            )}
            {professional_review.professional_notes && (
              <div className="review-field-card notes">
                <span className="field-label">NOTES</span>
                <p className="field-text">{professional_review.professional_notes}</p>
              </div>
            )}
            {professional_review.limitations && (
              <div className="review-field-card limitations">
                <span className="field-label">LIMITATIONS</span>
                <p className="field-text">{professional_review.limitations}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* FORM MODAL / EMBED IF IN_REVIEW */}
      {showCompleteForm && currentStatus === "IN_REVIEW" && (
        <ProfessionalReviewForm
          reviewId={reviewId}
          detectedFindings={analysis_summary?.detected_findings || []}
          onCompleteSuccess={handleCompleteSuccess}
          onCancel={() => setShowCompleteForm(false)}
        />
      )}

      {/* =========================================================
          CLINICAL RADIOGRAPH & AI EVIDENCE SECTION
          ========================================================= */}
      <div className="section-container ai-report-section">
        <div className="review-section-header">
          <div className="section-badge ai-badge">🤖 AI-ASSISTED REPORT & RADIOGRAPH</div>
          <h3>Machine Learning Findings & Visual Explanations</h3>
        </div>

        {/* SUMMARY STRIP */}
        <div className="summary-strip">
          <div className="summary-item">
            <span className="summary-label">X-Ray View</span>
            <strong>{analysis_summary?.view || "Frontal"}</strong>
          </div>
          <div className="summary-divider" />
          <div className="summary-item">
            <span className="summary-label">Evaluated</span>
            <strong>{Object.keys(analysis_summary?.findings || {}).length}</strong>
          </div>
          <div className="summary-divider" />
          <div className="summary-item">
            <span className="summary-label">Detected</span>
            <strong className="detected-summary">
              {analysis_summary?.detected_findings?.length || 0}
            </strong>
          </div>
        </div>

        {/* IMAGE */}
        {originalImage && (
          <div className="image-card">
            <div className="section-heading">
              <div>
                <span className="section-kicker">RADIOGRAPH</span>
                <h3>Chest X-Ray ({analysis_summary?.view})</h3>
              </div>
            </div>
            <div className="result-image-wrapper">
              <img src={originalImage} alt="Uploaded radiograph" className="result-xray" />
            </div>
          </div>
        )}

        {/* FINDINGS */}
        {analysis_summary?.findings && (
          <FindingsGrid findings={analysis_summary.findings} view={analysis_summary?.view || "Frontal"} />
        )}

        {/* PATIENT EXPLANATIONS */}
        {analysis_summary?.patient_explanations && (
          <PatientExplanations patientExplanations={analysis_summary.patient_explanations} />
        )}

        {/* GRAD-CAM */}
        {analysis_summary?.heatmaps && originalImage && (
          <HeatmapSection
            heatmaps={analysis_summary.heatmaps}
            findings={analysis_summary.findings}
            originalImage={originalImage}
          />
        )}
      </div>

      <ClinicalNotice />
    </section>
  );
}
