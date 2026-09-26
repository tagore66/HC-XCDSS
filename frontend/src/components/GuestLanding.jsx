import { useState, useEffect, useRef, useCallback } from "react";
import BrandIntro from "./BrandIntro";
import HeroLungVisual from "./HeroLungVisual";
import { getAuthToken } from "../services/api";
import "./GuestLanding.css";
import {
  Activity,
  ArrowRight,
  Stethoscope,
  Shield,
  Sliders,
  CheckCircle2,
  Play,
  Pause,
  RotateCcw,
  Sparkles,
  Eye,
  Layers,
  FileText,
} from "lucide-react";

// In-memory runtime tracking across SPA route transitions within the same document lifecycle
let hasPlayedIntroInSpaRuntime = false;

// Demonstration Clinical Cases with authentic X-Ray and Grad-CAM assets
const demoCases = [
  {
    id: "case-01",
    tag: "Case 01",
    name: "Pleural Effusion (Left Basilar)",
    xraySrc: "/sample_xray.jpg",
    gradcamSrc: "/sample_gradcam.jpg",
    roiLabel: "ROI [X: 620, Y: 580] • Left Basilar Recess",
    roiStyle: { left: "48%", top: "38%", width: "36%", height: "38%" },
    findings: [
      { name: "Pleural Effusion", prob: 89.2, target: true, status: "High Probability" },
      { name: "Atelectasis", prob: 64.3, target: false, status: "Secondary Finding" },
      { name: "Cardiomegaly", prob: 22.1, target: false, status: "Normal Limit" },
      { name: "Consolidation", prob: 14.8, target: false, status: "Unlikely" },
      { name: "Pulmonary Edema", prob: 11.0, target: false, status: "Unlikely" },
    ],
    primaryFinding: "Pleural Effusion (Left Basilar) • 89.2%",
    findingDetail:
      "Blunting of the left costophrenic angle with homogeneous fluid opacity layering in the dependent hemithorax.",
    plainExplanation:
      "The AI identified fluid accumulation in the lower left lung base (pleural space). This visual pattern is highlighted in warm colors on the Grad-CAM overlay and indicates a pleural effusion requiring clinical evaluation.",
  },
  {
    id: "case-02",
    tag: "Case 02",
    name: "Cardiomegaly (Cardiac Margin)",
    xraySrc: "/sample_xray_02.jpg",
    gradcamSrc: "/sample_gradcam_02.jpg",
    roiLabel: "ROI [X: 290, Y: 380] • Cardiac Silhouette",
    roiStyle: { left: "26%", top: "36%", width: "46%", height: "42%" },
    findings: [
      { name: "Cardiomegaly", prob: 86.7, target: true, status: "High Probability" },
      { name: "Pulmonary Edema", prob: 71.3, target: false, status: "Secondary Finding" },
      { name: "Pleural Effusion", prob: 18.4, target: false, status: "Unlikely" },
      { name: "Atelectasis", prob: 24.5, target: false, status: "Unlikely" },
      { name: "Consolidation", prob: 12.1, target: false, status: "Unlikely" },
    ],
    primaryFinding: "Cardiomegaly (Enlarged Cardiac Silhouette) • 86.7%",
    findingDetail:
      "Transverse cardiothoracic ratio exceeds 0.55 with left ventricular contour prominence and perihilar vascular fullness.",
    plainExplanation:
      "The model detected an enlarged heart shadow that occupies more than half the chest width, accompanied by mild vascular prominence. This finding is clearly visualized by the gradient attention map.",
  },
];

