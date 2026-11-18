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
  HelpCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Shield,
  Eye,
} from "lucide-react";

function formatCaseId(id) {
  if (!id) return "—";
  const clean = String(id).replace(/^#/, "");
  return `Case #${clean.substring(0, 8).toUpperCase()}`;
}

const FINDING_SHORT_SUMMARIES = {
  Atelectasis: "an area of the lung may not be fully expanded.",
  Cardiomegaly: "the heart appears enlarged on the X-ray.",
  Consolidation: "an area of the lung that is normally air-filled appears dense or hazy.",
  Edema: "diffuse haziness suggests fluid accumulation within lung tissues.",
  "Pleural Effusion": "signs of fluid collecting in the space around the lung.",
};

export default function ResultsScreen({
  result,
  preview,
  view,
  currentUser,
  onResetAnalysis,
  onBackToHistory,
  onOpenMyReviews,
}) {
  const isPhysician = currentUser?.role === "PROFESSIONAL";
  const userRole = isPhysician ? "professional" : "patient";

  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewSuccessMessage, setReviewSuccessMessage] = useState("");
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isInverted, setIsInverted] = useState(false);
  const [selectedHeatmapFinding, setSelectedHeatmapFinding] = useState(
    result?.detected_findings?.[0] || Object.keys(result?.heatmaps || {})[0] || "Atelectasis"
  );
  const [heatmapOpacity, setHeatmapOpacity] = useState(100); // 0 (original) to 100 (heatmap)
  const [showTechnicalData, setShowTechnicalData] = useState(isPhysician); // Physicians see technical specs by default

  // AI Assistant programmatic launch state
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [assistantPrompt, setAssistantPrompt] = useState("");

  const analysisView = result?.view || view || "Frontal";
  const targetAnalysisId = result?.analysis_id || result?.id;
  const originalImage = preview || (result?.image ? getHeatmapUrl(result.image) : null);
  const activeHeatmapPath = selectedHeatmapFinding && result?.heatmaps?.[selectedHeatmapFinding];
  const activeHeatmapUrl = activeHeatmapPath ? getHeatmapUrl(activeHeatmapPath) : null;

  const handleReviewSuccess = (reviewData) => {
    const caseRef = reviewData?.id ? reviewData.id.substring(0, 8).toUpperCase() : "—";
    setReviewSuccessMessage(`Professional review request #${caseRef} submitted and dispatched.`);
  };

  const detectedFindings = result?.detected_findings || [];
  const detectedCount = detectedFindings.length;
  const evaluatedCount = Object.keys(result?.findings || {}).length || 5;

  const allFindingNames = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion",
  ];

  const notDetectedFindings = allFindingNames.filter(
    (name) => !detectedFindings.includes(name)
  );

  const handleLaunchAssistantWithPrompt = (promptText) => {
    setAssistantPrompt(promptText);
    setAssistantOpen(true);
  };

  return (
    <section className="results-screen-container">
      {/* TOP TITLE & ACTION BAR */}
      <div className="results-top-bar">
        <div className="results-title-group">
          <div className="eyebrow">
            <Activity size={12} />
            <span>AI DECISION SUPPORT RESULT</span>
          </div>
          <h2>Chest Radiograph Analysis & Explanation</h2>
          <div className="results-case-meta">
            <span>{formatCaseId(targetAnalysisId)}</span>
            <span>•</span>
            <span>{analysisView} Projection</span>
          </div>
        </div>

        <div className="results-actions-group">
          {targetAnalysisId && (
            <button type="button" className="btn-secondary btn-sm" onClick={onBackToHistory}>
              <ArrowLeft size={13} />
              <span>History</span>
            </button>
          )}

          {!isPhysician && (
            <button
              type="button"
              className="btn-review-cta btn-sm"
              onClick={() => setShowReviewModal(true)}
              style={{
                padding: "7px 14px",
                fontSize: "12.5px",
                background: "linear-gradient(135deg, #059669 0%, #047857 100%)",
                border: "1px solid #10B981",
                color: "#FFFFFF",
                borderRadius: "var(--radius-sm)",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                fontWeight: "600",
                cursor: "pointer",
              }}
              title="Request a verified doctor or radiologist review"
            >
              <Stethoscope size={14} />
              <span>Ask Doctor / Review</span>
            </button>
          )}

          <button type="button" className="btn-primary btn-sm" onClick={onResetAnalysis}>
            <Plus size={13} />
            <span>New Analysis</span>
          </button>
        </div>
      </div>

      {/* SECTION 1: WHAT THIS ANALYSIS MEANS (PATIENT-FIRST SYNTHESIS) */}
      <div className="narrative-synthesis-card">
        <div className="narrative-card-header">
          <div className="narrative-badge-group">
            <span className="narrative-stage-pill">PATIENT SUMMARY</span>
            <span className={`detection-status-pill ${detectedCount > 0 ? "status-flagged" : "status-unremarkable"}`}>
              {detectedCount > 0 ? `${detectedCount} Finding(s) Flagged by AI` : "No Findings Flagged by AI"}
            </span>
          </div>
          <span className="narrative-projection-meta">{analysisView} View Evaluation</span>
        </div>

        <div className="narrative-body-block">
          <h3 className="narrative-headline">What this analysis means</h3>

          {detectedCount > 0 ? (
            <div className="synthesis-flagged-block">
              <p className="synthesis-intro-text">
                The AI flagged <strong>{detectedCount === 1 ? "one finding" : `${detectedCount} findings`}</strong> for further attention:
              </p>

              <ul className="synthesis-findings-list">
                {detectedFindings.map((finding) => (
                  <li key={finding} className="synthesis-finding-item">
                    <strong className="synthesis-finding-name">{finding}</strong> —{" "}
                    <span className="synthesis-finding-desc">
                      {FINDING_SHORT_SUMMARIES[finding] || "visual pattern flagged for clinical attention."}
                    </span>
                  </li>
                ))}
              </ul>

              {notDetectedFindings.length > 0 && (
                <p className="synthesis-unflagged-note">
                  The AI did not flag the other findings it evaluates:{" "}
                  <strong>{notDetectedFindings.map((f) => f.toLowerCase()).join(", ")}</strong>.
                </p>
              )}
            </div>
          ) : (
            <div className="synthesis-unflagged-block">
              <p className="synthesis-intro-text">
                The AI did not flag any of the 5 findings it evaluates (
                <em>Atelectasis, Cardiomegaly, Consolidation, Edema, Pleural Effusion</em>) on this view.
              </p>
            </div>
          )}

          {/* Core Clinical Context Disclaimer */}
          <div className="synthesis-clinical-disclaimer">
            <p style={{ margin: 0 }}>
              These are AI-generated findings, not a diagnosis. Their significance depends on your symptoms, medical history, physical examination, and other clinical information.
            </p>
          </div>
        </div>
      </div>

      {/* TWO-COLUMN DIAGNOSTIC WORKSTATION (HERO VIEWPORT 58% + FINDINGS HIERARCHY 42%) */}
      <div className="diagnostic-workstation-grid">
        {/* LEFT COLUMN (58%): MEDICAL CINEMA DIAGNOSTIC VIEWPORT */}
        <div className="cinema-image-stage" id="visual-attention-section">
          <div className="cinema-stage-toolbar">
            <div className="toolbar-title">
              <span className="viewport-title-text">AI VISUAL ATTENTION VIEWPORT</span>
              {activeHeatmapUrl ? (
                <span className="status-tag gradcam-active-tag">
                  AI Focus: {selectedHeatmapFinding}
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

          {/* Finding Switcher Bar */}
          <div className="cinema-finding-switcher">
            <span className="switcher-label">View AI Focus For:</span>
            <div className="switcher-chips-wrap">
              {allFindingNames.map((findingName) => {
                const isSelected = selectedHeatmapFinding === findingName;
                const isDetected = detectedFindings.includes(findingName);

                return (
                  <button
                    key={findingName}
                    type="button"
                    className={`switcher-chip ${isSelected ? "active" : ""} ${isDetected ? "detected" : ""}`}
                    onClick={() => {
                      setSelectedHeatmapFinding(findingName);
                      if (heatmapOpacity === 0) setHeatmapOpacity(100);
                    }}
                  >
                    {isDetected && <span className="chip-dot" />}
                    <span>{findingName}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Radiograph Viewport */}
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

              {/* Grad-CAM Heatmap Overlay with Crossfade */}
              {activeHeatmapUrl && (
                <img
                  src={activeHeatmapUrl}
                  alt={`Model visual attention heatmap for ${selectedHeatmapFinding}`}
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

          {/* Grad-CAM Interactive Crossfade Slider */}
          {activeHeatmapUrl && (
            <div className="gradcam-interactive-bar">
              <div className="gradcam-slider-wrap">
                <span className="gradcam-slider-label">Original (0%)</span>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={heatmapOpacity}
                  onChange={(e) => setHeatmapOpacity(Number(e.target.value))}
                  className="gradcam-slider-range"
                  aria-label="Model visual attention overlay opacity"
                />
                <span className="gradcam-slider-label">AI Focus Overlay ({heatmapOpacity}%)</span>
              </div>
            </div>
          )}

          {/* Educational Callout: Where Did the AI Focus? */}
          <div className="gradcam-educational-box">
            <div className="gradcam-edu-title">
              <Eye size={14} color="var(--cinema-teal)" />
              <span>This shows where the AI model focused when producing this finding.</span>
            </div>
            <p className="gradcam-edu-text">
              The highlighted area represents model attention for <strong>{selectedHeatmapFinding}</strong>. It is not a disease boundary, segmentation, or proof that disease is present.
            </p>
          </div>
        </div>

        {/* RIGHT COLUMN (42%): FINDINGS BREAKDOWN & HIERARCHY */}
        <FindingsGrid
          findings={result.findings}
          view={analysisView}
          selectedFinding={selectedHeatmapFinding}
          onSelectFinding={(finding) => {
            setSelectedHeatmapFinding(finding);
            if (heatmapOpacity === 0) setHeatmapOpacity(100);
          }}
        />
      </div>

      {/* STAGE 3: VERIFIED SPECIALIST SECOND OPINION CTA BANNER (For Patients) */}
      {targetAnalysisId && !isPhysician && (
        <div className="professional-review-cta-card">
          <div className="cta-text-block">
            <div className="cta-eyebrow-green">
              <Stethoscope size={13} />
              <span>STAGE 3 • VERIFIED SPECIALIST SECOND OPINION</span>
            </div>
            <h3 className="cta-title">Want a Qualified Medical Professional to Review Your Result?</h3>
            <p className="cta-desc">
              Have a board-verified doctor or radiologist independently inspect this radiograph, review the AI model activations, and deliver an official clinical review.
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

      {/* STAGE 4: HUMAN-CENTRED CLINICAL GUIDE & EXPLANATIONS */}
      <PatientExplanations
        findings={result.findings}
        detectedFindings={detectedFindings}
        patientExplanations={result.patient_explanations || []}
        selectedFinding={selectedHeatmapFinding}
        onSelectFinding={(f) => setSelectedHeatmapFinding(f)}
      />

      {/* STAGE 5: CLINICAL SAFETY & DECISION SUPPORT GUIDELINES */}
      <ClinicalNotice />

      {/* STAGE 6: STILL HAVE QUESTIONS? (AI ASSISTANT INTERACTIVE LAUNCHPAD) */}
      <div className="ai-questions-launchpad-card">
        <div className="launchpad-header">
          <div className="launchpad-icon-wrap">
            <Sparkles size={18} color="var(--accent-primary)" />
          </div>
          <div>
            <div className="eyebrow" style={{ color: "var(--accent-primary)" }}>
              STAGE 6 • STILL HAVE QUESTIONS?
            </div>
            <h3 className="launchpad-title">
              {isPhysician ? "Query Clinical AI Case Context" : "Ask about your X-ray"}
            </h3>
            <p className="launchpad-desc">
              {isPhysician
                ? "DenseNet121 model outputs, view-specific operating thresholds, and Grad-CAM spatial activation are loaded."
                : "I already have your analysis, findings and visual explanation. Ask me anything about this result."}
            </p>
          </div>
        </div>

        <div className="launchpad-prompt-chips">
          {isPhysician ? (
            <>
              <button
                type="button"
                className="launchpad-chip"
                onClick={() => handleLaunchAssistantWithPrompt("Evaluate radiological correlation with operating thresholds.")}
              >
                <span>📊 Evaluate Operating Thresholds</span>
              </button>

              <button
                type="button"
                className="launchpad-chip"
                onClick={() => handleLaunchAssistantWithPrompt("Explain the Grad-CAM spatial activation on this view.")}
              >
                <span>🔍 Grad-CAM Attention</span>
              </button>

              <button
                type="button"
                className="launchpad-chip"
                onClick={() => handleLaunchAssistantWithPrompt("What did the AI find on this radiograph?")}
              >
                <span>📋 Findings Breakdown</span>
              </button>

              <button
                type="button"
                className="launchpad-chip"
                onClick={() => handleLaunchAssistantWithPrompt("What are the clinical limitations of this AI prediction?")}
              >
                <span>🛡️ Model Limitations</span>
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="launchpad-chip"
                onClick={() => handleLaunchAssistantWithPrompt("What did the AI find?")}
              >
                <span>💬 What did the AI find?</span>
              </button>

              <button
                type="button"
                className="launchpad-chip"
                onClick={() => handleLaunchAssistantWithPrompt("Why was this area highlighted?")}
              >
                <span>🔍 Why was this area highlighted?</span>
              </button>

              <button
                type="button"
                className="launchpad-chip"
                onClick={() => handleLaunchAssistantWithPrompt("What does this finding mean?")}
              >
                <span>📖 What does this finding mean?</span>
              </button>

              <button
                type="button"
                className="launchpad-chip"
                onClick={() => handleLaunchAssistantWithPrompt("Why did the AI flag this?")}
              >
                <span>🎯 Why did the AI flag this?</span>
              </button>

              <button
                type="button"
                className="launchpad-chip"
                onClick={() => handleLaunchAssistantWithPrompt("What should I ask my doctor?")}
              >
                <span>📋 What should I ask my doctor?</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* SECTION 8: DETAILED TECHNICAL DATA (EXPANDABLE AT BOTTOM FOR CLINICIANS / CURIOUS USERS) */}
      <div className="technical-deepdive-container">
        <button
          type="button"
          className="technical-toggle-btn"
          onClick={() => setShowTechnicalData((prev) => !prev)}
        >
          <div className="tech-toggle-left">
            <Sliders size={14} />
            <span>STAGE 8 • Detailed Technical Data & Model Operating Parameters (Optional)</span>
          </div>
          <div className="tech-toggle-right">
            <span>{showTechnicalData ? "Hide Technical Specifications" : "View Technical Specifications"}</span>
            {showTechnicalData ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>
        </button>

        {showTechnicalData && (
          <div className="technical-expanded-panel">
            <div className="tech-specs-grid">
              <div className="tech-spec-card">
                <span className="tech-spec-label">Model Architecture</span>
                <span className="tech-spec-value">DenseNet-121 (CheXpert Backbone)</span>
                <span className="tech-spec-desc">121 convolutional layers with dense connectivity; features.norm5 Grad-CAM hook.</span>
              </div>
              <div className="tech-spec-card">
                <span className="tech-spec-label">Input Resolution</span>
                <span className="tech-spec-value">320 × 320 px (Single-Channel Grayscale)</span>
                <span className="tech-spec-desc">Standardized ImageNet normalization (mean=0.485, std=0.229).</span>
              </div>
              <div className="tech-spec-card">
                <span className="tech-spec-label">Projection Setting</span>
                <span className="tech-spec-value">{analysisView} Specific Operating Thresholds</span>
                <span className="tech-spec-desc">Operating thresholds selected from Stanford CheXpert validation data.</span>
              </div>
            </div>

            <div className="tech-thresholds-table-wrap">
              <table className="tech-thresholds-table">
                <thead>
                  <tr>
                    <th>Finding</th>
                    <th>Model Output</th>
                    <th>Operating Decision Threshold</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.findings || {}).map(([name, data]) => {
                    const prob = Number(data.probability) || 0;
                    const thresh = Number(data.threshold) || 0.5;
                    const isDetected = data.detected;

                    return (
                      <tr key={name} className={isDetected ? "row-tech-detected" : ""}>
                        <td style={{ fontWeight: "600" }}>{name}</td>
                        <td>{prob.toFixed(3)}</td>
                        <td>{thresh.toFixed(3)}</td>
                        <td>
                          <span className={isDetected ? "badge-detected-amber" : "badge-not-detected"}>
                            {isDetected ? "AI FLAGGED" : "NOT FLAGGED BY THE AI"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* FLOATING AI CLINICAL ASSISTANT DRAWER */}
      {targetAnalysisId && (
        <AIAssistant
          analysis={result}
          role={userRole}
          externalOpen={assistantOpen}
          onCloseExternal={() => {
            setAssistantOpen(false);
            setAssistantPrompt("");
          }}
          initialPrompt={assistantPrompt}
        />
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
