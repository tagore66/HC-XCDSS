import React from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Eye,
  Info,
} from "lucide-react";
import { CLINICAL_FINDING_DEFINITIONS } from "./PatientExplanations";

/**
 * Format decimal probability value to a 3-decimal string representation (e.g. 0.805).
 */
function formatScore(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return Number(value).toFixed(3);
}

/**
 * FindingsGrid component.
 * 
 * Implements the requested patient-journey structure:
 * - Flagged findings with: What it means, Where the AI focused, Why the highlighted area matters.
 * - What was not flagged section.
 */
export default function FindingsGrid({ findings, view, selectedFinding, onSelectFinding }) {
  const findingEntries = Object.entries(findings || {});

  if (findingEntries.length === 0) {
    return null;
  }

  const detectedEntries = findingEntries.filter(([_, data]) => data.detected);
  const notDetectedEntries = findingEntries.filter(([_, data]) => !data.detected);

  return (
    <div className="findings-hierarchy-panel">
      {/* Panel Header */}
      <div className="findings-panel-header">
        <div>
          <div className="eyebrow" style={{ color: "var(--accent-primary)" }}>
            WHAT DID THE AI FIND?
          </div>
          <h3 className="findings-panel-title">
            {detectedEntries.length > 0
              ? `${detectedEntries.length} finding${detectedEntries.length > 1 ? "s" : ""} need attention`
              : "No findings flagged for attention"}
          </h3>
        </div>
        <span className="findings-view-badge">{view} Projection</span>
      </div>

      {/* SECTION A: FLAGGED FINDINGS (EACH WITH: WHAT IT MEANS, WHERE AI FOCUSED, WHY IT MATTERS) */}
      {detectedEntries.length > 0 ? (
        <div className="detected-findings-group">
          {detectedEntries.map(([finding, data]) => {
            const isSelected = selectedFinding === finding;
            const probNum = Number(data.probability) || 0;
            const threshNum = Number(data.threshold) || 0.5;
            const def = CLINICAL_FINDING_DEFINITIONS[finding];

            return (
              <div
                key={finding}
                className={`detected-finding-card ${isSelected ? "active-in-viewport" : ""}`}
                onClick={() => onSelectFinding && onSelectFinding(finding)}
              >
                {/* Card Top Title & Secondary Scores */}
                <div className="detected-card-top">
                  <div className="detected-title-wrap">
                    <div className="detected-badge-line">
                      <span className="badge-detected-amber">AI FLAGGED</span>
                    </div>
                    <h4 className="detected-finding-name">{finding}</h4>
                  </div>

                  {/* Secondary Subtle Numerical Score Block */}
                  <div className="detected-secondary-scores">
                    <div className="score-pill">
                      <span className="score-pill-label">Model output:</span>
                      <span className="score-pill-val">{formatScore(probNum)}</span>
                    </div>
                    <div className="score-pill threshold-pill">
                      <span className="score-pill-label">Operating threshold:</span>
                      <span className="score-pill-val">{formatScore(threshNum)}</span>
                    </div>
                  </div>
                </div>

                {/* THE 3 PATIENT-FIRST EXPLANATION FACETS */}
                <div className="finding-triad-block">
                  {/* 1. What it means */}
                  <div className="triad-item">
                    <span className="triad-label">What it means</span>
                    <p className="triad-text">
                      {def?.simple_explanation || "A pattern matching this condition was identified by the AI on the radiograph."}
                    </p>
                  </div>

                  {/* 2. Where the AI focused */}
                  <div className="triad-item">
                    <span className="triad-label">Where the AI focused</span>
                    <p className="triad-text">
                      This shows where the AI model focused when producing this finding. Look at the diagnostic viewport to inspect the highlighted region.
                    </p>
                  </div>

                  {/* 3. Why the highlighted area matters */}
                  <div className="triad-item">
                    <span className="triad-label">Why the highlighted area matters</span>
                    <p className="triad-text">
                      The highlighted area represents model attention. It is not a disease boundary, segmentation, or proof that disease is present.
                    </p>
                  </div>
                </div>

                {/* Focus trigger */}
                <div className="detected-card-actions">
                  <button
                    type="button"
                    className={`btn-focus-attention ${isSelected ? "btn-active-attention" : ""}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectFinding && onSelectFinding(finding);
                    }}
                  >
                    <Eye size={13} />
                    <span>{isSelected ? "Active in Visual Viewport" : "Show AI focus area in viewport →"}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="no-detected-banner">
          <CheckCircle2 size={16} color="var(--color-success)" />
          <span>No findings were flagged above operating thresholds on this projection.</span>
        </div>
      )}

      {/* SECTION B: WHAT WAS NOT FLAGGED? */}
      {notDetectedEntries.length > 0 && (
        <div className="not-detected-findings-group">
          <div className="not-detected-group-header">
            <span>WHAT WAS NOT FLAGGED? ({notDetectedEntries.length} FINDINGS)</span>
            <span className="compact-note">No prominent model signal detected</span>
          </div>

          <div className="not-detected-table">
            {notDetectedEntries.map(([finding, data]) => {
              const isSelected = selectedFinding === finding;
              const probNum = Number(data.probability) || 0;
              const threshNum = Number(data.threshold) || 0.5;

              return (
                <div
                  key={finding}
                  className={`not-detected-row ${isSelected ? "row-selected" : ""}`}
                  onClick={() => onSelectFinding && onSelectFinding(finding)}
                  title={`Click to view ${finding} model attention heatmap`}
                >
                  <div className="row-left">
                    <span className="row-finding-name">{finding}</span>
                    <span className="row-finding-sub">No prominent model signal was detected for this finding on this view.</span>
                  </div>

                  <div className="row-middle">
                    <span className="badge-not-detected">NOT FLAGGED BY THE AI</span>
                  </div>

                  <div className="row-right">
                    <div className="row-subtle-scores">
                      <span>Output: {formatScore(probNum)}</span>
                      <span className="score-sep">•</span>
                      <span>Threshold: {formatScore(threshNum)}</span>
                    </div>
                    <ChevronRight size={13} className="row-chevron" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