// The 6 Continuous Diagnostic Transformation Phases
const signatureSteps = [
  {
    step: "01",
    phase: "REAL CHEST X-RAY",
    title: "Raw Radiograph Ingestion",
    caption: "Frontal PA projection calibrated with DICOM-grade exposure verification.",
    defaultCamOpacity: 0.0,
    showScanLine: false,
    showRoi: false,
    activeLayer: "DICOM Input Viewport",
    stageStatus: "Baseline Anatomy Verified",
    narrative:
      "Input frontal chest radiograph (PA projection) loaded at full dynamic range. Automated preprocessing calibrates thoracic orientation, contrast balance, and anatomical boundary markers.",
  },
  {
    step: "02",
    phase: "AI ANALYSIS",
    title: "Multi-Label DenseNet-121 Inference",
    caption: "Deep convolutional feature extraction across 121 interconnected neural layers.",
    defaultCamOpacity: 0.15,
    showScanLine: true,
    showRoi: false,
    activeLayer: "Neural Feature Extractor",
    stageStatus: "Multi-Label Inference Active",
    narrative:
      "The DenseNet-121 architecture executes simultaneous multi-label feature extraction across 5 critical cardiopulmonary pathologies, computing layer-wise activation gradients across all lung zones.",
  },
  {
    step: "03",
    phase: "ATTENTION EMERGES",
    title: "Spatial Region Localization",
    caption: "Algorithmic gradient vectors isolate highest-activation anatomical coordinates.",
    defaultCamOpacity: 0.45,
    showScanLine: false,
    showRoi: true,
    activeLayer: "Spatial Attention Reticle",
    stageStatus: "Attention Coordinates Locked",
    narrative:
      "Gradient flow backpropagates to the final convolutional layer (norm5), isolating specific thoracic coordinates with high diagnostic relevance and projecting a targeted region-of-interest reticle.",
  },
  {
    step: "04",
    phase: "REAL GRAD-CAM OVERLAY",
    title: "Gradient-Weighted Activation Map",
    caption: "Pixel-accurate thermal overlay revealing exact visual evidence driving the model.",
    defaultCamOpacity: 0.85,
    showScanLine: false,
    showRoi: true,
    activeLayer: "Grad-CAM Heatmap Blend",
    stageStatus: "Visual Explanation Rendered",
    narrative:
      "A true Grad-CAM activation heatmap is overlaid onto the original radiograph. Warm spectrum (red/amber) denotes primary attention, while cool spectrum (teal/blue) marks secondary parenchymal reference.",
  },
  {
    step: "05",
    phase: "STRUCTURED FINDING",
    title: "Deterministic Clinical Classification",
    caption: "Calibrated probability distribution across all 5 target cardiopulmonary conditions.",
    defaultCamOpacity: 0.85,
    showScanLine: false,
    showRoi: true,
    activeLayer: "Calibrated Diagnostic Engine",
    stageStatus: "Finding Classified & Scored",
    narrative:
      "Multi-label predictions are deterministically calibrated against validation thresholds. The system outputs quantitative probability scores, primary diagnostic finding, and anatomical localization metadata.",
  },
  {
    step: "06",
    phase: "UNDERSTANDABLE EXPLANATION",
    title: "Human-Centred Clinical Translation",
    caption: "Dual-tier synthesis providing clear plain-language communication for patients and clinicians.",
    defaultCamOpacity: 0.75,
    showScanLine: false,
    showRoi: true,
    activeLayer: "Dual-Tier Reporting Layer",
    stageStatus: "Review & Consultation Ready",
    narrative:
      "Technical findings are translated into clear, patient-friendly explanations to demystify complex medical imaging, empowering informed discussions with verified specialist physicians.",
  },
];

