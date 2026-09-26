import { useState, useEffect } from "react";
import {
  getProfessionalCaseWorkspace,
  getHeatmapUrl,
  saveProfessionalAssessmentDraft,
  submitProfessionalAssessment,
} from "../services/api";
import ClinicalNotice from "./ClinicalNotice";
import {
  Stethoscope,
  ArrowLeft,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  Save,
  Check,
  Maximize2,
  X,
  User,
  Activity,
  Info,
} from "lucide-react";

/**
 * Format decimal probability value to percentage string.
 */
function formatPercentage(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return `${(Number(value) * 100).toFixed(1)}%`;
}

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

/**
 * Safely format backend errors into human-readable strings, preventing [object Object].
 */
function extractErrorMessage(err, fallback = "An unexpected error occurred.") {
  if (!err) return fallback;
  if (typeof err === "string") return err;
  if (typeof err.message === "string" && err.message && err.message !== "[object Object]") {
    return err.message;
  }
  if (typeof err.detail === "string") return err.detail;
  if (Array.isArray(err.detail)) {
    return err.detail.map((e) => e.msg || e.message || JSON.stringify(e)).join("; ");
  }
  if (err.detail && typeof err.detail === "object") {
    return err.detail.msg || err.detail.message || JSON.stringify(err.detail);
  }
  return fallback;
}

/**
 * Professional Case Workspace Component.
 * Complete clinical interface for verified physicians to review assigned patient radiographs,
 * inspect AI inferences & Grad-CAM overlays, author independent clinical assessments,
 * save drafts, and submit final reviews.
 */
