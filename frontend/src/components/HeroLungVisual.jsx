import React, { useEffect, useRef, useState, useCallback } from "react";
import "./HeroLungVisual.css";

/**
 * HC-XCDSS Cinematic Radiology Lung Visualization
 * 
 * Aesthetic Philosophy:
 * - High-end clinical AI / Radiographic imaging fidelity.
 * - Authentic anatomical asymmetry (3-lobed right lung, 2-lobed left lung with cardiac notch & lingula).
 * - Layered radiopacity: faint posterior ribs, tracheobronchial arborization, pulmonary vasculature.
 * - Subtle organic living presence: micro-saccadic eye tracking, natural autonomous blinks,
 *   slow non-linear diaphragmatic respiration, and shifting Grad-CAM attention regions.
 * - Zero cartoon/kawaii attributes: sophisticated, discrete, and medically grounded.
 */
export default function HeroLungVisual({ isScanning = false }) {
  const containerRef = useRef(null);
  const leftEyeRef = useRef(null);
  const rightEyeRef = useRef(null);

  // Smooth pupil & parallax positions
  const [leftPupilPos, setLeftPupilPos] = useState({ x: 0, y: 0 });
  const [rightPupilPos, setRightPupilPos] = useState({ x: 0, y: 0 });
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [isBlinking, setIsBlinking] = useState(false);

  // Internal animation state refs
  const mouseRef = useRef({ x: typeof window !== "undefined" ? window.innerWidth * 0.68 : 800, y: typeof window !== "undefined" ? window.innerHeight * 0.38 : 350 });
  const currentLeftPos = useRef({ x: 0, y: 0 });
  const currentRightPos = useRef({ x: 0, y: 0 });
  const currentTilt = useRef({ x: 0, y: 0 });
  const targetTilt = useRef({ x: 0, y: 0 });
  const animFrameRef = useRef(null);
  const blinkTimerRef = useRef(null);
  const timeRef = useRef(0);

  // Autonomous natural organic blinking (randomized 3.6s – 6.8s)
  const triggerBlink = useCallback(() => {
    setIsBlinking(true);
    setTimeout(() => {
      setIsBlinking(false);
      const nextDelay = 3400 + Math.random() * 3200;
      blinkTimerRef.current = setTimeout(triggerBlink, nextDelay);
    }, 160);
  }, []);

  useEffect(() => {
    blinkTimerRef.current = setTimeout(triggerBlink, 3600);
    return () => {
      if (blinkTimerRef.current) clearTimeout(blinkTimerRef.current);
    };
  }, [triggerBlink]);

  // Pointer movement tracking
  useEffect(() => {
    const handlePointerMove = (e) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };

      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      // Subtle 3D card tilt
      const dx = (e.clientX - centerX) / (window.innerWidth / 2);
      const dy = (e.clientY - centerY) / (window.innerHeight / 2);
      targetTilt.current = {
        x: Math.max(-4.5, Math.min(4.5, -dy * 4)),
        y: Math.max(-6.5, Math.min(6.5, dx * 5.5)),
      };
    };

    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
    };
  }, []);

  // Main 60fps animation loop with micro-saccades and smooth interpolation
  useEffect(() => {
    const maxRadius = 5.2; // Sophisticated, restrained pupil travel radius (px)
    const lerpFactor = 0.095; // Fluid natural gaze easing

    const animate = () => {
      timeRef.current += 0.016;
      const t = timeRef.current;

      if (!leftEyeRef.current || !rightEyeRef.current || !containerRef.current) {
        animFrameRef.current = requestAnimationFrame(animate);
        return;
      }

      const leftRect = leftEyeRef.current.getBoundingClientRect();
      const rightRect = rightEyeRef.current.getBoundingClientRect();

      const leftCenter = {
        x: leftRect.left + leftRect.width / 2,
        y: leftRect.top + leftRect.height / 2,
      };

      const rightCenter = {
        x: rightRect.left + rightRect.width / 2,
        y: rightRect.top + rightRect.height / 2,
      };

      // Calculate independent gaze targets with organic micro-saccades
      const calcGazeOffset = (center, isLeft) => {
        if (isScanning) {
          // When scanning or CTA button hovered: focused downward-inward gaze
          return { x: isLeft ? 1.4 : -1.4, y: 2.8 };
        }

        const dx = mouseRef.current.x - center.x;
        const dy = mouseRef.current.y - center.y;
        const dist = Math.hypot(dx, dy);

        if (dist < 1) return { x: 0, y: 0 };

        const angle = Math.atan2(dy, dx);
        const intensity = Math.min(1, dist / 420);
        const radius = intensity * maxRadius;

        // Subtle biological micro-saccadic drift (imperceptible lifelike oscillation)
        const microX = Math.sin(t * 1.8 + (isLeft ? 0 : 1.2)) * 0.35;
        const microY = Math.cos(t * 2.1 + (isLeft ? 0.8 : 0)) * 0.28;

        return {
          x: Math.cos(angle) * radius + microX,
          y: Math.sin(angle) * radius + microY,
        };
      };

      const targetLeft = calcGazeOffset(leftCenter, true);
      const targetRight = calcGazeOffset(rightCenter, false);

      // Smooth interpolation (lerp)
      currentLeftPos.current.x += (targetLeft.x - currentLeftPos.current.x) * lerpFactor;
      currentLeftPos.current.y += (targetLeft.y - currentLeftPos.current.y) * lerpFactor;

      currentRightPos.current.x += (targetRight.x - currentRightPos.current.x) * lerpFactor;
      currentRightPos.current.y += (targetRight.y - currentRightPos.current.y) * lerpFactor;

      currentTilt.current.x += (targetTilt.current.x - currentTilt.current.x) * 0.06;
      currentTilt.current.y += (targetTilt.current.y - currentTilt.current.y) * 0.06;

      setLeftPupilPos({ ...currentLeftPos.current });
      setRightPupilPos({ ...currentRightPos.current });
      setTilt({ ...currentTilt.current });

      animFrameRef.current = requestAnimationFrame(animate);
    };

    animFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [isScanning]);

  return (
    <div
      ref={containerRef}
      className={`hero-lung-container ${isScanning ? "hero-lung-scanning" : ""}`}
      style={{
        transform: `perspective(1000px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
      }}
      aria-hidden="true"
    >
      {/* Deep Radiographic Volumetric Ambient Aura */}
      <div className="hero-lung-radiance" />

      {/* Main High-Fidelity Radiographic Canvas */}
      <svg
        className="hero-lung-svg"
        viewBox="0 0 540 460"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          {/* Subtle Radiographic Grain / Parenchymal Noise */}
          <filter id="radGrain" x="0%" y="0%" width="100%" height="100%">
            <feTurbulence type="fractalNoise" baseFrequency="0.045" numOctaves="3" result="noise" />
            <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 0.04 0" />
            <feComposite in2="SourceGraphic" in="glare" operator="in" />
          </filter>

          {/* Radiographic Bloom Filter */}
          <filter id="radiographicSoftGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter id="hilarVascularBlur" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="1.8" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Right Lung (Viewer Left): Volumetric 3-Lobe Radiographic Density */}
          <linearGradient id="radRightLungGrad" x1="160" y1="40" x2="60" y2="400" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#142B36" stopOpacity="0.88" />
            <stop offset="35%" stopColor="#0E202B" stopOpacity="0.82" />
            <stop offset="70%" stopColor="#091720" stopOpacity="0.90" />
            <stop offset="100%" stopColor="#050E14" stopOpacity="0.96" />
          </linearGradient>

          {/* Left Lung (Viewer Right): Cardiac Notch & Lingula Radiographic Density */}
          <linearGradient id="radLeftLungGrad" x1="380" y1="40" x2="480" y2="400" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#142B36" stopOpacity="0.88" />
            <stop offset="35%" stopColor="#0E202B" stopOpacity="0.82" />
            <stop offset="65%" stopColor="#0A1822" stopOpacity="0.90" />
            <stop offset="100%" stopColor="#050E14" stopOpacity="0.96" />
          </linearGradient>

          {/* Radiographic Pleural Reflection Edge Highlight */}
          <linearGradient id="pleuraEdgeGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#5EEAD4" stopOpacity="0.45" />
            <stop offset="30%" stopColor="#14B8A6" stopOpacity="0.28" />
            <stop offset="75%" stopColor="#0D9488" stopOpacity="0.14" />
            <stop offset="100%" stopColor="#083344" stopOpacity="0.30" />
          </linearGradient>

          {/* Internal Grad-CAM Neural Attention Fields */}
          <radialGradient id="gradcamRightLobe" cx="42%" cy="62%" r="48%">
            <stop offset="0%" stopColor="#14B8A6" stopOpacity="0.32" />
            <stop offset="45%" stopColor="#0D9488" stopOpacity="0.14" />
            <stop offset="80%" stopColor="#F59E0B" stopOpacity="0.06" />
            <stop offset="100%" stopColor="#0D9488" stopOpacity="0" />
          </radialGradient>

          <radialGradient id="gradcamLeftLobe" cx="58%" cy="58%" r="46%">
            <stop offset="0%" stopColor="#2DD4BF" stopOpacity="0.30" />
            <stop offset="50%" stopColor="#0D9488" stopOpacity="0.12" />
            <stop offset="100%" stopColor="#0D9488" stopOpacity="0" />
          </radialGradient>

          {/* Subtle Ocular Lens Gradients */}
          <linearGradient id="ocularLensBezel" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2DD4BF" stopOpacity="0.65" />
            <stop offset="100%" stopColor="#0F766E" stopOpacity="0.25" />
          </linearGradient>

          <radialGradient id="ocularChamberGrad" cx="50%" cy="42%" r="56%">
            <stop offset="0%" stopColor="#0F2834" />
            <stop offset="75%" stopColor="#07141C" />
            <stop offset="100%" stopColor="#02080D" />
          </radialGradient>

          <radialGradient id="ocularIrisGrad" cx="38%" cy="38%" r="62%">
            <stop offset="0%" stopColor="#5EEAD4" />
            <stop offset="45%" stopColor="#14B8A6" />
            <stop offset="85%" stopColor="#0D9488" />
            <stop offset="100%" stopColor="#042F2E" />
          </radialGradient>

          {/* Scanning Beam Sweep Gradient */}
          <linearGradient id="radScanSweepGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="transparent" />
            <stop offset="50%" stopColor="rgba(45, 212, 191, 0.22)" />
            <stop offset="100%" stopColor="transparent" />
          </linearGradient>
        </defs>

        {/* ------------------------------------------------------------------ */}
        {/* 1. FAINT THORACIC SKELETAL FRAMEWORK (Posterior & Anterior Ribs)    */}
        {/* ------------------------------------------------------------------ */}
        <g className="thoracic-rib-cage" opacity="0.38">
          {/* Posterior Rib Arches (Subtle horizontal translucent bands) */}
          <path d="M 80 110 C 170 125 370 125 460 110" stroke="rgba(255, 255, 255, 0.04)" strokeWidth="11" strokeLinecap="round" fill="none" />
          <path d="M 64 165 C 160 185 380 185 476 165" stroke="rgba(255, 255, 255, 0.04)" strokeWidth="13" strokeLinecap="round" fill="none" />
          <path d="M 52 225 C 150 250 390 250 488 225" stroke="rgba(255, 255, 255, 0.038)" strokeWidth="14" strokeLinecap="round" fill="none" />
          <path d="M 48 290 C 150 318 390 318 492 290" stroke="rgba(255, 255, 255, 0.035)" strokeWidth="15" strokeLinecap="round" fill="none" />
          <path d="M 54 355 C 150 385 390 385 486 355" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="15" strokeLinecap="round" fill="none" />

          {/* Central Mediastinum / Spine Column Shadow */}
          <rect x="256" y="20" width="28" height="410" rx="4" fill="rgba(255, 255, 255, 0.015)" />
          {/* Aortic Knob / Arch Silhouette on left side of mediastinum */}
          <path d="M 256 120 C 275 120 292 135 292 155 C 292 170 282 182 270 188" stroke="rgba(255, 255, 255, 0.05)" strokeWidth="8" strokeLinecap="round" fill="none" />
        </g>

        {/* ------------------------------------------------------------------ */}
        {/* 2. TRACHEOBRONCHIAL TREE (Anatomical Carina & Mainstem Bronchi)   */}
        {/* ------------------------------------------------------------------ */}
        <g className="tracheobronchial-tree" opacity="0.82">
          {/* Trachea with Cartilage C-Rings */}
          <path
            d="M 257 24 L 283 24 L 281 88 L 259 88 Z"
            fill="#091822"
            stroke="url(#pleuraEdgeGrad)"
            strokeWidth="1.4"
          />
          {[36, 48, 60, 72, 84].map((y) => (
            <line
              key={y}
              x1="258"
              y1={y}
              x2="282"
              y2={y}
              stroke="rgba(94, 234, 212, 0.28)"
              strokeWidth="1.1"
            />
          ))}

          {/* Carina Bifurcation & Main Bronchi */}
          {/* Right Main Bronchus (Shorter, steeper, ~25° from midline) */}
          <path
            d="M 259 88 C 250 108 226 130 196 148"
            stroke="url(#pleuraEdgeGrad)"
            strokeWidth="2.4"
            strokeLinecap="round"
            fill="none"
          />
          {/* Left Main Bronchus (Longer, more horizontal, ~45° under aortic arch) */}
          <path
            d="M 281 88 C 292 108 322 130 355 146"
            stroke="url(#pleuraEdgeGrad)"
            strokeWidth="2.2"
            strokeLinecap="round"
            fill="none"
          />
        </g>

        {/* ------------------------------------------------------------------ */}
        {/* 3. LIVING ASYMMETRIC LUNG PAIR (Organic Diaphragmatic Motion)      */}
        {/* ------------------------------------------------------------------ */}
        <g className="hero-lung-pair-group">
          {/* ================================================================ */}
          {/* RIGHT LUNG (Viewer's Left): 3 Lobes, Elevated Hepatic Dome       */}
          {/* ================================================================ */}
          <g className="lung-lobe-anatomical-right">
            {/* Primary Radiographic Parenchyma */}
            <path
              className="lung-parenchyma-path"
              d="M 236 102
                 C 214 66 174 58 138 72
                 C 94 90 62 142 50 216
                 C 38 290 42 344 70 380
                 C 96 414 154 408 188 388
                 C 212 374 226 342 232 292
                 C 238 242 238 158 236 102 Z"
              fill="url(#radRightLungGrad)"
              stroke="url(#pleuraEdgeGrad)"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />

            {/* Shifting Internal Grad-CAM Heatmap Attention Core */}
            <path
              className="lung-heatmap-glow-right"
              d="M 228 114
                 C 208 80 172 72 142 84
                 C 104 100 74 148 64 216
                 C 54 280 56 332 80 366
                 C 102 396 150 390 178 374
                 C 200 360 214 332 220 286
                 C 226 240 226 164 228 114 Z"
              fill="url(#gradcamRightLobe)"
            />

            {/* Bronchopulmonary Vascular Arborization (Multi-generation branches) */}
            <g className="lung-vascular-branches" filter="url(#hilarVascularBlur)">
              {/* Superior Lobar Vessels */}
              <path d="M 198 140 C 172 120 148 108 126 104 M 158 115 C 145 98 132 88 120 84" stroke="rgba(45, 212, 191, 0.42)" strokeWidth="1.2" strokeLinecap="round" fill="none" />
              {/* Middle Lobar Vessels */}
              <path d="M 198 140 C 165 162 132 195 108 238 M 148 185 C 122 200 96 235 86 280" stroke="rgba(45, 212, 191, 0.48)" strokeWidth="1.4" strokeLinecap="round" fill="none" />
              {/* Inferior / Basilar Lobar Vessels */}
              <path d="M 198 140 C 190 200 178 275 174 345 M 184 240 C 158 275 148 318 144 365 M 165 295 C 132 322 118 350 114 372" stroke="rgba(45, 212, 191, 0.44)" strokeWidth="1.3" strokeLinecap="round" fill="none" />
            </g>

            {/* Horizontal Fissure (Separates Superior & Middle Lobes) */}
            <path d="M 68 238 C 112 230 172 220 228 236" stroke="rgba(94, 234, 212, 0.18)" strokeWidth="1.1" strokeDasharray="3 4" fill="none" />
            {/* Oblique Fissure (Separates Middle & Inferior Lobes) */}
            <path d="M 98 348 C 142 300 188 230 226 185" stroke="rgba(94, 234, 212, 0.15)" strokeWidth="1.1" strokeDasharray="3 4" fill="none" />
          </g>

          {/* ================================================================ */}
          {/* LEFT LUNG (Viewer's Right): 2 Lobes, Cardiac Notch & Lingula     */}
          {/* ================================================================ */}
          <g className="lung-lobe-anatomical-left">
            {/* Primary Radiographic Parenchyma with Deep Cardiac Notch */}
            <path
              className="lung-parenchyma-path"
              d="M 304 102
                 C 326 66 366 58 402 72
                 C 446 90 478 142 490 216
                 C 502 290 498 344 470 380
                 C 444 414 386 408 352 388
                 C 322 368 304 326 304 274
                 C 304 224 314 184 312 152
                 C 310 128 306 112 304 102 Z"
              fill="url(#radLeftLungGrad)"
              stroke="url(#pleuraEdgeGrad)"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />

            {/* Shifting Internal Grad-CAM Heatmap Attention Core */}
            <path
              className="lung-heatmap-glow-left"
              d="M 312 114
                 C 332 80 368 72 398 84
                 C 436 100 466 148 476 216
                 C 486 280 484 332 460 366
                 C 438 396 390 390 362 374
                 C 334 356 318 320 318 274
                 C 318 228 326 188 324 156
                 C 322 134 316 120 312 114 Z"
              fill="url(#gradcamLeftLobe)"
            />

            {/* Bronchopulmonary Vascular Arborization */}
            <g className="lung-vascular-branches" filter="url(#hilarVascularBlur)">
              {/* Superior Division */}
              <path d="M 342 142 C 368 120 394 108 418 104 M 382 115 C 395 98 410 88 424 84" stroke="rgba(45, 212, 191, 0.42)" strokeWidth="1.2" strokeLinecap="round" fill="none" />
              {/* Lingular Division (Encircling Cardiac Notch) */}
              <path d="M 342 142 C 375 162 410 195 434 238 M 392 185 C 418 200 444 235 454 280" stroke="rgba(45, 212, 191, 0.48)" strokeWidth="1.4" strokeLinecap="round" fill="none" />
              {/* Inferior / Basilar Division */}
              <path d="M 342 142 C 352 200 364 275 368 345 M 358 240 C 384 275 394 318 398 365 M 375 295 C 410 322 424 350 428 372" stroke="rgba(45, 212, 191, 0.44)" strokeWidth="1.3" strokeLinecap="round" fill="none" />
            </g>

            {/* Left Oblique Fissure */}
            <path d="M 470 232 C 424 246 364 268 316 296" stroke="rgba(94, 234, 212, 0.16)" strokeWidth="1.1" strokeDasharray="3 4" fill="none" />
          </g>

          {/* ================================================================ */}
          {/* 4. DISCRETE CLINICAL SENSORY NODES (Integrated Gaze Tracking)     */}
          {/* ================================================================ */}

          {/* --- RIGHT LUNG OCULAR NODE (Viewer's Left — Upper Hilar Zone) --- */}
          <g
            ref={leftEyeRef}
            className={`hero-ocular-node left-node ${isBlinking ? "node-blinking" : ""}`}
            transform="translate(152, 182)"
          >
            {/* Outer Clinical Bezel Ring */}
            <circle cx="0" cy="0" r="14.5" fill="#030A0F" stroke="url(#ocularLensBezel)" strokeWidth="1.4" filter="url(#radiographicSoftGlow)" />
            {/* Dark Vitreous Chamber */}
            <circle cx="0" cy="0" r="13" fill="url(#ocularChamberGrad)" />
            {/* Faint Optical Reticle Ring */}
            <circle cx="0" cy="0" r="11" stroke="rgba(45, 212, 191, 0.14)" strokeWidth="0.7" strokeDasharray="3 3" fill="none" />

            {/* Trackable Crystalline Iris & Deep Aperture Pupil */}
            <g transform={`translate(${leftPupilPos.x}, ${leftPupilPos.y})`}>
              {/* Iris Body */}
              <circle cx="0" cy="0" r="7.4" fill="url(#ocularIrisGrad)" />
              {/* Iris Micro-Collar */}
              <circle cx="0" cy="0" r="6.2" stroke="rgba(94, 234, 212, 0.55)" strokeWidth="0.6" fill="none" />
              {/* Deep Central Aperture Pupil */}
              <circle cx="0" cy="0" r="3.8" fill="#010406" />
              {/* Crisp Corneal Specular Catchlights (Authentic glassy wetness) */}
              <circle cx="-1.8" cy="-2.0" r="1.4" fill="#FFFFFF" opacity="0.95" />
              <circle cx="1.4" cy="1.4" r="0.7" fill="#FFFFFF" opacity="0.55" />
            </g>

            {/* Precision Anatomical Shutter Eyelids */}
            <path className="shutter-top" d="M -15 0 C -15 -11 15 -11 15 0 C 15 -1 15 -1 -15 -1 Z" fill="#040D14" />
            <path className="shutter-bottom" d="M -15 0 C -15 11 15 11 15 0 C 15 1 15 1 -15 1 Z" fill="#040D14" />
          </g>

          {/* --- LEFT LUNG OCULAR NODE (Viewer's Right — Asymmetric Hilar Zone) --- */}
          <g
            ref={rightEyeRef}
            className={`hero-ocular-node right-node ${isBlinking ? "node-blinking" : ""}`}
            transform="translate(388, 182)"
          >
            {/* Outer Clinical Bezel Ring */}
            <circle cx="0" cy="0" r="14.5" fill="#030A0F" stroke="url(#ocularLensBezel)" strokeWidth="1.4" filter="url(#radiographicSoftGlow)" />
            {/* Dark Vitreous Chamber */}
            <circle cx="0" cy="0" r="13" fill="url(#ocularChamberGrad)" />
            {/* Faint Optical Reticle Ring */}
            <circle cx="0" cy="0" r="11" stroke="rgba(45, 212, 191, 0.14)" strokeWidth="0.7" strokeDasharray="3 3" fill="none" />

            {/* Trackable Crystalline Iris & Deep Aperture Pupil */}
            <g transform={`translate(${rightPupilPos.x}, ${rightPupilPos.y})`}>
              {/* Iris Body */}
              <circle cx="0" cy="0" r="7.4" fill="url(#ocularIrisGrad)" />
              {/* Iris Micro-Collar */}
              <circle cx="0" cy="0" r="6.2" stroke="rgba(94, 234, 212, 0.55)" strokeWidth="0.6" fill="none" />
              {/* Deep Central Aperture Pupil */}
              <circle cx="0" cy="0" r="3.8" fill="#010406" />
              {/* Crisp Corneal Specular Catchlights */}
              <circle cx="-1.8" cy="-2.0" r="1.4" fill="#FFFFFF" opacity="0.95" />
              <circle cx="1.4" cy="1.4" r="0.7" fill="#FFFFFF" opacity="0.55" />
            </g>

            {/* Precision Anatomical Shutter Eyelids */}
            <path className="shutter-top" d="M -15 0 C -15 -11 15 -11 15 0 C 15 -1 15 -1 -15 -1 Z" fill="#040D14" />
            <path className="shutter-bottom" d="M -15 0 C -15 11 15 11 15 0 C 15 1 15 1 -15 1 Z" fill="#040D14" />
          </g>
        </g>
      </svg>
    </div>
  );
}