export default function GuestLanding({ onOpenAuth, currentUser }) {
  // Cinematic startup animation state (plays on page load/refresh for unauthenticated visitors)
  const [showIntro, setShowIntro] = useState(() => {
    if (typeof window === "undefined") return false;

    // Authenticated user check: never play intro for logged-in users
    if (currentUser || getAuthToken()) {
      hasPlayedIntroInSpaRuntime = true;
      return false;
    }

    // Accessibility check: honors prefers-reduced-motion
    const prefersReducedMotion =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) {
      hasPlayedIntroInSpaRuntime = true;
      return false;
    }

    // SPA navigation check: do not replay on internal SPA route transitions
    if (hasPlayedIntroInSpaRuntime) {
      return false;
    }

    // First document load / refresh for unauthenticated user: play intro
    hasPlayedIntroInSpaRuntime = true;
    return true;
  });

  // Active Demo Case state (Case 1 vs Case 2)
  const [activeCaseIndex, setActiveCaseIndex] = useState(0);
  const currentCase = demoCases[activeCaseIndex] || demoCases[0];

  // Signature Sequence Step (0 to 5)
  const [signatureStep, setSignatureStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const [isInView, setIsInView] = useState(false);
  const [isHeroBtnHovered, setIsHeroBtnHovered] = useState(false);

  // Manual Grad-CAM Opacity Override (null when following step default)
  const [manualOpacity, setManualOpacity] = useState(null);

  const signatureSectionRef = useRef(null);

  const handleIntroComplete = useCallback(() => {
    hasPlayedIntroInSpaRuntime = true;
    setShowIntro(false);
  }, []);

  // Viewport Intersection Observer: Play/Resume demo only when user scrolls into view
  useEffect(() => {
    const el = signatureSectionRef.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setIsInView(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsInView(entry.isIntersecting);
      },
      {
        threshold: 0.25, // Starts/resumes when 25% of the demo section is visible in viewport
      }
    );

    observer.observe(el);
    return () => {
      observer.disconnect();
    };
  }, []);

  // Continuous Autoplay Timer for Signature Transformation Sequence (runs ONLY when in viewport and not paused)
  useEffect(() => {
    if (!isPlaying || showIntro || !isInView) return;
    const interval = setInterval(() => {
      setSignatureStep((prev) => (prev + 1) % signatureSteps.length);
    }, 3800);

    return () => clearInterval(interval);
  }, [isPlaying, showIntro, isInView]);

  const activePhase = signatureSteps[signatureStep] || signatureSteps[0];
  const effectiveCamOpacity =
    manualOpacity !== null ? manualOpacity : activePhase.defaultCamOpacity;


  return (
    <>
      {/* 1. CINEMATIC STARTUP BRAND INTRO */}
      {showIntro && <BrandIntro onComplete={handleIntroComplete} />}

      <div
        className={`guest-landing-root ${
          showIntro ? "guest-landing-standby" : "guest-landing-entered"
        }`}
      >

        {/* TOP SUB-NAVIGATION */}
        <nav className="gl-nav-bar" aria-label="Product Navigation">
          <div className="gl-nav-inner">
            <div
              className="gl-nav-brand"
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
            >
              <div className="gl-nav-brand-icon">
                <Activity size={15} />
              </div>
              <span className="gl-nav-brand-title">HC-XCDSS</span>
              <span className="gl-nav-brand-tag">Clinical Decision Support</span>
            </div>

            <div className="gl-nav-links">
              <a href="#signature-transformation" className="gl-nav-link">
                How HC-XCDSS Sees
              </a>
              <a href="#explainability" className="gl-nav-link">
                Explainability
              </a>
              <a href="#professional-review" className="gl-nav-link">
                Physician Review
              </a>
              <a href="#safety-notice" className="gl-nav-link">
                Clinical Governance
              </a>
            </div>

            <div className="gl-nav-actions">
              <button
                type="button"
                className="btn-gl-ghost"
                onClick={() => onOpenAuth("login")}
              >
                Sign In
              </button>
              <button
                type="button"
                className="btn-gl-primary"
                onClick={() => onOpenAuth("register", "PATIENT")}
              >
                Start Analysis
                <ArrowRight size={13} />
              </button>
            </div>
          </div>
        </nav>

        {/* 2. CINEMATIC EDITORIAL HERO */}
        <section className="gl-hero-editorial">
          <div className="gl-hero-editorial-inner">
            {/* Left Content Column: Headline, Copy & Actions */}
            <div className="gl-hero-content-col">
              {/* System Status Pill */}
              <div className="gl-hero-eyebrow-line">
                <span className="gl-eyebrow-accent-dot" />
                <span className="gl-eyebrow-text">HUMAN-CENTRED EXPLAINABLE AI</span>
              </div>

              {/* Main Editorial Headline */}
              <h1 className="gl-hero-headline">See what the scan sees.</h1>

              {/* Elevated, Atmospheric Subtitle */}
              <p className="gl-hero-subhead">
                An explainable clinical decision support framework bridging multi-label deep
                learning, visual attention mapping, and verified specialist physician review.
              </p>

              {/* Understated, Refined Entry Buttons */}
              <div className="gl-hero-actions">
                <button
                  type="button"
                  className="btn-gl-primary-hero"
                  onMouseEnter={() => setIsHeroBtnHovered(true)}
                  onMouseLeave={() => setIsHeroBtnHovered(false)}
                  onClick={() => onOpenAuth("register", "PATIENT")}
                >
                  <span>Start Patient Analysis</span>
                  <ArrowRight size={15} />
                </button>

                <button
                  type="button"
                  className="btn-gl-secondary-hero"
                  onClick={() => onOpenAuth("register", "PROFESSIONAL")}
                >
                  <Stethoscope size={15} />
                  <span>Physician Access</span>
                </button>

                <button
                  type="button"
                  className="gl-hero-text-link"
                  onClick={() => onOpenAuth("login")}
                >
                  Already registered? Sign in →
                </button>
              </div>
            </div>

            {/* Right Visual Column: Living Medical-Tech Animated Lungs */}
            <div className="gl-hero-visual-col">
              <HeroLungVisual isScanning={isHeroBtnHovered} />
            </div>
          </div>
        </section>

        {/* 3. SIGNATURE EXPERIENCE: HOW HC-XCDSS SEES (CONTINUOUS TRANSFORMATION STORY) */}
        <section
          id="signature-transformation"
          ref={signatureSectionRef}
          className="gl-section gl-signature-section"
        >
          <div className="gl-showcase-inner">
            {/* Preamble & Section Header */}
            <div className="gl-section-preamble">
              <span className="gl-preamble-tag">Visual Signature • How HC-XCDSS Sees</span>
              <h2 className="gl-preamble-title">
                The Continuous Diagnostic Transformation
              </h2>
              <p className="gl-preamble-desc">
                Follow one uninterrupted story: from raw radiograph ingestion and multi-label AI
                feature extraction to emerging spatial attention, Grad-CAM activation, and
                plain-language translation.
              </p>
            </div>

            {/* Case Selector Header Bar */}
            <div className="gl-sig-case-bar">
              <div className="sig-case-label-group">
                <span className="sig-case-caption">SELECT CLINICAL DEMONSTRATION CASE:</span>
              </div>
              <div className="sig-case-pills">
                {demoCases.map((c, idx) => {
                  const isCurrent = idx === activeCaseIndex;
                  return (
                    <button
                      key={c.id}
                      type="button"
                      className={`sig-case-pill ${isCurrent ? "active" : ""}`}
                      onClick={() => {
                        setActiveCaseIndex(idx);
                        setManualOpacity(null);
                      }}
                    >
                      <span className="case-pill-tag">{c.tag}</span>
                      <span className="case-pill-name">{c.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Continuous Story Scrubber / Interactive Timeline */}
            <div className="gl-sig-timeline-scrubber">
              <div className="sig-scrubber-controls">
                <button
                  type="button"
                  className="sig-play-toggle-btn"
                  onClick={() => setIsPlaying(!isPlaying)}
                  title={isPlaying ? "Pause Sequence" : "Play Continuous Sequence"}
                  aria-label={isPlaying ? "Pause Sequence" : "Play Continuous Sequence"}
                >
                  {isPlaying ? <Pause size={13} /> : <Play size={13} />}
                  <span>{isPlaying ? "Autoplay Active" : "Paused"}</span>
                </button>

                <button
                  type="button"
                  className="sig-reset-btn"
                  onClick={() => {
                    setSignatureStep(0);
                    setManualOpacity(null);
                    setIsPlaying(true);
                  }}
                  title="Restart Sequence from Step 01"
                >
                  <RotateCcw size={12} />
                  <span>Restart</span>
                </button>
              </div>

              {/* 6 Story Step Scrubber Pills */}
              <div className="sig-step-pills-row">
                {signatureSteps.map((stg, idx) => {
                  const isActive = idx === signatureStep;
                  const isPassed = idx < signatureStep;
                  return (
                    <button
                      key={idx}
                      type="button"
                      className={`sig-step-pill ${isActive ? "active" : ""} ${
                        isPassed ? "passed" : ""
                      }`}
                      onClick={() => {
                        setSignatureStep(idx);
                        setManualOpacity(null);
                      }}
                    >
                      <span className="pill-step-num">{stg.step}</span>
                      <span className="pill-step-phase">{stg.phase}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Main Interactive Showcase Stage (Dual Column) */}
            <div className="gl-signature-stage">
              {/* Left Column: Cinematic Medical Imaging Viewport */}
              <div className="gl-sig-viewport-col">
                <div className="gl-sig-viewport-bezel">
                  {/* Viewport Top Bar / DICOM HUD */}
                  <div className="sig-viewport-topbar">
                    <div className="sig-viewport-meta-left">
                      <span className="sig-status-light" />
                      <span className="sig-layer-badge">{activePhase.activeLayer}</span>
                    </div>
                    <div className="sig-viewport-meta-right">
                      <span className="sig-proj-badge">PA CHEST • 120 kVp</span>
                      <span className="sig-time-badge">
                        PHASE {activePhase.step}/06
                      </span>
                    </div>
                  </div>

                  {/* Radiograph Visual Stage */}
                  <div className="sig-viewport-stage">
                    {/* Layer 1: Base Chest Radiograph */}
                    <img
                      src={currentCase.xraySrc}
                      alt={`Original Radiograph for ${currentCase.name}`}
                      className="sig-base-xray-img"
                    />

                    {/* Layer 2: Live AI Scan Sweep Line (Step 2+) */}
                    <div
                      className={`sig-scan-laser-layer ${
                        activePhase.showScanLine || signatureStep === 1
                          ? "laser-active"
                          : ""
                      }`}
                    >
                      <div className="sig-scan-laser-bar" />
                      <div className="sig-scan-laser-glow" />
                    </div>

                    {/* Layer 3: Emerging Spatial Attention ROI Reticle (Step 3+) */}
                    <div
                      className={`sig-roi-reticle-box ${
                        activePhase.showRoi || signatureStep >= 2 ? "roi-visible" : ""
                      }`}
                      style={currentCase.roiStyle}
                    >
                      <div className="roi-corner top-left" />
                      <div className="roi-corner top-right" />
                      <div className="roi-corner bottom-left" />
                      <div className="roi-corner bottom-right" />
                      <div className="roi-center-crosshair" />
                      <div className="roi-meta-tag">
                        <Sparkles size={10} className="roi-tag-icon" />
                        <span>{currentCase.roiLabel}</span>
                      </div>
                    </div>

                    {/* Layer 4: Real Grad-CAM Gradient Activation Heatmap */}
                    <img
                      src={currentCase.gradcamSrc}
                      alt={`Grad-CAM Activation Map for ${currentCase.name}`}
                      className="sig-gradcam-overlay-img"
                      style={{ opacity: effectiveCamOpacity }}
                    />

                    {/* Anatomical Orientation Markers */}
                    <span className="sig-marker-tag marker-r">R</span>
                    <span className="sig-marker-tag marker-l">L</span>

                    {/* Viewport Bottom Live Overlay Pill */}
                    <div className="sig-viewport-floating-info">
                      <div className="floating-info-header">
                        <Eye size={12} className="floating-icon" />
                        <span className="floating-title">{activePhase.stageStatus}</span>
                      </div>
                      <p className="floating-caption">{activePhase.caption}</p>
                    </div>
                  </div>

                  {/* Viewport Bottom HUD & Interactive Opacity Slider */}
                  <div className="sig-viewport-controls-bottom">
                    <div className="sig-intensity-slider-group">
                      <div className="slider-label-row">
                        <span className="slider-label-text">
                          <Sliders size={12} />
                          Grad-CAM Heatmap Intensity:
                        </span>
                        <span className="slider-val-readout">
                          {Math.round(effectiveCamOpacity * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.02"
                        value={effectiveCamOpacity}
                        onChange={(e) => setManualOpacity(parseFloat(e.target.value))}
                        className="sig-slider-bar"
                        aria-label="Adjust Grad-CAM Layer Blend"
                      />
                      <div className="slider-scale-ticks">
                        <span onClick={() => setManualOpacity(0)}>0% (Raw X-Ray)</span>
                        <span onClick={() => setManualOpacity(0.5)}>50% (Balanced)</span>
                        <span onClick={() => setManualOpacity(1.0)}>100% (Thermal CAM)</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: Synchronized Clinical Reasoning Dashboard */}
              <div className="gl-sig-narrative-col">
                {/* Active Step Story Card */}
                <div className="sig-story-step-card">
                  <div className="story-step-header">
                    <div className="story-step-tag">
                      <Layers size={12} />
                      <span>PHASE {activePhase.step} OF 06</span>
                    </div>
                    <span className="story-phase-name">{activePhase.phase}</span>
                  </div>

                  <h3 className="story-step-title">{activePhase.title}</h3>
                  <p className="story-step-body">{activePhase.narrative}</p>
                </div>

                {/* Multi-Label Model Probability Spectrum (5 Target Pathologies) */}
                <div className="sig-probabilities-card">
                  <div className="prob-card-header">
                    <div className="prob-header-left">
                      <Activity size={13} className="prob-header-icon" />
                      <span className="prob-card-title">DenseNet-121 Multi-Label Vector</span>
                    </div>
                    <span className="prob-header-sub">
                      {signatureStep === 0
                        ? "Pre-Inference Baseline"
                        : signatureStep === 1
                        ? "Inference Sweeping..."
                        : "Calibrated Output"}
                    </span>
                  </div>

                  <div className="prob-items-list">
                    {currentCase.findings.map((finding, fIdx) => {
                      // Compute animated width based on current step
                      const displayPct =
                        signatureStep === 0
                          ? 0
                          : signatureStep === 1
                          ? Math.min(finding.prob * 0.6, 45)
                          : finding.prob;

                      const isTargetFinding = finding.target && signatureStep >= 2;

                      return (
                        <div
                          key={fIdx}
                          className={`prob-row-item ${isTargetFinding ? "target-highlight" : ""}`}
                        >
                          <div className="prob-row-meta">
                            <span className="prob-condition-name">{finding.name}</span>
                            <div className="prob-row-right">
                              {isTargetFinding && (
                                <span className="prob-status-badge">Target Finding</span>
                              )}
                              <span className="prob-pct-value">
                                {signatureStep === 0 ? "—" : `${displayPct.toFixed(1)}%`}
                              </span>
                            </div>
                          </div>

                          <div className="prob-track-bg">
                            <div
                              className={`prob-fill-bar ${
                                finding.target ? "fill-primary" : "fill-secondary"
                              }`}
                              style={{ width: `${displayPct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Structured Clinical Finding Readout (Highlight in Step 5+) */}
                <div
                  className={`sig-finding-callout-card ${
                    signatureStep >= 4 ? "callout-active" : ""
                  }`}
                >
                  <div className="callout-header">
                    <div className="callout-icon-wrap">
                      <CheckCircle2 size={14} />
                    </div>
                    <div>
                      <span className="callout-sub">Structured Clinical Output</span>
                      <strong className="callout-title">{currentCase.primaryFinding}</strong>
                    </div>
                  </div>
                  <p className="callout-body">{currentCase.findingDetail}</p>
                </div>

                {/* Plain-Language Understandable Patient Translation (Highlight in Step 6) */}
                <div
                  className={`sig-explanation-callout-card ${
                    signatureStep === 5 ? "explanation-active" : ""
                  }`}
                >
                  <div className="explanation-header">
                    <div className="explanation-icon-wrap">
                      <FileText size={14} />
                    </div>
                    <div>
                      <span className="explanation-sub">Patient-Centred Translation</span>
                      <strong className="explanation-title">
                        Understandable Clinical Insight
                      </strong>
                    </div>
                  </div>
                  <p className="explanation-body">{currentCase.plainExplanation}</p>
                </div>

                {/* Direct Entry CTA */}
                <div className="sig-action-row">
                  <button
                    type="button"
                    className="btn-gl-primary"
                    onClick={() => onOpenAuth("register", "PATIENT")}
                  >
                    <span>Analyze Your Chest X-Ray</span>
                    <ArrowRight size={13} />
                  </button>
                  <button
                    type="button"
                    className="btn-gl-ghost"
                    onClick={() => onOpenAuth("register", "PROFESSIONAL")}
                  >
                    <Stethoscope size={13} />
                    <span>Physician Portal</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 4. VISUAL EXPLAINABILITY & TRANSPARENCY PRINCIPLES */}
        <section id="explainability" className="gl-section gl-explain-section">
          <div className="gl-showcase-inner">
            <div className="gl-explain-layout">
              {/* Left Column: Visual Side-by-Side Verification */}
              <div className="gl-explain-media-col">
                <div className="gl-compare-stage">
                  <div className="compare-card">
                    <div className="compare-img-wrap">
                      <img src="/sample_xray.jpg" alt="Original Chest Radiograph" />
                    </div>
                    <div className="compare-meta">
                      <span className="compare-tag">Raw Radiograph</span>
                      <span className="compare-caption">Input PA Projection</span>
                    </div>
                  </div>

                  <div className="compare-card">
                    <div className="compare-img-wrap">
                      <img
                        src="/sample_gradcam.jpg"
                        alt="Grad-CAM Model Attention Map"
                        style={{ opacity: 0.8 }}
                      />
                    </div>
                    <div className="compare-meta">
                      <span className="compare-tag">Model Attention</span>
                      <span className="compare-caption">Gradient Activation Heatmap</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: Editorial Value Proposition */}
              <div className="gl-explain-text-col">
                <span className="gl-preamble-tag">Visual Transparency</span>
                <h2 className="gl-explain-heading">
                  Explainability at the Point of Care
                </h2>
                <p className="gl-explain-lead">
                  AI predictions without anatomical localization cannot be safely evaluated.
                  HC-XCDSS visualizes model attention to enable informed clinical verification.
                </p>

                <div className="gl-explain-principles">
                  <div className="principle-item">
                    <CheckCircle2 size={16} className="principle-icon" />
                    <div>
                      <strong className="principle-title">Anatomical Focus Mapping</strong>
                      <p className="principle-desc">
                        Grad-CAM highlights specific lung zones, cardiac margins, and pleural
                        spaces that drove the model's multi-label classification.
                      </p>
                    </div>
                  </div>

                  <div className="principle-item">
                    <CheckCircle2 size={16} className="principle-icon" />
                    <div>
                      <strong className="principle-title">Clinical Verification Aid</strong>
                      <p className="principle-desc">
                        Clinicians and patients can immediately compare algorithmic attention
                        against visible radiographical evidence.
                      </p>
                    </div>
                  </div>

                  <div className="principle-item">
                    <CheckCircle2 size={16} className="principle-icon" />
                    <div>
                      <strong className="principle-title">
                        Decision Support, Not Autonomous Diagnosis
                      </strong>
                      <p className="principle-desc">
                        Visual heatmaps indicate regions of model attention to assist
                        evaluation, without replacing diagnostic clinical judgment.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 5. HUMAN-IN-THE-LOOP (SPECIALIST REVIEW) */}
        <section id="professional-review" className="gl-section gl-review-section">
          <div className="gl-showcase-inner">
            <div className="gl-review-layout">
              <div className="gl-review-editorial-col">
                <span className="gl-preamble-tag">Human-Centred AI</span>
                <h2 className="gl-review-heading">Specialist Physician Second Opinions</h2>
                <p className="gl-review-lead">
                  AI decision support is most powerful when paired with licensed clinical
                  oversight. Patients can seamlessly request an independent second opinion
                  from credentialed medical specialists.
                </p>

                <div className="gl-review-timeline">
                  <div className="timeline-node">
                    <div className="node-badge">01</div>
                    <div className="node-content">
                      <strong className="node-title">Patient Review Request</strong>
                      <p className="node-desc">
                        Patients request an independent specialist review directly following
                        analysis.
                      </p>
                    </div>
                  </div>

                  <div className="timeline-node">
                    <div className="node-badge">02</div>
                    <div className="node-content">
                      <strong className="node-title">Specialist Case Examination</strong>
                      <p className="node-desc">
                        Reviewing physicians evaluate high-resolution radiographs with
                        multi-layer Grad-CAM overlays.
                      </p>
                    </div>
                  </div>

                  <div className="timeline-node">
                    <div className="node-badge">03</div>
                    <div className="node-content">
                      <strong className="node-title">Immutable Clinical Addendum</strong>
                      <p className="node-desc">
                        The physician confirms or revises findings and produces a signed clinical
                        assessment.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="gl-review-actions">
                  <button
                    type="button"
                    className="btn-gl-secondary-hero"
                    onClick={() => onOpenAuth("register", "PROFESSIONAL")}
                  >
                    <Stethoscope size={15} />
                    <span>Physician Portal Access</span>
                  </button>
                </div>
              </div>

              {/* Review Card Presentation */}
              <div className="gl-review-card-col">
                <div className="gl-physician-consult-card">
                  <div className="consult-header">
                    <div className="consult-badge-wrap">
                      <span className="consult-pill">Specialist Review Sample</span>
                    </div>
                    <span className="consult-status">Verified Assessment</span>
                  </div>

                  <div className="consult-quote">
                    "Bilateral costophrenic angle blunting noted, consistent with dependent
                    pleural fluid collections. Compressive basilar volume loss. Moderate
                    cardiac enlargement confirmed."
                  </div>

                  <div className="consult-signoff">
                    <Stethoscope size={16} className="consult-doctor-icon" />
                    <div>
                      <span className="doctor-name">Dr. M. Vance, MD</span>
                      <span className="doctor-cred">Board Certified Radiologist</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 6. CLINICAL GOVERNANCE & SAFETY NOTICE */}
        <section id="safety-notice" className="gl-section gl-safety-section">
          <div className="gl-showcase-inner">
            <div className="gl-safety-notice-card">
              <div className="safety-icon-wrapper">
                <Shield size={20} />
              </div>
              <div className="safety-text-group">
                <h3 className="safety-card-title">
                  Clinical Decision Support Platform Notice
                </h3>
                <p className="safety-card-body">
                  HC-XCDSS is an investigational Clinical Decision Support System designed to
                  assist healthcare professionals and empower patients with structured
                  radiographic insights. Model predictions and Grad-CAM visual heatmaps are
                  assistive aids and do not constitute confirmed medical diagnoses or replace
                  licensed physician judgment.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* 7. FINAL EDITORIAL CALL TO ACTION */}
        <section className="gl-section gl-cta-editorial-section">
          <div className="gl-showcase-inner">
            <div className="gl-cta-monolith">
              <h2 className="gl-cta-heading">Explore your X-ray with clarity.</h2>
              <p className="gl-cta-subhead">
                Experience multi-label deep learning analysis paired with transparent visual
                Grad-CAM explainability and physician second opinions.
              </p>

              <div className="gl-cta-button-row">
                <button
                  type="button"
                  className="btn-gl-primary-hero"
                  onClick={() => onOpenAuth("register", "PATIENT")}
                >
                  <span>Start Patient Analysis</span>
                  <ArrowRight size={15} />
                </button>

                <button
                  type="button"
                  className="btn-gl-secondary-hero"
                  onClick={() => onOpenAuth("register", "PROFESSIONAL")}
                >
                  <Stethoscope size={15} />
                  <span>Physician Access</span>
                </button>
              </div>

              <button
                type="button"
                className="gl-cta-signin-link"
                onClick={() => onOpenAuth("login")}
              >
                Already have an account? Sign in to your workspace →
              </button>
            </div>
          </div>
        </section>

        {/* 8. MINIMALIST EDITORIAL FOOTER */}
        <footer className="gl-editorial-footer">
          <div className="gl-showcase-inner">
            <div className="footer-top-row">
              <div className="footer-brand-lockup">
                <div className="footer-brand-icon">
                  <Activity size={15} />
                </div>
                <div>
                  <span className="footer-brand-title">HC-XCDSS</span>
                  <span className="footer-brand-subtitle">
                    Human-Centred Explainable AI
                  </span>
                </div>
              </div>

              <div className="footer-nav-links">
                <a href="#signature-transformation" className="footer-link">
                  How HC-XCDSS Sees
                </a>
                <a href="#explainability" className="footer-link">
                  Explainability
                </a>
                <a href="#professional-review" className="footer-link">
                  Physician Review
                </a>
                <a href="#safety-notice" className="footer-link">
                  Clinical Governance
                </a>
              </div>
            </div>

            <div className="footer-horizontal-divider" />

            <div className="footer-bottom-row">
              <p className="footer-disclaimer-text">
                HC-XCDSS provides AI-assisted radiographic findings to support clinical
                evaluation. Model predictions and visual heatmaps are not confirmed medical
                diagnoses.
              </p>
              <p className="footer-copyright-text">
                &copy; {new Date().getFullYear()} HC-XCDSS Framework. All rights reserved.
              </p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}
