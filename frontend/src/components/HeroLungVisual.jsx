import React, { useEffect, useRef, useState, useCallback } from "react";
import "./HeroLungVisual.css";

/**
 * HC-XCDSS Premium Living Medical-Tech Lung Visualization
 * 
 * Features:
 * - Two stylized anatomical lung lobes with subtle, sophisticated personified eyes.
 * - Smooth GPU-accelerated cursor tracking with independent pupil gaze and binocular convergence.
 * - Organic breathing cycle with subtle chest expansion.
 * - Internal radiographic / Grad-CAM visual attention glow.
 * - Natural autonomous blink cycle.
 * - Subtle 3D parallax tilt reactive to cursor distance.
 * - Interactive focus reaction when user hovers over the primary call to action.
 * - Full prefers-reduced-motion compliance.
 */
export default function HeroLungVisual({ isScanning = false }) {
  const containerRef = useRef(null);
  const leftEyeRef = useRef(null);
  const rightEyeRef = useRef(null);

  // Pupil smooth position state (lerped in rAF)
  const [leftPupilPos, setLeftPupilPos] = useState({ x: 0, y: 0 });
  const [rightPupilPos, setRightPupilPos] = useState({ x: 0, y: 0 });
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [isBlinking, setIsBlinking] = useState(false);

  // Internal animation state refs
  const mouseRef = useRef({ x: window.innerWidth * 0.7, y: window.innerHeight * 0.35 });
  const currentLeftPos = useRef({ x: 0, y: 0 });
  const currentRightPos = useRef({ x: 0, y: 0 });
  const currentTilt = useRef({ x: 0, y: 0 });
  const targetTilt = useRef({ x: 0, y: 0 });
  const animFrameRef = useRef(null);
  const blinkTimerRef = useRef(null);

  // Autonomous natural blinking effect (random interval 3.8s - 6.5s)
  const triggerBlink = useCallback(() => {
    setIsBlinking(true);
    setTimeout(() => {
      setIsBlinking(false);
      const nextDelay = 3500 + Math.random() * 3000;
      blinkTimerRef.current = setTimeout(triggerBlink, nextDelay);
    }, 180);
  }, []);

  useEffect(() => {
    blinkTimerRef.current = setTimeout(triggerBlink, 3800);
    return () => {
      if (blinkTimerRef.current) clearTimeout(blinkTimerRef.current);
    };
  }, [triggerBlink]);

  // Pointer move handler
  useEffect(() => {
    const handlePointerMove = (e) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };

      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      // Calculate subtle 3D tilt
      const dx = (e.clientX - centerX) / (window.innerWidth / 2);
      const dy = (e.clientY - centerY) / (window.innerHeight / 2);
      targetTilt.current = {
        x: Math.max(-6, Math.min(6, -dy * 5)),
        y: Math.max(-8, Math.min(8, dx * 7)),
      };
    };

    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
    };
  }, []);

  // Main animation loop for smooth eye tracking and parallax lerping
  useEffect(() => {
    const maxRadius = 7.5; // Max pupil travel distance within socket (px)
    const lerpFactor = 0.12; // Easing speed

    const animate = () => {
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

      // Calculate target pupil offsets
      const calcPupilOffset = (center) => {
        if (isScanning) {
          // When scanning / button hovered, gently focus forward-downward
          return { x: 0, y: 3.5 };
        }

        const dx = mouseRef.current.x - center.x;
        const dy = mouseRef.current.y - center.y;
        const dist = Math.hypot(dx, dy);

        if (dist < 1) return { x: 0, y: 0 };

        const angle = Math.atan2(dy, dx);
        // Distance scaling with smooth saturation
        const intensity = Math.min(1, dist / 400);
        const radius = intensity * maxRadius;

        return {
          x: Math.cos(angle) * radius,
          y: Math.sin(angle) * radius,
        };
      };

      const targetLeft = calcPupilOffset(leftCenter);
      const targetRight = calcPupilOffset(rightCenter);

      // Smooth interpolation (lerp)
      currentLeftPos.current.x += (targetLeft.x - currentLeftPos.current.x) * lerpFactor;
      currentLeftPos.current.y += (targetLeft.y - currentLeftPos.current.y) * lerpFactor;

      currentRightPos.current.x += (targetRight.x - currentRightPos.current.x) * lerpFactor;
      currentRightPos.current.y += (targetRight.y - currentRightPos.current.y) * lerpFactor;

      currentTilt.current.x += (targetTilt.current.x - currentTilt.current.x) * 0.08;
      currentTilt.current.y += (targetTilt.current.y - currentTilt.current.y) * 0.08;

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
        transform: `perspective(900px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
      }}
      aria-hidden="true"
    >
      {/* Ambient Diagnostic Radiance Aura */}
      <div className="hero-lung-radiance" />

      {/* Main Medical-Tech SVG Canvas */}
      <svg
        className="hero-lung-svg"
        viewBox="0 0 520 440"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          {/* Radiographic Lung Cavity Gradient */}
          <linearGradient id="lungCavityGradLeft" x1="160" y1="60" x2="60" y2="380" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#122530" stopOpacity="0.92" />
            <stop offset="45%" stopColor="#0B1B24" stopOpacity="0.85" />
            <stop offset="85%" stopColor="#08141C" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#050C12" stopOpacity="0.98" />
          </linearGradient>

          <linearGradient id="lungCavityGradRight" x1="360" y1="60" x2="460" y2="380" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#122530" stopOpacity="0.92" />
            <stop offset="45%" stopColor="#0B1B24" stopOpacity="0.85" />
            <stop offset="85%" stopColor="#08141C" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#050C12" stopOpacity="0.98" />
          </linearGradient>

          {/* Radiographic Edge Contour Gradient */}
          <linearGradient id="lungEdgeGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#2DD4BF" stopOpacity="0.6" />
            <stop offset="35%" stopColor="#14B8A6" stopOpacity="0.35" />
            <stop offset="70%" stopColor="#0D9488" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#042F2E" stopOpacity="0.4" />
          </linearGradient>

          {/* Grad-CAM Internal Heatmap Glow - Left Lobe */}
          <radialGradient id="camGlowLeft" cx="45%" cy="58%" r="42%">
            <stop offset="0%" stopColor="#14B8A6" stopOpacity="0.38" />
            <stop offset="55%" stopColor="#0D9488" stopOpacity="0.16" />
            <stop offset="100%" stopColor="#0D9488" stopOpacity="0" />
          </radialGradient>

          {/* Grad-CAM Internal Heatmap Glow - Right Lobe (Cardiac & Basilar Focus) */}
          <radialGradient id="camGlowRight" cx="55%" cy="62%" r="45%">
            <stop offset="0%" stopColor="#2DD4BF" stopOpacity="0.35" />
            <stop offset="50%" stopColor="#0D9488" stopOpacity="0.14" />
            <stop offset="85%" stopColor="#F59E0B" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#0D9488" stopOpacity="0" />
          </radialGradient>

          {/* Eye Diagnostic Lens Rim */}
          <linearGradient id="eyeRimGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2DD4BF" stopOpacity="0.75" />
            <stop offset="100%" stopColor="#0F766E" stopOpacity="0.3" />
          </linearGradient>

          {/* Sclera Internal Depth */}
          <radialGradient id="scleraGrad" cx="50%" cy="45%" r="55%">
            <stop offset="0%" stopColor="#102A36" />
            <stop offset="80%" stopColor="#08151D" />
            <stop offset="100%" stopColor="#040B0F" />
          </radialGradient>

          {/* Iris Glow Gradient */}
          <radialGradient id="irisGrad" cx="40%" cy="40%" r="60%">
            <stop offset="0%" stopColor="#5EEAD4" />
            <stop offset="50%" stopColor="#14B8A6" />
            <stop offset="90%" stopColor="#0F766E" />
            <stop offset="100%" stopColor="#042F2E" />
          </radialGradient>

          {/* Glow Filters */}
          <filter id="radiographicBloom" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter id="softVascularGlow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* ------------------------------------------------------------ */}
        {/* TRACHEA & PRIMARY BRONCHIAL HILUM (Central Medical Backbone) */}
        {/* ------------------------------------------------------------ */}
        <g className="lung-trachea-group" opacity="0.75">
          {/* Trachea Cylinder Rings */}
          <path
            d="M 248 18 L 272 18 L 270 78 L 250 78 Z"
            fill="url(#lungCavityGradLeft)"
            stroke="url(#lungEdgeGrad)"
            strokeWidth="1.6"
          />
          <line x1="249" y1="32" x2="271" y2="32" stroke="rgba(45, 212, 191, 0.3)" strokeWidth="1.2" />
          <line x1="249" y1="46" x2="271" y2="46" stroke="rgba(45, 212, 191, 0.3)" strokeWidth="1.2" />
          <line x1="249" y1="60" x2="271" y2="60" stroke="rgba(45, 212, 191, 0.3)" strokeWidth="1.2" />
          <line x1="250" y1="74" x2="270" y2="74" stroke="rgba(45, 212, 191, 0.3)" strokeWidth="1.2" />

          {/* Carina Bifurcation */}
          <path
            d="M 250 78 C 242 98 215 118 185 136 M 270 78 C 278 98 305 118 335 136"
            stroke="url(#lungEdgeGrad)"
            strokeWidth="2"
            strokeLinecap="round"
            fill="none"
          />
        </g>

        {/* ------------------------------------------------------------ */}
        {/* LIVING LUNG PAIR (Breathing Organic Expansion Group)         */}
        {/* ------------------------------------------------------------ */}
        <g className="hero-lung-pair-group">
          {/* ======================================================== */}
          {/* RIGHT LOBE (Viewer's Left Lung)                          */}
          {/* ======================================================== */}
          <g className="lung-lobe-left">
            {/* Base Anatomical Parenchyma Surface */}
            <path
              className="lung-parenchyma-path"
              d="M 224 96 
                 C 204 62 168 54 136 68
                 C 96 86 64 138 52 208
                 C 40 278 44 332 72 368
                 C 98 402 152 396 182 376
                 C 204 362 216 332 222 284
                 C 228 236 228 152 224 96 Z"
              fill="url(#lungCavityGradLeft)"
              stroke="url(#lungEdgeGrad)"
              strokeWidth="2.2"
              strokeLinejoin="round"
            />

            {/* Internal Shifting Grad-CAM Attention Heatmap */}
            <path
              className="lung-heatmap-glow-left"
              d="M 218 108 
                 C 200 76 168 68 140 80
                 C 106 96 76 142 66 208
                 C 56 270 58 322 82 356
                 C 104 386 150 380 176 364
                 C 196 352 208 324 214 280
                 C 220 236 220 160 218 108 Z"
              fill="url(#camGlowLeft)"
            />

            {/* Vascular / Bronchial Tree Fine Branches */}
            <g className="lung-vascular-branches" opacity="0.65" filter="url(#softVascularGlow)">
              <path
                d="M 195 130 
                   C 170 148 140 178 120 220
                   M 140 178 C 115 190 92 226 84 270
                   M 125 210 C 108 245 102 295 106 335
                   M 155 195 C 158 238 152 285 148 340
                   M 150 255 C 168 285 174 320 176 355
                   M 170 148 C 152 120 128 105 110 102
                   M 142 124 C 132 108 122 96 112 90"
                stroke="rgba(45, 212, 191, 0.45)"
                strokeWidth="1.4"
                strokeLinecap="round"
                fill="none"
              />
            </g>

            {/* Fissure Line (Right Lung Anatomical Lobes Separator) */}
            <path
              d="M 72 230 C 115 222 170 210 218 226"
              stroke="rgba(45, 212, 191, 0.22)"
              strokeWidth="1.2"
              strokeDasharray="3 3"
              fill="none"
            />
          </g>

          {/* ======================================================== */}
          {/* LEFT LOBE (Viewer's Right Lung — with Cardiac Notch)    */}
          {/* ======================================================== */}
          <g className="lung-lobe-right">
            {/* Base Anatomical Parenchyma Surface with Medial Cardiac Notch */}
            <path
              className="lung-parenchyma-path"
              d="M 296 96
                 C 316 62 352 54 384 68
                 C 424 86 456 138 468 208
                 C 480 278 476 332 448 368
                 C 422 402 368 396 338 376
                 C 308 356 292 316 292 268
                 C 292 220 302 180 300 148
                 C 298 124 296 108 296 96 Z"
              fill="url(#lungCavityGradRight)"
              stroke="url(#lungEdgeGrad)"
              strokeWidth="2.2"
              strokeLinejoin="round"
            />

            {/* Internal Shifting Grad-CAM Attention Heatmap */}
            <path
              className="lung-heatmap-glow-right"
              d="M 302 108
                 C 320 76 352 68 380 80
                 C 414 96 444 142 454 208
                 C 464 270 462 322 438 356
                 C 416 386 370 380 344 364
                 C 318 348 304 312 304 268
                 C 304 224 312 184 310 152
                 C 308 132 304 116 302 108 Z"
              fill="url(#camGlowRight)"
            />

            {/* Vascular / Bronchial Tree Fine Branches */}
            <g className="lung-vascular-branches" opacity="0.65" filter="url(#softVascularGlow)">
              <path
                d="M 325 130 
                   C 350 148 380 178 400 220
                   M 380 178 C 405 190 428 226 436 270
                   M 395 210 C 412 245 418 295 414 335
                   M 365 195 C 362 238 368 285 372 340
                   M 370 255 C 352 285 346 320 344 355
                   M 350 148 C 368 120 392 105 410 102
                   M 378 124 C 388 108 398 96 408 90"
                stroke="rgba(45, 212, 191, 0.45)"
                strokeWidth="1.4"
                strokeLinecap="round"
                fill="none"
              />
            </g>

            {/* Oblique Fissure (Left Lung Anatomical Separator) */}
            <path
              d="M 448 225 C 405 238 350 258 304 286"
              stroke="rgba(45, 212, 191, 0.22)"
              strokeWidth="1.2"
              strokeDasharray="3 3"
              fill="none"
            />
          </g>

          {/* ======================================================== */}
          {/* SOPHISTICATED MEDICAL-TECH PERSONIFIED EYES               */}
          {/* ======================================================== */}

          {/* --- LEFT EYE (Positioned on viewer's left lung) --- */}
          <g
            ref={leftEyeRef}
            className={`hero-eye-group left-eye ${isBlinking ? "eye-blinking" : ""}`}
            transform="translate(142, 185)"
          >
            {/* Outer Diagnostic Glow Rim */}
            <circle cx="0" cy="0" r="19" fill="#051016" stroke="url(#eyeRimGrad)" strokeWidth="1.8" filter="url(#radiographicBloom)" />
            {/* Sclera Chamber */}
            <circle cx="0" cy="0" r="17.5" fill="url(#scleraGrad)" />
            {/* Sclera Reticle Arc Marks */}
            <circle cx="0" cy="0" r="15" stroke="rgba(45, 212, 191, 0.18)" strokeWidth="0.8" strokeDasharray="4 3" fill="none" />

            {/* Trackable Iris + Pupil Unit */}
            <g transform={`translate(${leftPupilPos.x}, ${leftPupilPos.y})`}>
              {/* Iris Body */}
              <circle cx="0" cy="0" r="10.5" fill="url(#irisGrad)" />
              {/* Iris Micro-Ring */}
              <circle cx="0" cy="0" r="9.2" stroke="rgba(94, 234, 212, 0.5)" strokeWidth="0.8" fill="none" />
              {/* Deep Pupil Core */}
              <circle cx="0" cy="0" r="5.6" fill="#04090D" />
              {/* Sharp Corneal Reflection Catchlight */}
              <circle cx="-3" cy="-3.2" r="2.2" fill="#FFFFFF" opacity="0.95" />
              <circle cx="2" cy="2.2" r="1" fill="#FFFFFF" opacity="0.6" />
            </g>

            {/* Eyelid Shutter for Natural Organic Blinking */}
            <path
              className="eye-shutter-top"
              d="M -19 0 C -19 -14 19 -14 19 0 C 19 -1 19 -1 -19 -1 Z"
              fill="#061219"
            />
            <path
              className="eye-shutter-bottom"
              d="M -19 0 C -19 14 19 14 19 0 C 19 1 19 1 -19 1 Z"
              fill="#061219"
            />
          </g>

          {/* --- RIGHT EYE (Positioned on viewer's right lung) --- */}
          <g
            ref={rightEyeRef}
            className={`hero-eye-group right-eye ${isBlinking ? "eye-blinking" : ""}`}
            transform="translate(378, 185)"
          >
            {/* Outer Diagnostic Glow Rim */}
            <circle cx="0" cy="0" r="19" fill="#051016" stroke="url(#eyeRimGrad)" strokeWidth="1.8" filter="url(#radiographicBloom)" />
            {/* Sclera Chamber */}
            <circle cx="0" cy="0" r="17.5" fill="url(#scleraGrad)" />
            {/* Sclera Reticle Arc Marks */}
            <circle cx="0" cy="0" r="15" stroke="rgba(45, 212, 191, 0.18)" strokeWidth="0.8" strokeDasharray="4 3" fill="none" />

            {/* Trackable Iris + Pupil Unit */}
            <g transform={`translate(${rightPupilPos.x}, ${rightPupilPos.y})`}>
              {/* Iris Body */}
              <circle cx="0" cy="0" r="10.5" fill="url(#irisGrad)" />
              {/* Iris Micro-Ring */}
              <circle cx="0" cy="0" r="9.2" stroke="rgba(94, 234, 212, 0.5)" strokeWidth="0.8" fill="none" />
              {/* Deep Pupil Core */}
              <circle cx="0" cy="0" r="5.6" fill="#04090D" />
              {/* Sharp Corneal Reflection Catchlight */}
              <circle cx="-3" cy="-3.2" r="2.2" fill="#FFFFFF" opacity="0.95" />
              <circle cx="2" cy="2.2" r="1" fill="#FFFFFF" opacity="0.6" />
            </g>

            {/* Eyelid Shutter for Natural Organic Blinking */}
            <path
              className="eye-shutter-top"
              d="M -19 0 C -19 -14 19 -14 19 0 C 19 -1 19 -1 -19 -1 Z"
              fill="#061219"
            />
            <path
              className="eye-shutter-bottom"
              d="M -19 0 C -19 14 19 14 19 0 C 19 1 19 1 -19 1 Z"
              fill="#061219"
            />
          </g>
        </g>
      </svg>
    </div>
  );
}
