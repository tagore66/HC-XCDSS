import { useState } from "react";
import { getHeatmapUrl } from "../services/api";
import FindingsGrid from "./FindingsGrid";
import PatientExplanations from "./PatientExplanations";
import ClinicalNotice from "./ClinicalNotice";
import RequestReviewModal from "./RequestReviewModal";
import AIAssistant from "./AIAssistant";
import {
  Activity,
  ArrowLeft,
  Plus,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sliders,
  Sparkles,
  Stethoscope,
  CheckCircle2,
  Maximize2,
  FileText,
  Info,
  Layers,
} from "lucide-react";

function formatCaseId(id) {
  if (!id) return "—";
  const clean = String(id).replace(/^#/, "");
  return `Case #${clean.substring(0, 8).toUpperCase()}`;
}

export default function ResultsScreen({
  result,
  preview,
  view,
  onResetAnalysis,
  onBackToHistory,
  onOpenMyReviews,
}) {
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewSuccessMessage, setReviewSuccessMessage] = useState("");
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isInverted, setIsInverted] = useState(false);
  const [selectedHeatmapFinding, setSelectedHeatmapFinding] = useState(
    result?.detected_findings?.[0] || Object.keys(result?.heatmaps || {})[0] || null
  );
  const [heatmapOpacity, setHeatmapOpacity] = useState(100); // 0 (original) to 100 (heatmap)

  const analysisView = result?.view || view;
  const originalImage = preview || (result?.image ? getHeatmapUrl(result.image) : null);
  const activeHeatmapPath = selectedHeatmapFinding && result?.heatmaps?.[selectedHeatmapFinding];
  const activeHeatmapUrl = activeHeatmapPath ? getHeatmapUrl(activeHeatmapPath) : null;

  const handleReviewSuccess = (reviewData) => {
    const caseRef = reviewData?.id ? reviewData.id.substring(0, 8).toUpperCase() : "—";
    setReviewSuccessMessage(`Professional review request #${caseRef} submitted and dispatched.`);
  };

  const detectedCount = result.detected_findings?.length || 0;
  const evaluatedCount = Object.keys(result.findings || {}).length;

  return (
    <section className="results-screen-container">
      {/* 1. TOP TITLE & ACTION BAR */}
      <div className="results-top-bar">
        <div className="results-title-group">
          <div className="eyebrow">
            <Activity size={12} />
            <span>AI DECISION SUPPORT RESULT</span>
          </div>
          <h2>Chest Radiograph Analysis</h2>
          <div className="results-case-meta">
            <span>{formatCaseId(result.analysis_id)}</span>
            <span>•</span>
            <span>{analysisView} Projection</span>
          </div>
        </div>

        <div className="results-actions-group">
          {result.analysis_id && (
            <button type="button" className="btn-secondary btn-sm" onClick={onBackToHistory}>
              <ArrowLeft size={13} />
              <span>History</span>
            </button>
          )}

          <button type="button" className="btn-primary btn-sm" onClick={onResetAnalysis}>
            <Plus size={13} />
            <span>New Analysis</span>
          </button>
        </div>
      </div>

      {/* 2. SUMMARY STRIP */}
      <div className="results-summary-ribbon">
        <div className="ribbon-item">
          <span className="ribbon-label">Projection</span>
          <span className="ribbon-val">{analysisView} View</span>
        </div>
        <div className="ribbon-item">
          <span className="ribbon-label">Findings Evaluated</span>
          <span className="ribbon-val">{evaluatedCount} Conditions</span>
        </div>
        <div className="ribbon-item">
          <span className="ribbon-label">Detection Status</span>
          <span className={`ribbon-val ${detectedCount > 0 ? "detected-positive" : "detected-negative"}`}>
            {detectedCount > 0
              ? `${detectedCount} Finding(s) Detected Above Threshold`
              : "No Acute Findings Detected"}
          </span>
        </div>
      </div>

      {/* 3. PRIMARY DIAGNOSTIC WORKSPACE (Hero Viewport 58% + Hierarchical Findings 42%) */}
      <div className="diagnostic-workstation-grid">
        {/* Left: Medical Cinema Diagnostic Viewport (Visual Hero) */}
        <div className="cinema-image-stage">
          <div className="cinema-stage-toolbar">
            <div className="toolbar-title">
              <span className="viewport-title-text">Diagnostic Viewport</span>
              {activeHeatmapUrl ? (
                <span className="status-tag gradcam-active-tag">
                  Grad-CAM: {selectedHeatmapFinding}
                </span>
              ) : (
                <span className="status-tag original-active-tag">
                  Original Radiograph
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
                title="Toggle Radiograph Inversion"
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
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {/* Base Original Radiograph */}
              {originalImage && (
                <img
                  src={originalImage}
                  alt="Chest radiograph"
                  className="cinema-xray-img"
                />
              )}

              {/* Grad-CAM Heatmap Overlay with Crossfade/Opacity Slider */}
              {activeHeatmapUrl && (
                <img
                  src={activeHeatmapUrl}
                  alt={`Grad-CAM model attention heatmap for ${selectedHeatmapFinding}`}
                  className="cinema-xray-img"
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: "100%",
                    opacity: heatmapOpacity / 100,
                    pointerEvents: "none",
                    transition: "opacity 180ms ease",
                  }}
                />
              )}
            </div>
          </div>

          {/* Grad-CAM Interactive Opacity Slider */}
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
                  aria-label="Grad-CAM overlay opacity"
                />
                <span className="gradcam-slider-label">Grad-CAM ({heatmapOpacity}%)</span>
              </div>
            </div>
          )}

          <div className="cinema-stage-footer">
            <span>Projection: {analysisView}</span>
            <span className="gradcam-notice-text">
              Model attention overlays indicate spatial regions that influenced the CheXpert prediction.
            </span>
          </div>
        </div>

        {/* Right: Hierarchical Radiographic Findings */}
        <FindingsGrid
          findings={result.findings}
          view={analysisView}
          selectedFinding={selectedHeatmapFinding}
          onSelectFinding={(finding) => {
            setSelectedHeatmapFinding(finding);
            if (!heatmapOpacity) setHeatmapOpacity(100);
          }}
        />
      </div>

      {/* 4. PROFESSIONAL REVIEW CTA (GREEN / EMERALD HUMAN VERIFICATION BANNER) */}
      {result.analysis_id && (
        <div className="professional-review-cta-card">
          <div className="cta-text-block">
            <div className="cta-eyebrow-green">
              <Stethoscope size={13} />
              <span>VERIFIED SPECIALIST SECOND OPINION</span>
            </div>
            <h3 className="cta-title">Request Professional Clinical Review</h3>
            <p className="cta-desc">
              Have a board-verified medical specialist independently review this radiograph, inspect AI model predictions and Grad-CAM activations, and provide verified clinical recommendations.
            </p>
          </div>

          {reviewSuccessMessage ? (
            <div className="review-success-banner">
              <CheckCircle2 size={16} />
              <span>{reviewSuccessMessage}</span>
              {onOpenMyReviews && (
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={onOpenMyReviews}
                  style={{ marginLeft: "8px" }}
                >
                  View My Doctor Reviews →
                </button>
              )}
            </div>
          ) : (
            <button
              type="button"
              className="btn-review-cta"
              onClick={() => setShowReviewModal(true)}
            >
              <Stethoscope size={15} />
              <span>Request Doctor Review</span>
            </button>
          )}
        </div>
      )}

      {/* 5. PATIENT GUIDANCE / LAY EXPLANATIONS */}
      <PatientExplanations patientExplanations={result.patient_explanations} />

      {/* 6. CLINICAL SAFETY NOTICE */}
      <ClinicalNotice />

      {/* 7. FLOATING AI CLINICAL ASSISTANT (BOTTOM RIGHT LAUNCHER) */}
      {result.analysis_id && (
        <AIAssistant analysis={result} initialRole="patient" />
      )}

      {/* REVIEW REQUEST MODAL */}
      {showReviewModal && (
        <RequestReviewModal
          analysis={result}
          onClose={() => setShowReviewModal(false)}
          onSuccess={handleReviewSuccess}
        />
      )}
    </section>
  );
}
