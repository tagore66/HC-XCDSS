import React, { useEffect, useRef, useState, useCallback } from "react";
import "./HeroLungVisual.css";

/**
 * HC-XCDSS Interactive Living Lung Visualization
 *
 * Preserves the exact user-specified artwork (hero_lungs_artwork.png)
 * and enhances it with:
 * - Smooth cursor-following eyes with independent tracking & micro-saccades
 * - Occasional subtle organic blinking
 * - Very slow diaphragmatic breathing motion
 * - Subtle cursor-based 3D parallax depth
 * - Restrained internal teal/amber AI-attention glow movement
 * - Subtle hover reaction when Start Patient Analysis is hovered
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
  const mouseRef = useRef({
    x: typeof window !== "undefined" ? window.innerWidth * 0.7 : 800,
    y: typeof window !== "undefined" ? window.innerHeight * 0.4 : 350,
  });
  const currentLeftPos = useRef({ x: 0, y: 0 });
  const currentRightPos = useRef({ x: 0, y: 0 });
  const currentTilt = useRef({ x: 0, y: 0 });
  const targetTilt = useRef({ x: 0, y: 0 });
  const animFrameRef = useRef(null);
  const blinkTimerRef = useRef(null);
  const timeRef = useRef(0);

  // Autonomous natural organic blinking (randomized 3.4s – 6.8s)
  const triggerBlink = useCallback(() => {
    setIsBlinking(true);
    setTimeout(() => {
      setIsBlinking(false);
      const nextDelay = 3200 + Math.random() * 3600;
      blinkTimerRef.current = setTimeout(triggerBlink, nextDelay);
    }, 160);
  }, []);

  useEffect(() => {
    blinkTimerRef.current = setTimeout(triggerBlink, 3400);
    return () => {
      if (blinkTimerRef.current) clearTimeout(blinkTimerRef.current);
    };
  }, [triggerBlink]);

  // Pointer movement tracking for 3D parallax
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
        x: Math.max(-4.5, Math.min(4.5, -dy * 3.8)),
        y: Math.max(-6.0, Math.min(6.0, dx * 5.0)),
      };
    };

    window.addEventListener("pointermove", handlePointerMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
    };
  }, []);

  // Main 60fps animation loop with micro-saccades and smooth interpolation
  useEffect(() => {
    const maxRadius = 6.2; // Maximum pupil travel radius within eye socket
    const lerpFactor = 0.09; // Fluid natural gaze easing

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
          // When scanning or CTA button hovered: focused downward-leftward gaze towards CTA
          return { x: isLeft ? -2.8 : -3.4, y: 3.2 };
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

      {/* Main Living Lung Container */}
      <div className="hero-lung-body-wrap">
        {/* Exact Original Cinematic Artwork */}
        <img
          src="/hero_lungs_artwork.png"
          alt="HC-XCDSS Medical Imaging Artwork"
          className="hero-lung-artwork-img"
          draggable={false}
        />

        {/* Dynamic Internal AI-Attention & Grad-CAM Glow Layer */}
        <div className="hero-lung-attention-layer">
          <div className="attention-glow attention-glow-right" />
          <div className="attention-glow attention-glow-left" />
          <div className="attention-glow attention-glow-core" />
        </div>

        {/* High-Precision Interactive SVG Eye Overlay */}
        <svg
          className="hero-lung-eye-overlay"
          viewBox="0 0 567 559"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            {/* Left Eye Aperture Clip */}
            <clipPath id="leftEyeApertureClip">
              <ellipse cx="189" cy="277" rx="17.5" ry="14" />
            </clipPath>

            {/* Right Eye Aperture Clip */}
            <clipPath id="rightEyeApertureClip">
              <ellipse cx="383" cy="276" rx="17.5" ry="14" />
            </clipPath>

            {/* Iris Radial Gradient (Teal / Medical Cyan to Deep Slate) */}
            <radialGradient id="artIrisGrad" cx="38%" cy="38%" r="62%">
              <stop offset="0%" stopColor="#5EEAD4" />
              <stop offset="42%" stopColor="#14B8A6" />
              <stop offset="82%" stopColor="#0D9488" />
              <stop offset="100%" stopColor="#042F2E" />
            </radialGradient>

            {/* Deep Socket Gradient */}
            <radialGradient id="artSocketGrad" cx="50%" cy="45%" r="55%">
              <stop offset="0%" stopColor="#0A1E29" />
              <stop offset="65%" stopColor="#061219" />
              <stop offset="100%" stopColor="#02080D" />
            </radialGradient>

            {/* Soft Eye Glow */}
            <filter id="eyeSoftGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="2.5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* ================================================================ */}
          {/* LEFT EYE (Viewer's Left, Anatomical Right) — Center: (189, 277)   */}
          {/* ================================================================ */}
          <g
            ref={leftEyeRef}
            className={`artwork-eye-group left-eye-group ${isBlinking ? "eye-blinking" : ""}`}
          >
            {/* Eye Socket Outer Glow / Subtle Rim */}
            <ellipse
              cx="189"
              cy="277"
              rx="18.5"
              ry="15"
              fill="#061219"
              stroke="rgba(45, 212, 191, 0.45)"
              strokeWidth="1.2"
              filter="url(#eyeSoftGlow)"
            />

            {/* Clipped Eye Chamber */}
            <g clipPath="url(#leftEyeApertureClip)">
              {/* Vitreous Chamber Background */}
              <rect x="165" y="255" width="48" height="44" fill="url(#artSocketGrad)" />

              {/* Inner Optical Reticle Detail */}
              <ellipse
                cx="189"
                cy="277"
                rx="14"
                ry="11"
                stroke="rgba(94, 234, 212, 0.18)"
                strokeWidth="0.8"
                strokeDasharray="2 3"
                fill="none"
              />

              {/* Smooth Trackable Pupil & Iris Group */}
              <g transform={`translate(${189 + leftPupilPos.x}, ${277 + leftPupilPos.y})`}>
                {/* Iris */}
                <circle cx="0" cy="0" r="8.8" fill="url(#artIrisGrad)" />
                <circle cx="0" cy="0" r="7.6" stroke="rgba(94, 234, 212, 0.65)" strokeWidth="0.7" fill="none" />
                {/* Deep Pupil */}
                <circle cx="0" cy="0" r="4.8" fill="#010406" />

                {/* Primary Crisp Corneal Specular Catchlight */}
                <circle cx="-2.4" cy="-2.6" r="1.8" fill="#FFFFFF" opacity="0.95" />
                {/* Secondary Micro-Reflection */}
                <circle cx="2.0" cy="1.8" r="0.9" fill="#FFFFFF" opacity="0.65" />
              </g>

              {/* Precision Shutter Eyelids for Natural Blinking */}
              <path
                className="art-eyelid eyelid-top"
                d="M 168 277 C 168 260 210 260 210 277 C 210 277 168 277 168 277 Z"
                fill="#051017"
              />
              <path
                className="art-eyelid eyelid-bottom"
                d="M 168 277 C 168 294 210 294 210 277 C 210 277 168 277 168 277 Z"
                fill="#051017"
              />
            </g>
          </g>

          {/* ================================================================ */}
          {/* RIGHT EYE (Viewer's Right, Anatomical Left) — Center: (383, 276) */}
          {/* ================================================================ */}
          <g
            ref={rightEyeRef}
            className={`artwork-eye-group right-eye-group ${isBlinking ? "eye-blinking" : ""}`}
          >
            {/* Eye Socket Outer Glow / Subtle Rim */}
            <ellipse
              cx="383"
              cy="276"
              rx="18.5"
              ry="15"
              fill="#061219"
              stroke="rgba(45, 212, 191, 0.45)"
              strokeWidth="1.2"
              filter="url(#eyeSoftGlow)"
            />

            {/* Clipped Eye Chamber */}
            <g clipPath="url(#rightEyeApertureClip)">
              {/* Vitreous Chamber Background */}
              <rect x="359" y="254" width="48" height="44" fill="url(#artSocketGrad)" />

              {/* Inner Optical Reticle Detail */}
              <ellipse
                cx="383"
                cy="276"
                rx="14"
                ry="11"
                stroke="rgba(94, 234, 212, 0.18)"
                strokeWidth="0.8"
                strokeDasharray="2 3"
                fill="none"
              />

              {/* Smooth Trackable Pupil & Iris Group */}
              <g transform={`translate(${383 + rightPupilPos.x}, ${276 + rightPupilPos.y})`}>
                {/* Iris */}
                <circle cx="0" cy="0" r="8.8" fill="url(#artIrisGrad)" />
                <circle cx="0" cy="0" r="7.6" stroke="rgba(94, 234, 212, 0.65)" strokeWidth="0.7" fill="none" />
                {/* Deep Pupil */}
                <circle cx="0" cy="0" r="4.8" fill="#010406" />

                {/* Primary Crisp Corneal Specular Catchlight */}
                <circle cx="-2.4" cy="-2.6" r="1.8" fill="#FFFFFF" opacity="0.95" />
                {/* Secondary Micro-Reflection */}
                <circle cx="2.0" cy="1.8" r="0.9" fill="#FFFFFF" opacity="0.65" />
              </g>

              {/* Precision Shutter Eyelids for Natural Blinking */}
              <path
                className="art-eyelid eyelid-top"
                d="M 362 276 C 362 259 404 259 404 276 C 404 276 362 276 362 276 Z"
                fill="#051017"
              />
              <path
                className="art-eyelid eyelid-bottom"
                d="M 362 276 C 362 293 404 293 404 276 C 404 276 362 276 362 276 Z"
                fill="#051017"
              />
            </g>
          </g>
        </svg>
      </div>
    </div>
  );
}
