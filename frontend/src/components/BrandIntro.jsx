import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { Activity } from "lucide-react";

/**
 * HC-XCDSS Premium Cinematic Brand Reveal
 * 
 * Rendered via createPortal directly into document.body to ensure
 * a true full-viewport overlay unaffected by parent transforms, margins, or header.
 * 
 * Precise Sequence & Timings (~5.2s total):
 * 0.0–0.30s (300ms): Dark canvas settles (#080D12)
 * 0.3–1.90s (1600ms): Large dominant ECG draws across screen (75-85% viewport width)
 * 1.35–1.55s (200ms): QRS spike impact at apex
 * 1.55–2.05s (500ms): Radial glow pulse (0.2 -> 2.5) & logo emergence
 * 2.05–2.45s (400ms): Logo settles with overshoot (0.65 -> 1.08 -> 1.0)
 * 2.45–2.65s (200ms): Quiet moment / hold
 * 2.65–3.50s (850ms): HC-XCDSS wordmark horizontal clip-path mask reveal (clean left -> right)
 * 3.50–3.80s (300ms): Wordmark dwell hold
 * 3.80–4.40s (600ms): Clinical Decision Support tagline deliberate fade & settle
 * 4.40–4.75s (350ms): Complete lockup hold
 * 4.75–5.20s (450ms): Smooth dissolve transition into landing page
 */
export default function BrandIntro({ onComplete }) {
  const [phase, setPhase] = useState("canvas");
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  // Lock body scrolling during intro overlay and restore cleanly on unmount
  useEffect(() => {
    if (typeof document === "undefined") return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, []);

  const handleSkip = () => {
    setPhase("dissolve");
    setTimeout(() => {
      if (onCompleteRef.current) onCompleteRef.current();
    }, 150);
  };

  // Keyboard shortcut (Escape / Space) to skip intro
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" || e.key === " ") {
        handleSkip();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    // Honors prefers-reduced-motion
    const prefersReducedMotion =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReducedMotion) {
      if (onCompleteRef.current) onCompleteRef.current();
      return;
    }

    const tSignal = setTimeout(() => setPhase("signal"), 300);
    const tImpact = setTimeout(() => setPhase("impact"), 1350);
    const tBrand = setTimeout(() => setPhase("brand"), 1550);
    const tSettle = setTimeout(() => setPhase("settle"), 2050);
    const tHoldLogo = setTimeout(() => setPhase("holdLogo"), 2450);
    const tWordmark = setTimeout(() => setPhase("wordmark"), 2650);
    const tHoldWordmark = setTimeout(() => setPhase("holdWordmark"), 3500);
    const tTagline = setTimeout(() => setPhase("tagline"), 3800);
    const tHoldFull = setTimeout(() => setPhase("holdFull"), 4400);
    const tDissolve = setTimeout(() => setPhase("dissolve"), 4750);
    const tComplete = setTimeout(() => {
      if (onCompleteRef.current) onCompleteRef.current();
    }, 5200);

    return () => {
      clearTimeout(tSignal);
      clearTimeout(tImpact);
      clearTimeout(tBrand);
      clearTimeout(tSettle);
      clearTimeout(tHoldLogo);
      clearTimeout(tWordmark);
      clearTimeout(tHoldWordmark);
      clearTimeout(tTagline);
      clearTimeout(tHoldFull);
      clearTimeout(tDissolve);
      clearTimeout(tComplete);
    };
  }, []);

  const hasImpacted = [
    "impact",
    "brand",
    "settle",
    "holdLogo",
    "wordmark",
    "holdWordmark",
    "tagline",
    "holdFull",
    "dissolve",
  ].includes(phase);

  const isLogoVisible = [
    "brand",
    "settle",
    "holdLogo",
    "wordmark",
    "holdWordmark",
    "tagline",
    "holdFull",
    "dissolve",
  ].includes(phase);

  const isWordmarkVisible = [
    "wordmark",
    "holdWordmark",
    "tagline",
    "holdFull",
    "dissolve",
  ].includes(phase);

  const isTaglineVisible = [
    "tagline",
    "holdFull",
    "dissolve",
  ].includes(phase);

  const overlayContent = (
    <div
      className={`cinematic-intro-overlay ${phase === "dissolve" ? "cinematic-dissolving" : ""}`}
      aria-hidden="true"
    >
      {/* Background Soft Diagnostic Ambient Glow */}
      <div className={`cinematic-ambient-glow ${phase !== "canvas" ? "active" : ""}`} />

      {/* Main Cinematic Viewport Stage */}
      <div className={`cinematic-stage phase-${phase}`}>
        {/* Large Dominant Diagnostic ECG Waveform */}
        <div className={`cinematic-signal-container ${hasImpacted ? "receding" : ""}`}>
          <svg
            className="cinematic-large-ecg-svg"
            viewBox="0 0 1000 240"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              <linearGradient id="largeSignalGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#19D3C5" stopOpacity="0.15" />
                <stop offset="42%" stopColor="#19D3C5" stopOpacity="0.85" />
                <stop offset="50%" stopColor="#3DE8DD" stopOpacity="1" />
                <stop offset="58%" stopColor="#19D3C5" stopOpacity="0.85" />
                <stop offset="100%" stopColor="#19D3C5" stopOpacity="0.15" />
              </linearGradient>
              <filter id="largeSignalGlow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Subtle baseline grid line */}
            <line
              x1="0"
              y1="120"
              x2="1000"
              y2="120"
              stroke="rgba(25, 211, 197, 0.08)"
              strokeWidth="1.2"
              strokeDasharray="4 4"
            />

            {/* Large Diagnostic Signal Path */}
            <path
              className={`cinematic-large-signal-path ${phase !== "canvas" ? "drawing" : ""}`}
              d="M 0 120 L 260 120 C 290 120 305 102 325 102 C 345 102 360 120 390 120 L 440 120 L 460 142 L 500 12 L 535 205 L 560 120 L 610 120 C 635 120 655 85 685 85 C 715 85 735 120 760 120 L 1000 120"
              stroke="url(#largeSignalGrad)"
              strokeWidth="3.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              filter="url(#largeSignalGlow)"
            />
          </svg>
        </div>

        {/* Brand Reveal & Focal Lockup Area */}
        <div className={`cinematic-brand-stage ${isLogoVisible ? "active" : ""}`}>
          {/* QRS Radial Glow Pulse */}
          <div className={`cinematic-radial-pulse ${phase === "brand" ? "pulsing" : ""}`} />

          {/* Secondary Soft Outer Illumination */}
          <div className={`cinematic-backdrop-glow ${isLogoVisible ? "visible" : ""}`} />

          {/* Central Logo Box (116px desktop, 86px mobile) */}
          <div className={`cinematic-logo-box ${isLogoVisible ? "emerged" : ""}`}>
            <Activity className="cinematic-logo-icon" />
          </div>

          {/* Wordmark and Tagline Lockup */}
          <div className="cinematic-typography-group">
            <div className={`cinematic-title-container ${isWordmarkVisible ? "revealed" : ""}`}>
              <h1 className="cinematic-wordmark-title">HC-XCDSS</h1>
            </div>
            <div className={`cinematic-tagline-container ${isTaglineVisible ? "revealed" : ""}`}>
              <p className="cinematic-tagline-text">Clinical Decision Support</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  if (typeof document === "undefined") {
    return overlayContent;
  }

  return createPortal(overlayContent, document.body);
}
