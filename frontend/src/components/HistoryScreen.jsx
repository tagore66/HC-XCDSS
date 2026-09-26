import { useState } from "react";
import {
  Activity,
  Plus,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ChevronRight,
  Filter,
} from "lucide-react";

function formatDate(value) {
  if (!value) return "Unknown date";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatCaseId(id) {
  if (!id) return "—";
  const clean = String(id).replace(/^#/, "");
  return `Case #${clean.substring(0, 8).toUpperCase()}`;
}

export default function HistoryScreen({
  history = [],
  loading,
  error,
  onOpenAnalysis,
  onNewAnalysis,
}) {
  const [filter, setFilter] = useState("all"); // 'all', 'detected', 'reviewed'

  const filteredHistory = history.filter((item) => {
    if (filter === "detected") {
      return item.detected_findings && item.detected_findings.length > 0;
    }
    if (filter === "reviewed") {
      return Boolean(item.review_status);
    }
    return true;
  });

  return (
    <section className="results-screen-container">
      {/* HEADER */}
      <div className="results-top-bar">
        <div>
          <div className="eyebrow" style={{ color: "var(--accent-primary)" }}>
            <Clock size={12} />
            <span>ARCHIVAL RECORDS</span>
          </div>
          <h2>Analysis History</h2>
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "2px" }}>
            Review past chest radiograph analyses and associated professional second opinions.
          </p>
        </div>

        <div className="results-actions-group">
          <button type="button" className="btn-primary btn-sm" onClick={onNewAnalysis}>
            <Plus size={13} />
            <span>New Analysis</span>
          </button>
        </div>
      </div>

      {/* FILTER BUTTONS */}
      <div className="portal-tab-bar" style={{ marginBottom: "14px" }}>
        <button
          type="button"
          className={`portal-tab ${filter === "all" ? "active" : ""}`}
          onClick={() => setFilter("all")}
        >
          All Analyses ({history.length})
        </button>
        <button
          type="button"
          className={`portal-tab ${filter === "detected" ? "active" : ""}`}
          onClick={() => setFilter("detected")}
        >
          With Detected Findings
        </button>
        <button
          type="button"
          className={`portal-tab ${filter === "reviewed" ? "active" : ""}`}
          onClick={() => setFilter("reviewed")}
        >
          With Doctor Review
        </button>
      </div>

      {loading && (
        <div className="dashboard-stats-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="stat-card" style={{ height: "90px", opacity: 0.6 }} />
          ))}
        </div>
      )}

      {error && (
        <div className="validation-error-card">
          <div className="val-error-header">
            <AlertTriangle size={15} />
            <span>{error}</span>
          </div>
        </div>
      )}

      {!loading && !error && filteredHistory.length === 0 && (
        <div className="dashboard-empty-card">
          <div className="empty-card-icon">
            <Clock size={24} />
          </div>
          <h3>No analyses found</h3>
          <p>
            {filter === "all"
              ? "Your completed X-ray analyses will appear here."
              : "No historical analyses matched your selected filter."}
          </p>
          <button
            type="button"
            className="btn-primary"
            onClick={onNewAnalysis}
            style={{ marginTop: "8px" }}
          >
            <Plus size={14} />
            <span>Start First Analysis</span>
          </button>
        </div>
      )}

      {!loading && !error && filteredHistory.length > 0 && (
        <div className="dashboard-analyses-grid">
          {filteredHistory.map((analysis) => {
            const detectedCount = analysis.detected_findings?.length || 0;

            return (
              <div
                key={analysis.analysis_id}
                className="dashboard-analysis-card"
                onClick={() => onOpenAnalysis(analysis.analysis_id)}
              >
                <div className="analysis-card-top">
                  <span className="analysis-id-tag">{formatCaseId(analysis.analysis_id)}</span>
                  <span className="status-tag" style={{ background: "var(--surface-primary)" }}>
                    {analysis.view || "Frontal"} View
                  </span>
                </div>

                <div className="analysis-card-body">
                  <h4 style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)" }}>
                    {analysis.view || "Frontal"} Chest Radiograph
                  </h4>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                    {formatDate(analysis.created_at)}
                  </p>

                  <div className="findings-summary-box">
                    <span className="findings-count-label">
                      {detectedCount > 0
                        ? `${detectedCount} finding(s) detected`
                        : "No acute findings detected"}
                    </span>
                    {detectedCount > 0 && analysis.detected_findings && (
                      <div className="finding-chips-wrap">
                        {analysis.detected_findings.slice(0, 3).map((f) => (
                          <span key={f} className="finding-chip">{f}</span>
                        ))}
                        {analysis.detected_findings.length > 3 && (
                          <span className="finding-chip-more">
                            +{analysis.detected_findings.length - 3}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {analysis.review_status && (
                    <div style={{ marginTop: "6px" }}>
                      <span className={`status-tag status-${analysis.review_status.toLowerCase()}`}>
                        Doctor Review: {analysis.review_status}
                      </span>
                    </div>
                  )}
                </div>

                <div className="analysis-card-action">
                  <span className="btn-open-analysis">
                    View Analysis →
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
