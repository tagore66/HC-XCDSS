import React from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Eye,
  Sliders,
  Sparkles,
} from "lucide-react";

/**
 * Format decimal probability value to percentage string.
 */
function percentage(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return `${(Number(value) * 100).toFixed(1)}%`;
}

/**
 * FindingsGrid component.
 * 
 * Strict Visual Hierarchy:
 * 1. Detected Findings: High-contrast amber attention card with prominent confidence and direct viewport trigger.
 * 2. Not Detected Findings: Compact neutral slate rows for rapid clinical scanning.
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
            DENSENET121 INFERENCE
          </div>
          <h3 className="findings-panel-title">Radiographic Findings</h3>
        </div>
        <span className="findings-view-badge">{view} View Thresholds</span>
      </div>

      {/* SECTION A: DETECTED FINDINGS (PROMINENT AMBER ATTENTION CARDS) */}
      {detectedEntries.length > 0 ? (
        <div className="detected-findings-group">
          <div className="detected-group-label">
            <span className="amber-dot" />
            <span>ACUTE FINDINGS DETECTED ({detectedEntries.length})</span>
          </div>

          {detectedEntries.map(([finding, data]) => {
            const isSelected = selectedFinding === finding;
            const probNum = Number(data.probability) || 0;
            const threshNum = Number(data.threshold) || 0.5;

            return (
              <div
                key={finding}
                className={`detected-finding-card ${isSelected ? "active-in-viewport" : ""}`}
                onClick={() => onSelectFinding && onSelectFinding(finding)}
              >
                <div className="detected-card-top">
                  <div className="detected-title-wrap">
                    <h4 className="detected-finding-name">{finding}</h4>
                    <span className="badge-detected-amber">DETECTED</span>
                  </div>

                  <div className="detected-confidence-display">
                    <span className="detected-prob-val">{percentage(probNum)}</span>
                    <span className="detected-prob-label">confidence</span>
                  </div>
                </div>

                {/* Progress bar with calibrated threshold tick */}
                <div className="detected-progress-container">
                  <div className="detected-progress-bar">
                    <div
                      className="detected-progress-fill"
                      style={{ width: `${Math.min(probNum * 100, 100)}%` }}
                    />
                    <div
                      className="detected-threshold-line"
                      style={{ left: `${Math.min(threshNum * 100, 100)}%` }}
                      title={`Detection operating threshold: ${percentage(threshNum)}`}
                    />
                  </div>
                  <div className="detected-progress-labels">
                    <span>Baseline 0%</span>
                    <span>Threshold: <strong>{percentage(threshNum)}</strong></span>
                    <span>100%</span>
                  </div>
                </div>

                {/* Action trigger to focus viewport */}
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
                    <span>{isSelected ? "Active in Diagnostic Viewport" : "View model attention →"}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="no-detected-banner">
          <CheckCircle2 size={16} color="var(--color-success)" />
          <span>No acute radiographic abnormalities detected above operating thresholds.</span>
        </div>
      )}

      {/* SECTION B: NOT DETECTED FINDINGS (COMPACT NEUTRAL SCAN ROWS) */}
      {notDetectedEntries.length > 0 && (
        <div className="not-detected-findings-group">
          <div className="not-detected-group-header">
            <span>UNREMARKABLE / NOT DETECTED ({notDetectedEntries.length})</span>
            <span className="compact-note">Click row to inspect</span>
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
                  </div>

                  <div className="row-middle">
                    <span className="badge-not-detected">NOT DETECTED</span>
                  </div>

                  <div className="row-right">
                    <span className="row-prob-text">{percentage(probNum)}</span>
                    <span className="row-thresh-text">(Thresh {percentage(threshNum)})</span>
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
