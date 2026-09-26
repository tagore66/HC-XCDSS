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

  // Background canvas animation ref
  const canvasRef = useRef(null);
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

  // --------------------------------------------------------------------------
  // CINEMATIC LIVING CHEST X-RAY / AI VISION BACKGROUND ENGINE
  // Multi-layered radiographic anatomy, volumetric lung parenchymal haze,
  // contour-guided flow particles, soft scanning activation field, and Grad-CAM
  // perceptual heatmaps with multi-depth parallax inertia.
  // --------------------------------------------------------------------------
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId;
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let cssW = window.innerWidth;
    let cssH = window.innerHeight;
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;

    const handleResize = () => {
      if (!canvas) return;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      cssW = window.innerWidth;
      cssH = window.innerHeight;
      canvas.width = cssW * dpr;
      canvas.height = cssH * dpr;
    };

    window.addEventListener("resize", handleResize);

    // Mouse parallax tracking with smooth dampening
    let targetMouseX = 0;
    let targetMouseY = 0;
    let smoothMouseX = 0;
    let smoothMouseY = 0;

    const handlePointerMove = (e) => {
      const halfW = window.innerWidth / 2;
      const halfH = window.innerHeight / 2;
      targetMouseX = (e.clientX - halfW) / (halfW || 1);
      targetMouseY = (e.clientY - halfH) / (halfH || 1);
    };

    window.addEventListener("pointermove", handlePointerMove, { passive: true });

    // Contour-guided particles that travel along anatomical pathways
    const particleCount = 48;
    const contourParticles = Array.from({ length: particleCount }, (_, idx) => ({
      pathIndex: idx % 6, // 0: Left Bronchus, 1: Right Bronchus, 2: Left Ribs, 3: Right Ribs, 4: Left Diaphragm, 5: Right Diaphragm
      progress: Math.random(),
      speed: 0.0018 + Math.random() * 0.0022,
      baseRadius: 1.2 + Math.random() * 1.5,
      alpha: 0.25 + Math.random() * 0.5,
    }));

    let time = 0;

    const render = () => {
      time += 0.008;

      // Smooth mouse interpolation
      smoothMouseX += (targetMouseX - smoothMouseX) * 0.045;
      smoothMouseY += (targetMouseY - smoothMouseY) * 0.045;

      // Use standard DPR transform and clear in CSS pixels
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, cssW, cssH);

      // Scale down anatomical visualization to ~70% and center naturally behind hero
      const centerX = cssW * 0.5;
      const centerY = Math.min(Math.max(cssH * 0.40, 240), 370);
      const scale = Math.min(Math.max(cssW / 1400, 0.55), 0.85) * 0.72;

      // Slow organic respiration breathing cycle (T ~ 9.0s)
      const breath = 1.0 + Math.sin(time * 0.68) * 0.022;
      const breathY = Math.sin(time * 0.68) * 4.5;

      // Continuous harmonic scanning envelope (gentle ambient wave)
      const scanPhase = time * 0.72;
      const scanCenterY = centerY + Math.sin(scanPhase) * (140 * scale);
      const scanSpan = 180 * scale;

      // Helper function: calculate soft scan illumination boost
      const getScanBoost = (itemY) => {
        const dist = Math.abs(itemY - scanCenterY);
        if (dist > scanSpan) return 0;
        return Math.cos((dist / scanSpan) * (Math.PI / 2)) * 0.25;
      };

      // ======================================================================
      // LAYER 1: VOLUMETRIC LUNG PARENCHYMA HAZE (SOFT RADIOGRAPHIC DEPTH)
      // ======================================================================
      const deepParallaxX = smoothMouseX * 10;
      const deepParallaxY = smoothMouseY * 7;

      ctx.save();
      ctx.translate(centerX + deepParallaxX, centerY + breathY * 0.6 + deepParallaxY);

      // Left Lung Parenchymal Volumetric Wash
      const leftParenchymaGrad = ctx.createRadialGradient(
        -150 * scale * breath,
        20 * scale,
        25 * scale,
        -150 * scale * breath,
        20 * scale,
        220 * scale
      );
      leftParenchymaGrad.addColorStop(0, "rgba(20, 184, 166, 0.14)");
      leftParenchymaGrad.addColorStop(0.55, "rgba(20, 184, 166, 0.05)");
      leftParenchymaGrad.addColorStop(1, "rgba(20, 184, 166, 0)");

      ctx.fillStyle = leftParenchymaGrad;
      ctx.beginPath();
      ctx.ellipse(-150 * scale * breath, 20 * scale, 130 * scale * breath, 195 * scale, -0.1, 0, Math.PI * 2);
      ctx.fill();

      // Right Lung Parenchymal Volumetric Wash
      const rightParenchymaGrad = ctx.createRadialGradient(
        150 * scale * breath,
        20 * scale,
        25 * scale,
        150 * scale * breath,
        20 * scale,
        220 * scale
      );
      rightParenchymaGrad.addColorStop(0, "rgba(20, 184, 166, 0.13)");
      rightParenchymaGrad.addColorStop(0.55, "rgba(20, 184, 166, 0.045)");
      rightParenchymaGrad.addColorStop(1, "rgba(20, 184, 166, 0)");

      ctx.fillStyle = rightParenchymaGrad;
      ctx.beginPath();
      ctx.ellipse(150 * scale * breath, 20 * scale, 130 * scale * breath, 195 * scale, 0.1, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      // ======================================================================
      // LAYER 2: GRAD-CAM PERCEPTUAL ATTENTION HEATMAP FIELDS
      // ======================================================================
      const heatParallaxX = smoothMouseX * 14;
      const heatParallaxY = smoothMouseY * 10;

      ctx.save();
      // Left basilar / costophrenic attention field (Soft Diagnostic Teal)
      const leftHeatX = centerX - 180 * scale * breath + heatParallaxX;
      const leftHeatY = centerY + 130 * scale + breathY + heatParallaxY;
      const leftScanBoost = getScanBoost(leftHeatY);
      const leftHeatR = (120 + Math.sin(time * 0.9) * 18) * scale;
      const leftGrad = ctx.createRadialGradient(leftHeatX, leftHeatY, 0, leftHeatX, leftHeatY, leftHeatR);
      leftGrad.addColorStop(0, `rgba(20, 184, 166, ${0.22 + leftScanBoost * 0.18})`);
      leftGrad.addColorStop(0.55, `rgba(20, 184, 166, ${0.07 + leftScanBoost * 0.10})`);
      leftGrad.addColorStop(1, "rgba(20, 184, 166, 0)");
      ctx.fillStyle = leftGrad;
      ctx.beginPath();
      ctx.arc(leftHeatX, leftHeatY, leftHeatR, 0, Math.PI * 2);
      ctx.fill();

      // Right basilar / costophrenic attention field (Soft Diagnostic Teal)
      const rightHeatX = centerX + 180 * scale * breath + heatParallaxX;
      const rightHeatY = centerY + 130 * scale + breathY + heatParallaxY;
      const rightScanBoost = getScanBoost(rightHeatY);
      const rightHeatR = (115 + Math.cos(time * 0.8) * 16) * scale;
      const rightGrad = ctx.createRadialGradient(rightHeatX, rightHeatY, 0, rightHeatX, rightHeatY, rightHeatR);
      rightGrad.addColorStop(0, `rgba(20, 184, 166, ${0.20 + rightScanBoost * 0.18})`);
      rightGrad.addColorStop(0.55, `rgba(20, 184, 166, ${0.06 + rightScanBoost * 0.10})`);
      rightGrad.addColorStop(1, "rgba(20, 184, 166, 0)");
      ctx.fillStyle = rightGrad;
      ctx.beginPath();
      ctx.arc(rightHeatX, rightHeatY, rightHeatR, 0, Math.PI * 2);
      ctx.fill();

      // Soft Mediastinal / Cardiac border attention field with organic Amber flare
      const heartHeatX = centerX - 50 * scale + heatParallaxX;
      const heartHeatY = centerY + 80 * scale + breathY + heatParallaxY;
      const heartScanBoost = getScanBoost(heartHeatY);
      const heartPulse = Math.sin(time * 1.1) * 0.5 + 0.5;
      const heartHeatR = (115 + heartPulse * 16) * scale;
      const heartGrad = ctx.createRadialGradient(heartHeatX, heartHeatY, 0, heartHeatX, heartHeatY, heartHeatR);
      heartGrad.addColorStop(0, `rgba(245, 158, 11, ${0.20 + heartPulse * 0.08 + heartScanBoost * 0.18})`);
      heartGrad.addColorStop(0.55, `rgba(20, 184, 166, ${0.06 + heartScanBoost * 0.08})`);
      heartGrad.addColorStop(1, "rgba(245, 158, 11, 0)");
      ctx.fillStyle = heartGrad;
      ctx.beginPath();
      ctx.arc(heartHeatX, heartHeatY, heartHeatR, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      // ======================================================================
      // LAYER 3: TRANSLUCENT RADIOGRAPHIC ANATOMICAL CONTOURS
      // ======================================================================
      const midParallaxX = smoothMouseX * 12;
      const midParallaxY = smoothMouseY * 9;

      ctx.save();
      ctx.translate(centerX + midParallaxX, centerY + breathY + midParallaxY);

      // A. Clavicles (Soft Radiographic Collar Bones)
      const clavicleBoost = getScanBoost(centerY - 150 * scale);
      ctx.lineWidth = 1.4;
      ctx.strokeStyle = `rgba(215, 238, 248, ${0.25 + clavicleBoost * 0.20})`;

      // Left Clavicle
      ctx.beginPath();
      ctx.moveTo(-15 * scale, -145 * scale);
      ctx.bezierCurveTo(-55 * scale, -160 * scale, -150 * scale, -140 * scale, -220 * scale * breath, -165 * scale);
      ctx.stroke();

      // Right Clavicle
      ctx.beginPath();
      ctx.moveTo(15 * scale, -145 * scale);
      ctx.bezierCurveTo(55 * scale, -160 * scale, 150 * scale, -140 * scale, 220 * scale * breath, -165 * scale);
      ctx.stroke();

      // B. Midline Vertebral Column (Soft Translucent Density, No HUD Rectangles)
      const spineGrad = ctx.createLinearGradient(0, -140 * scale, 0, 150 * scale);
      spineGrad.addColorStop(0, "rgba(20, 184, 166, 0.04)");
      spineGrad.addColorStop(0.5, "rgba(20, 184, 166, 0.12)");
      spineGrad.addColorStop(1, "rgba(20, 184, 166, 0.03)");
      ctx.fillStyle = spineGrad;
      ctx.beginPath();
      ctx.rect(-5 * scale, -140 * scale, 10 * scale, 290 * scale);
      ctx.fill();

      // C. 8 Pairs of Soft Translucent Rib Contours
      for (let r = 0; r < 8; r++) {
        const rY = (r * 35 - 110) * scale;
        const widthSpread = (120 + r * 24) * scale * breath;
        const dip = (42 + r * 6) * scale;

        const ribGlobalY = centerY + rY;
        const rBoost = getScanBoost(ribGlobalY);
        const ribAlpha = 0.20 + Math.sin(time * 0.65 + r * 0.4) * 0.04 + rBoost * 0.18;

        ctx.lineWidth = 1.3;
        ctx.strokeStyle = `rgba(205, 235, 248, ${ribAlpha})`;

        // Left Rib Arc
        ctx.beginPath();
        ctx.moveTo(-12 * scale, rY - 8 * scale);
        ctx.bezierCurveTo(
          -widthSpread * 0.55,
          rY - 16 * scale,
          -widthSpread,
          rY + dip * 0.45,
          -widthSpread * 0.90,
          rY + dip
        );
        ctx.stroke();

        // Right Rib Arc
        ctx.beginPath();
        ctx.moveTo(12 * scale, rY - 8 * scale);
        ctx.bezierCurveTo(
          widthSpread * 0.55,
          rY - 16 * scale,
          widthSpread,
          rY + dip * 0.45,
          widthSpread * 0.90,
          rY + dip
        );
        ctx.stroke();
      }

      // D. Bilateral Lung Pleural Contours (Soft Radiographic Outlines)
      const lungOutlineBoost = getScanBoost(centerY + 20 * scale);
      ctx.lineWidth = 1.4;
      ctx.strokeStyle = `rgba(20, 184, 166, ${0.24 + lungOutlineBoost * 0.18})`;

      // Left Hemithorax
      ctx.beginPath();
      ctx.moveTo(-28 * scale, -150 * scale * breath);
      ctx.bezierCurveTo(-135 * scale * breath, -145 * scale, -275 * scale * breath, -30 * scale, -285 * scale * breath, 135 * scale);
      ctx.lineTo(-275 * scale * breath, 195 * scale);
      ctx.bezierCurveTo(-210 * scale * breath, 145 * scale, -105 * scale * breath, 130 * scale, -30 * scale, 170 * scale);
      ctx.stroke();

      // Right Hemithorax
      ctx.beginPath();
      ctx.moveTo(28 * scale, -150 * scale * breath);
      ctx.bezierCurveTo(135 * scale * breath, -145 * scale, 275 * scale * breath, -30 * scale, 285 * scale * breath, 135 * scale);
      ctx.lineTo(275 * scale * breath, 195 * scale);
      ctx.bezierCurveTo(210 * scale * breath, 145 * scale, 105 * scale * breath, 130 * scale, 30 * scale, 170 * scale);
      ctx.stroke();

      // E. Cardiac Silhouette Border & Aortic Arch
      const heartBoost = getScanBoost(centerY + 70 * scale);
      ctx.lineWidth = 1.4;
      ctx.strokeStyle = `rgba(20, 184, 166, ${0.26 + heartBoost * 0.18})`;

      ctx.beginPath();
      ctx.moveTo(-20 * scale, -55 * scale);
      ctx.bezierCurveTo(-34 * scale, -10 * scale, -130 * scale, 50 * scale, -140 * scale, 115 * scale);
      ctx.bezierCurveTo(-145 * scale, 160 * scale, -58 * scale, 170 * scale, -18 * scale, 170 * scale);
      ctx.stroke();

      // F. Bronchovascular Tree Arborization (Fine Delicate Branching)
      const airwayBoost = getScanBoost(centerY - 20 * scale);
      ctx.strokeStyle = `rgba(180, 230, 245, ${0.20 + airwayBoost * 0.15})`;
      ctx.lineWidth = 1.1;

      // Trachea
      ctx.beginPath();
      ctx.moveTo(0, -155 * scale);
      ctx.lineTo(0, -55 * scale);
      ctx.stroke();

      // Left Bronchial Tree
      ctx.beginPath();
      ctx.moveTo(0, -55 * scale);
      ctx.lineTo(-60 * scale, -12 * scale);
      ctx.lineTo(-120 * scale, 30 * scale);
      ctx.lineTo(-175 * scale, 95 * scale);
      ctx.moveTo(-60 * scale, -12 * scale);
      ctx.lineTo(-105 * scale, -28 * scale);
      ctx.moveTo(-120 * scale, 30 * scale);
      ctx.lineTo(-140 * scale, 65 * scale);
      ctx.stroke();

      // Right Bronchial Tree
      ctx.beginPath();
      ctx.moveTo(0, -55 * scale);
      ctx.lineTo(58 * scale, -10 * scale);
      ctx.lineTo(115 * scale, 38 * scale);
      ctx.lineTo(165 * scale, 105 * scale);
      ctx.moveTo(58 * scale, -10 * scale);
      ctx.lineTo(102 * scale, -26 * scale);
      ctx.moveTo(115 * scale, 38 * scale);
      ctx.lineTo(135 * scale, 75 * scale);
      ctx.stroke();

      ctx.restore();

      // ======================================================================
      // LAYER 4: CONTOUR-GUIDED FLOW PARTICLES (DELICATE DATA DUST)
      // ======================================================================
      const particleParallaxX = smoothMouseX * 16;
      const particleParallaxY = smoothMouseY * 12;

      ctx.save();
      ctx.translate(centerX + particleParallaxX, centerY + breathY + particleParallaxY);

      for (let i = 0; i < contourParticles.length; i++) {
        const p = contourParticles[i];
        p.progress += p.speed * 0.8;
        if (p.progress > 1) p.progress = 0;
        let px;
        let py;
        const pr = p.progress;

        // Calculate parametric position along anatomical contours
        switch (p.pathIndex) {
          case 0: // Left Bronchial Descent
            px = -pr * 175 * scale;
            py = (-55 + pr * 150) * scale;
            break;
          case 1: // Right Bronchial Descent
            px = pr * 165 * scale;
            py = (-55 + pr * 160) * scale;
            break;
          case 2: // Left 5th Rib Arc
            px = (-12 - pr * 180 * breath) * scale;
            py = (55 + Math.sin(pr * Math.PI) * 40) * scale;
            break;
          case 3: // Right 5th Rib Arc
            px = (12 + pr * 180 * breath) * scale;
            py = (55 + Math.sin(pr * Math.PI) * 40) * scale;
            break;
          case 4: // Left Diaphragm Dome
            px = (-30 - pr * 245 * breath) * scale;
            py = (170 - Math.sin(pr * Math.PI) * 40) * scale;
            break;
          case 5: // Right Diaphragm Dome
            px = (30 + pr * 245 * breath) * scale;
            py = (170 - Math.sin(pr * Math.PI) * 40) * scale;
            break;
          default:
            px = 0;
            py = 0;
        }

        const globalPY = centerY + py;
        const pBoost = getScanBoost(globalPY);
        const pAlpha = p.alpha * (0.40 + pBoost * 0.45);
        const pRadius = p.baseRadius * (0.85 + pBoost * 0.4);

        ctx.beginPath();
        ctx.arc(px, py, pRadius, 0, Math.PI * 2);
        ctx.fillStyle =
          pBoost > 0.08
            ? `rgba(30, 215, 195, ${Math.min(0.65, pAlpha + 0.2)})`
            : `rgba(185, 230, 245, ${pAlpha * 0.75})`;
        ctx.fill();
      }
      ctx.restore();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("pointermove", handlePointerMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <>
      {/* 1. CINEMATIC STARTUP BRAND INTRO */}
      {showIntro && <BrandIntro onComplete={handleIntroComplete} />}

      <div
        className={`guest-landing-root ${
          showIntro ? "guest-landing-standby" : "guest-landing-entered"
        }`}
      >
        {/* Background Living AI Vision Canvas */}
        <canvas ref={canvasRef} className="gl-bg-canvas" aria-hidden="true" />

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