export default function ProfessionalCaseWorkspace({ reviewId, onBack, onWorkflowComplete }) {
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isInverted, setIsInverted] = useState(false);
  const [selectedHeatmapFinding, setSelectedHeatmapFinding] = useState(null);
  const [heatmapOpacity, setHeatmapOpacity] = useState(100);

  // Assessment Form State
  const [formData, setFormData] = useState({
    clinical_observations: "",
    professional_impression: "",
    recommendations: "",
    urgency: "ROUTINE",
    follow_up: false,
    additional_notes: "",
  });

  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [assessmentSuccess, setAssessmentSuccess] = useState("");
  const [assessmentError, setAssessmentError] = useState("");
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function loadWorkspace() {
      setLoading(true);
      setError("");
      try {
        const data = await getProfessionalCaseWorkspace(reviewId);
        if (isMounted) {
          setCaseData(data);
          const detectedFirst = data?.analysis?.detected_findings?.[0];
          const heatmapsFirst = Object.keys(data?.analysis?.heatmaps || {})[0];
          setSelectedHeatmapFinding(detectedFirst || heatmapsFirst || null);
        }
      } catch (err) {
        if (!isMounted) return;
        console.error("Workspace load error:", err);
        const status = err.status || 500;
        if (status === 401) {
          setError("Authentication session expired. Please log in again.");
        } else if (status === 403) {
          setError("You do not have access to this case.");
        } else if (status === 404) {
          setError("This review case could not be found.");
        } else {
          setError("Unable to load this clinical case right now. Please try again.");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    if (reviewId) {
      loadWorkspace();
    }

    return () => {
      isMounted = false;
    };
  }, [reviewId]);

  // Sync form data whenever caseData loads or updates (declared before conditional returns)
  useEffect(() => {
    const profReview = caseData?.professional_review;
    if (profReview) {
      setFormData({
        clinical_observations: profReview.clinical_observations || profReview.clinical_summary || profReview.assessment || "",
        professional_impression: profReview.professional_impression || profReview.clinical_impression || profReview.clinical_summary || "",
        recommendations: profReview.recommendations || "",
        urgency: profReview.urgency || "ROUTINE",
        follow_up: Boolean(profReview.follow_up ?? profReview.follow_up_required),
        additional_notes: profReview.additional_notes || profReview.professional_notes || "",
      });
    }
  }, [caseData]);

  // Loading State
  if (loading) {
    return (
      <section className="pro-workspace-container">
        <div className="dashboard-empty-card" style={{ padding: "60px 20px" }}>
          <span className="spinner" style={{ width: "24px", height: "24px", borderWidth: "3px" }} />
          <h3>Loading Clinical Case Workspace...</h3>
          <p>Retrieving radiograph, CheXpert inferences, Grad-CAM overlays, and assessment history.</p>
        </div>
      </section>
    );
  }

  // Error State
  if (error || !caseData) {
    return (
      <section className="pro-workspace-container">
        <div className="validation-error-card" style={{ padding: "28px" }}>
          <div className="val-error-header">
            <AlertTriangle size={20} />
            <h3 style={{ margin: 0 }}>Unable to Open Case</h3>
          </div>
          <p className="val-error-desc">{error || "The requested clinical case is unavailable."}</p>
          <button type="button" className="btn-secondary btn-sm" onClick={onBack} style={{ marginTop: "10px" }}>
            <ArrowLeft size={13} />
            <span>Back to Review Queue</span>
          </button>
        </div>
      </section>
    );
  }

  const {
    review_request = {},
    patient = {},
    analysis = {},
    ai_report = null,
    professional_review = null,
  } = caseData;

  const profReview = caseData.professional_review || professional_review;
  const isCompleted = review_request.status === "COMPLETED";

  const originalImage = analysis.image_url
    ? getHeatmapUrl(analysis.image_url)
    : analysis.image
    ? getHeatmapUrl(analysis.image)
    : null;

  const rawFindings = analysis.findings || {};
  const standardConditions = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion",
  ];

  const allConditionKeys = Array.from(
    new Set([...standardConditions, ...Object.keys(rawFindings)])
  );

  const rawHeatmaps = analysis.heatmaps || {};
  const activeHeatmapPath = selectedHeatmapFinding && rawHeatmaps[selectedHeatmapFinding];
  const activeHeatmapUrl = activeHeatmapPath ? getHeatmapUrl(activeHeatmapPath) : null;

  // Handle Save Draft
  const handleSaveDraft = async () => {
    setIsSavingDraft(true);
    setAssessmentError("");
    setAssessmentSuccess("");
    try {
      const savedReview = await saveProfessionalAssessmentDraft(reviewId, formData);
      setCaseData((prev) => ({
        ...prev,
        review_request: {
          ...prev.review_request,
          status: prev.review_request.status === "COMPLETED" ? "COMPLETED" : "IN_REVIEW",
        },
        professional_review: savedReview,
      }));
      setAssessmentSuccess("Draft assessment saved successfully.");
      setTimeout(() => setAssessmentSuccess(""), 4000);
    } catch (err) {
      console.error("Draft save error:", err);
      const status = err.status || 500;
      if (status === 409) {
        setAssessmentError("Review already completed and cannot be modified.");
      } else if (status === 403) {
        setAssessmentError("You do not have permission to edit this assessment.");
      } else {
        setAssessmentError(extractErrorMessage(err, "Failed to save draft assessment."));
      }
    } finally {
      setIsSavingDraft(false);
    }
  };

  // Handle Initiate Submit
  const handleInitiateSubmit = () => {
    setAssessmentError("");
    const obs = (formData.clinical_observations || "").trim();
    const imp = (formData.professional_impression || "").trim();

    if (!obs && !imp) {
      setAssessmentError("Please enter Clinical Observations or Professional Impression before submitting.");
      return;
    }

    if ((obs && obs.length < 5) && (imp && imp.length < 5)) {
      setAssessmentError("Clinical assessment observations / impression must be at least 5 characters long.");
      return;
    }

    setShowConfirmModal(true);
  };

  // Handle Confirm Final Submit
  const handleConfirmSubmit = async () => {
    setShowConfirmModal(false);
    setIsSubmitting(true);
    setAssessmentError("");
    setAssessmentSuccess("");
    try {
      const completedReview = await submitProfessionalAssessment(reviewId, formData);
      setCaseData((prev) => ({
        ...prev,
        review_request: {
          ...prev.review_request,
          status: "COMPLETED",
          completed_at: new Date().toISOString(),
        },
        professional_review: completedReview,
      }));
      setAssessmentSuccess("Professional clinical review successfully signed and finalized!");
      if (onWorkflowComplete) {
        onWorkflowComplete();
      }
    } catch (err) {
      console.error("Submission error:", err);
      const status = err.status || 500;
      if (status === 409) {
        setAssessmentError("Review already completed.");
      } else if (status === 403) {
        setAssessmentError("You do not have permission to submit this assessment.");
      } else if (status === 422 || status === 400) {
        setAssessmentError(extractErrorMessage(err, "Validation failed. Please check your clinical observations and impression."));
      } else {
        setAssessmentError(extractErrorMessage(err, "Unable to submit professional review. Please try again."));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="pro-workspace-container">
      {/* 1. TOP BAR */}
      <header className="pro-workspace-header">
        <div>
          <div className="eyebrow" style={{ color: "var(--accent-primary)" }}>
            <Stethoscope size={12} />
            <span>CLINICAL CASE WORKSPACE</span>
          </div>
          <div className="header-title-row">
            <h2>{formatCaseId(review_request.id)}</h2>
            <div className="header-badges">
              <span className={`status-tag status-${review_request.status?.toLowerCase() || "assigned"}`}>
                {review_request.status || "ASSIGNED"}
              </span>
              <span className="status-tag status-paid">
                💳 {review_request.payment_status || "PAID"}
              </span>
            </div>
          </div>
          <div className="header-subtext">
            <span>Radiograph: <strong>{formatCaseId(analysis.analysis_id || review_request.analysis_id)}</strong></span>
            <span className="subtext-separator">•</span>
            <span>Projection: <strong>{analysis.view || "Frontal"}</strong></span>
            <span className="subtext-separator">•</span>
            <span>Requested: {formatDateTime(review_request.requested_at || review_request.created_at)}</span>
          </div>
        </div>

        <button type="button" className="btn-secondary btn-sm" onClick={onBack}>
          <ArrowLeft size={13} />
          <span>Back to Reviews</span>
        </button>
      </header>

      {/* 2. TWO-COLUMN WORKSPACE GRID */}
      <div className="pro-workspace-grid">
        {/* LEFT COLUMN: DIAGNOSTIC RADIOGRAPH VIEWPORT & GRAD-CAM OVERLAYS */}
        <div className="pro-workspace-col-left">
          {/* Medical Cinema Viewport */}
          <div className="cinema-image-stage">
            <div className="cinema-stage-toolbar">
              <div className="toolbar-title">
                <span>Diagnostic Stage</span>
                {activeHeatmapUrl && (
                  <span className="status-tag" style={{ background: "rgba(25, 211, 197, 0.15)", color: "var(--cinema-teal)", fontSize: "10px" }}>
                    Grad-CAM: {selectedHeatmapFinding}
                  </span>
                )}
              </div>

              <div className="cinema-btn-group">
                <button
                  type="button"
                  className="cinema-tool-btn"
                  onClick={() => setZoomLevel((z) => Math.max(0.8, z - 0.2))}
                  title="Zoom Out"
                >
                  <ZoomOut size={13} />
                </button>
                <button
                  type="button"
                  className="cinema-tool-btn"
                  onClick={() => setZoomLevel((z) => Math.min(2.5, z + 0.2))}
                  title="Zoom In"
                >
                  <ZoomIn size={13} />
                </button>
                <button
                  type="button"
                  className="cinema-tool-btn"
                  onClick={() => setZoomLevel(1)}
                  title="Reset Zoom"
                >
                  <RotateCcw size={13} />
                </button>
                <button
                  type="button"
                  className={`cinema-tool-btn ${isInverted ? "active" : ""}`}
                  onClick={() => setIsInverted((inv) => !inv)}
                  title="Toggle Inversion"
                >
                  Invert
                </button>
              </div>
            </div>

            <div className="cinema-viewport">
              <div
                style={{
                  position: "relative",
                  transform: `scale(${zoomLevel})`,
                  transition: "transform 150ms ease",
                  filter: isInverted ? "invert(1)" : "none",
                }}
              >
                {originalImage && (
                  <img
                    src={originalImage}
                    alt="Chest radiograph"
                    className="cinema-xray-img"
                  />
                )}

                {activeHeatmapUrl && (
                  <img
                    src={activeHeatmapUrl}
                    alt={`Grad-CAM heatmap for ${selectedHeatmapFinding}`}
                    className="cinema-xray-img"
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      width: "100%",
                      height: "100%",
                      opacity: heatmapOpacity / 100,
                      pointerEvents: "none",
                      transition: "opacity 150ms ease",
                    }}
                  />
                )}
              </div>
            </div>

            {/* Grad-CAM Opacity Slider */}
            {activeHeatmapUrl && (
              <div className="gradcam-interactive-bar">
                <div className="gradcam-slider-wrap">
                  <span className="gradcam-slider-label">Original</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={heatmapOpacity}
                    onChange={(e) => setHeatmapOpacity(Number(e.target.value))}
                    className="gradcam-slider-range"
                  />
                  <span className="gradcam-slider-label">Grad-CAM ({heatmapOpacity}%)</span>
                </div>
              </div>
            )}

            <div className="cinema-stage-footer">
              <span>{analysis.view || "Frontal"} View Radiograph</span>
              <span className="gradcam-notice-text">
                Model attention highlights influential regions for decision support.
              </span>
            </div>
          </div>

          {/* AI Decision Support Inferences List */}
          <div className="pro-card" style={{ padding: "18px" }}>
            <div className="pro-card-header" style={{ padding: "0 0 12px 0", marginBottom: "12px" }}>
              <div>
                <span className="eyebrow">AI INFERENCE</span>
                <h3 style={{ fontSize: "15px" }}>DenseNet121 Evaluated Findings</h3>
              </div>
              <span className="section-meta">{analysis.view || "Frontal"} View</span>
            </div>

            <div className="findings-list-wrap">
              {allConditionKeys.map((finding) => {
                const findingData = rawFindings[finding] || {};
                const prob = typeof findingData === "object" ? findingData.probability : findingData;
                const isDetected = typeof findingData === "object" ? findingData.detected : false;
                const thresh = typeof findingData === "object" ? findingData.threshold : 0.5;
                const isSelected = selectedHeatmapFinding === finding;
                const hasHeatmap = Boolean(rawHeatmaps[finding]);

                return (
                  <div
                    key={finding}
                    className={`finding-row-card ${isDetected ? "detected" : ""} ${isSelected ? "active-explanation" : ""}`}
                    onClick={() => hasHeatmap && setSelectedHeatmapFinding(finding)}
                    style={{ cursor: hasHeatmap ? "pointer" : "default" }}
                  >
                    <div className="finding-header-row">
                      <span className="finding-title">{finding}</span>
                      {isDetected ? (
                        <span className="finding-badge-detected">DETECTED</span>
                      ) : (
                        <span className="finding-badge-negative">NOT DETECTED</span>
                      )}
                    </div>

                    <div className="finding-progress-track">
                      <div
                        className={`finding-progress-fill ${isDetected ? "fill-detected" : ""}`}
                        style={{ width: `${Math.min((Number(prob) || 0) * 100, 100)}%` }}
                      />
                    </div>

                    <div className="finding-metrics-row">
                      <span>Model Probability: <strong>{formatPercentage(prob)}</strong></span>
                      <span>Threshold: <strong>{formatPercentage(thresh)}</strong></span>
                    </div>

                    {hasHeatmap && (
                      <button
                        type="button"
                        className="btn-view-explanation"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedHeatmapFinding(finding);
                        }}
                      >
                        <span>{isSelected ? "Active attention heatmap" : "View attention heatmap"}</span>
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: PROFESSIONAL CLINICAL ASSESSMENT DOCUMENT EDITOR */}
        <div className="pro-workspace-col-right">
          <div className="assessment-form-card">
            <div className="assessment-form-header">
              <div>
                <div className="eyebrow" style={{ color: "var(--accent-primary)" }}>
                  <Stethoscope size={12} />
                  <span>HUMAN PHYSICIAN REVIEW</span>
                </div>
                <h3 style={{ fontSize: "16px", fontWeight: "700", color: "var(--text-primary)" }}>
                  Professional Clinical Assessment
                </h3>
              </div>
              {isCompleted ? (
                <span className="patient-status-pill status-completed">
                  <CheckCircle2 size={11} />
                  <span>Signed & Completed</span>
                </span>
              ) : (
                <span className="patient-status-pill status-in-review">
                  <span>Authoring Assessment</span>
                </span>
              )}
            </div>

            {/* Patient Context Note */}
            {review_request.patient_message && (
              <div style={{
                background: "var(--surface-secondary)",
                border: "1px solid var(--border-main)",
                borderRadius: "var(--radius-md)",
                padding: "10px 14px",
                fontSize: "12px",
                marginBottom: "16px",
              }}>
                <span style={{ fontWeight: "700", color: "var(--text-muted)", textTransform: "uppercase", fontSize: "10px" }}>
                  Patient Clinical Query / Note:
                </span>
                <p style={{ fontStyle: "italic", color: "var(--text-secondary)", marginTop: "2px" }}>
                  "{review_request.patient_message}"
                </p>
              </div>
            )}

            {assessmentSuccess && (
              <div style={{
                padding: "10px 14px",
                background: "var(--color-success-bg)",
                border: "1px solid var(--color-success-border)",
                borderRadius: "var(--radius-md)",
                color: "var(--color-success-text)",
                fontSize: "12px",
                fontWeight: "600",
                marginBottom: "14px",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}>
                <CheckCircle2 size={14} />
                <span>{assessmentSuccess}</span>
              </div>
            )}

            {assessmentError && (
              <div className="validation-error-card" style={{ marginBottom: "14px" }}>
                <div className="val-error-header">
                  <AlertTriangle size={14} />
                  <span>{typeof assessmentError === "string" ? assessmentError : extractErrorMessage(assessmentError)}</span>
                </div>
              </div>
            )}

            {/* Assessment Fields (Document Editor Style) */}
            <div className="form-group">
              <label htmlFor="clinicalObservations" className="form-label">
                Clinical Observations
              </label>
              <textarea
                id="clinicalObservations"
                rows="4"
                className="form-textarea"
                placeholder="Describe thoracic and osseous observations, lung fields, cardiac silhouette, diaphragm, and soft tissue..."
                value={formData.clinical_observations}
                onChange={(e) => setFormData((prev) => ({ ...prev, clinical_observations: e.target.value }))}
                disabled={isCompleted || isSubmitting || isSavingDraft}
              />
            </div>

            <div className="form-group">
              <label htmlFor="professionalImpression" className="form-label">
                Professional Impression
              </label>
              <textarea
                id="professionalImpression"
                rows="3"
                className="form-textarea"
                placeholder="State your clinical impression and correlation with AI findings..."
                value={formData.professional_impression}
                onChange={(e) => setFormData((prev) => ({ ...prev, professional_impression: e.target.value }))}
                disabled={isCompleted || isSubmitting || isSavingDraft}
              />
            </div>

            <div className="form-group">
              <label htmlFor="recommendations" className="form-label">
                Recommendations & Next Steps
              </label>
              <textarea
                id="recommendations"
                rows="3"
                className="form-textarea"
                placeholder="Recommended diagnostic follow-ups, clinical correlation, or patient advice..."
                value={formData.recommendations}
                onChange={(e) => setFormData((prev) => ({ ...prev, recommendations: e.target.value }))}
                disabled={isCompleted || isSubmitting || isSavingDraft}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "14px" }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label htmlFor="urgencySelect" className="form-label">Clinical Urgency</label>
                <select
                  id="urgencySelect"
                  className="form-select"
                  value={formData.urgency}
                  onChange={(e) => setFormData((prev) => ({ ...prev, urgency: e.target.value }))}
                  disabled={isCompleted || isSubmitting || isSavingDraft}
                >
                  <option value="ROUTINE">Routine</option>
                  <option value="PRIORITY">Priority</option>
                  <option value="URGENT">Urgent</option>
                  <option value="EMERGENCY">Emergency</option>
                </select>
              </div>

              <div className="form-group" style={{ margin: 0, justifyContent: "center" }}>
                <label className="form-label">Formal Follow-up</label>
                <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", cursor: isCompleted ? "default" : "pointer", marginTop: "6px" }}>
                  <input
                    type="checkbox"
                    checked={formData.follow_up}
                    onChange={(e) => setFormData((prev) => ({ ...prev, follow_up: e.target.checked }))}
                    disabled={isCompleted || isSubmitting || isSavingDraft}
                  />
                  <span>Recommend physician follow-up</span>
                </label>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="additionalNotes" className="form-label">
                Additional Clinical Notes
              </label>
              <textarea
                id="additionalNotes"
                rows="2"
                className="form-textarea"
                placeholder="Optional notes or references for clinical record..."
                value={formData.additional_notes}
                onChange={(e) => setFormData((prev) => ({ ...prev, additional_notes: e.target.value }))}
                disabled={isCompleted || isSubmitting || isSavingDraft}
              />
            </div>

            {/* Actions */}
            {!isCompleted && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "18px", paddingTop: "14px", borderTop: "1px solid var(--border-subtle)" }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleSaveDraft}
                  disabled={isSavingDraft || isSubmitting}
                >
                  <Save size={14} />
                  <span>{isSavingDraft ? "Saving Draft..." : "Save Draft"}</span>
                </button>

                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleInitiateSubmit}
                  disabled={isSavingDraft || isSubmitting}
                >
                  <Check size={14} />
                  <span>Submit & Sign Review</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* CONFIRMATION MODAL */}
      {showConfirmModal && (
        <div className="modal-overlay" onClick={() => setShowConfirmModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "460px" }}>
            <div className="modal-header">
              <div>
                <span className="eyebrow">FINAL CONFIRMATION</span>
                <h3 style={{ fontSize: "16px", fontWeight: "700" }}>Sign and Finalize Clinical Assessment</h3>
              </div>
              <button className="modal-close-btn" onClick={() => setShowConfirmModal(false)}>
                <X size={16} />
              </button>
            </div>
            <div className="modal-body" style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
              <p>
                You are about to sign and submit this clinical assessment for <strong>{formatCaseId(review_request.id)}</strong>.
              </p>
              <p style={{ marginTop: "8px" }}>
                Once submitted, this review will be finalized, timestamped with your medical credentials, and made available to the patient.
              </p>
              <div className="modal-actions" style={{ marginTop: "16px" }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowConfirmModal(false)}
                >
                  Return to Edit
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleConfirmSubmit}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Signing..." : "Confirm & Sign"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
