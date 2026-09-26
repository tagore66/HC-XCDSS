import { getHeatmapUrl } from "../services/api";
import { Eye, Info, Sparkles } from "lucide-react";

/**
 * Format decimal value to percentage string.
 */
function percentage(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return `${(Number(value) * 100).toFixed(1)}%`;
}

/**
 * HeatmapSection component.
 * Displays Grad-CAM visual explanations alongside original X-ray images for detected findings.
 */
export default function HeatmapSection({ heatmaps, findings, originalImage }) {
  const heatmapEntries = Object.entries(heatmaps || {});

  if (heatmapEntries.length === 0) {
    return null;
  }

  return (
    <div className="pro-card" style={{ padding: "22px" }}>
      <div className="section-heading" style={{ marginBottom: "8px" }}>
        <div>
          <div className="eyebrow">EXPLAINABLE AI</div>
          <h3>Model Attention Visualizations (Grad-CAM)</h3>
        </div>
        <span className="badge-recommended">
          Visual Evidence
        </span>
      </div>

      <div style={{
        padding: "10px 14px",
        background: "var(--surface-secondary)",
        border: "1px solid var(--border-main)",
        borderRadius: "var(--radius-md)",
        fontSize: "12px",
        color: "var(--text-secondary)",
        lineHeight: "1.5",
        marginBottom: "18px",
        display: "flex",
        alignItems: "flex-start",
        gap: "10px",
      }}>
        <Info size={16} color="var(--accent-primary)" style={{ flexShrink: 0, marginTop: "2px" }} />
        <span>
          <strong>Model attention visualization:</strong> Highlights indicate anatomical regions that influenced the model's prediction for each finding.
          <em> This visualization explains model attention and is not diagnostic proof of disease.</em>
        </span>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
        gap: "16px",
      }}>
        {heatmapEntries.map(([finding, path]) => {
          const findingData = findings?.[finding];

          return (
            <div
              key={finding}
              style={{
                background: "var(--surface-secondary)",
                border: "1px solid var(--border-main)",
                borderRadius: "var(--radius-lg)",
                overflow: "hidden",
              }}
            >
              <div style={{
                padding: "10px 14px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                background: "var(--surface-primary)",
                borderBottom: "1px solid var(--border-subtle)",
              }}>
                <div>
                  <h4 style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-primary)" }}>{finding}</h4>
                  {findingData && (
                    <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                      Confidence: {percentage(findingData.probability)}
                    </span>
                  )}
                </div>

                <span className="finding-badge-detected">DETECTED</span>
              </div>

              <div style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "8px",
                padding: "10px",
                background: "var(--cinema-bg)",
              }}>
                <div>
                  <span style={{ display: "block", fontSize: "10px", color: "var(--cinema-text-muted)", marginBottom: "4px", textAlign: "center" }}>
                    Original
                  </span>
                  <img
                    src={originalImage}
                    alt={`${finding} original X-ray`}
                    style={{ maxHeight: "150px", margin: "0 auto", borderRadius: "var(--radius-xs)" }}
                  />
                </div>

                <div>
                  <span style={{ display: "block", fontSize: "10px", color: "var(--cinema-teal)", marginBottom: "4px", textAlign: "center" }}>
                    Grad-CAM
                  </span>
                  <img
                    src={getHeatmapUrl(path)}
                    alt={`${finding} Grad-CAM heatmap`}
                    style={{ maxHeight: "150px", margin: "0 auto", borderRadius: "var(--radius-xs)" }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
