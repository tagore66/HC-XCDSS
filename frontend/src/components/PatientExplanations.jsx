import React, { useState } from "react";
import { BookOpen, Info, CheckCircle2, AlertTriangle, ChevronRight, HelpCircle } from "lucide-react";

/**
 * Comprehensive plain-language clinical guide for all 5 evaluated thoracic findings.
 */
export const CLINICAL_FINDING_DEFINITIONS = {
  Atelectasis: {
    title: "Atelectasis (Partial Lung Deflation)",
    simple_explanation: "Part of the lung appears less expanded with air than normal on the X-ray.",
    what_it_means:
      "Atelectasis occurs when tiny air sacs (alveoli) within a lung segment become deflated or collapsed. It is an imaging appearance describing reduced air expansion.",
    possible_causes: [
      "Shallow breathing or resting in bed for extended periods",
      "Mucus temporarily obstructing a small airway branch",
      "External compression from neighboring fluid or tissue",
      "Recovery following chest or abdominal surgical procedures",
    ],
    important_note:
      "This X-ray appearance describes an area of reduced air volume. It does not determine the underlying medical cause by itself.",
  },
  Cardiomegaly: {
    title: "Cardiomegaly (Enlarged Heart Silhouette)",
    simple_explanation: "The heart appears enlarged or broader on the X-ray relative to the chest cavity.",
    what_it_means:
      "Cardiomegaly means the shadow cast by the heart on the radiograph exceeds typical proportion limits for this projection.",
    possible_causes: [
      "Long-term high blood pressure (hypertension)",
      "Heart muscle stretching or thickening (cardiomyopathy)",
      "Fluid accumulation around the heart lining (pericardial effusion)",
      "Patient rotation or shallow breath during X-ray image capture",
    ],
    important_note:
      "An enlarged cardiac outline on a radiograph is a visual pattern. A physician correlates this with blood pressure, symptoms, and targeted heart evaluations.",
  },
  Consolidation: {
    title: "Consolidation (Solid / Fluid-Filled Lung Region)",
    simple_explanation: "An area of the lung that is normally air-filled appears dense, opaque, or hazy on the radiograph.",
    what_it_means:
      "Consolidation indicates that normally airy spaces in the lung contain fluid, inflammatory material, or cellular buildup rather than air.",
    possible_causes: [
      "Pulmonary infection such as pneumonia (bacterial or viral)",
      "Localized lung tissue inflammation",
      "Aspiration of fluids into airway branches",
      "Fluid or hemorrhage within alveolar spaces",
    ],
    important_note:
      "Consolidation is an imaging description of density. Whether it represents an active infection or resolving inflammation requires clinical evaluation of your symptoms, temperature, and lab work.",
  },
  Edema: {
    title: "Edema (Fluid Accumulation in Lung Tissues)",
    simple_explanation: "The X-ray shows diffuse haziness suggesting extra fluid within the lung tissues.",
    what_it_means:
      "Pulmonary edema refers to fluid collecting in the tissues and air spaces of the lungs, causing subtle hazy markings on the radiograph.",
    possible_causes: [
      "Cardiac fluid backpressure or heart-related strain",
      "Fluid overload or kidney filtration changes",
      "Inflammatory changes affecting lung blood vessels",
      "Severe acute systemic illness",
    ],
    important_note:
      "The AI model recognizes optical density patterns associated with fluid. Evaluating actual fluid status requires a comprehensive clinical examination by a doctor.",
  },
  "Pleural Effusion": {
    title: "Pleural Effusion (Fluid Collection Around the Lung)",
    simple_explanation: "The X-ray shows signs of fluid collecting in the space between the lung and the chest wall.",
    what_it_means:
      "A pleural effusion is a collection of fluid in the pleural cavity surrounding the lung, typically causing blunting of the sharp lower lung angle.",
    possible_causes: [
      "Heart failure or systemic fluid retention",
      "Lung or pleural inflammation and infection",
      "Systemic inflammatory disorders",
      "Post-surgical fluid collection",
    ],
    important_note:
      "There are many potential medical reasons for fluid in the pleural space. An X-ray shows its presence, but clinical evaluation is required to determine the exact cause.",
  },
};

/**
 * PatientExplanations component.
 * Displays patient-first plain-language explanations for all 5 findings with active status filtering.
 */
export default function PatientExplanations({
  findings = {},
  detectedFindings = [],
  patientExplanations = [],
  selectedFinding = null,
  onSelectFinding = null,
}) {
  const [activeTab, setActiveTab] = useState("all"); // "all" | "detected" | "not_flagged"
  const [expandedFinding, setExpandedFinding] = useState(
    selectedFinding || detectedFindings[0] || "Atelectasis"
  );

  const allFindingNames = [
    "Atelectasis",
    "Cardiomegaly",
    "Consolidation",
    "Edema",
    "Pleural Effusion",
  ];

  // Merge server-supplied explanations with local clinical definitions
  const explanationMap = {};
  allFindingNames.forEach((name) => {
    const serverExp = patientExplanations.find((p) => p.finding === name);
    explanationMap[name] = {
      ...CLINICAL_FINDING_DEFINITIONS[name],
      ...(serverExp || {}),
      detected: detectedFindings.includes(name) || !!findings[name]?.detected,
    };
  });

  const notFlaggedCount = allFindingNames.filter((name) => !explanationMap[name].detected).length;

  const filteredNames = allFindingNames.filter((name) => {
    const isDetected = explanationMap[name].detected;
    if (activeTab === "detected") return isDetected;
    if (activeTab === "not_flagged") return !isDetected;
    return true;
  });

  return (
    <div className="patient-guidance-section" id="finding-explanations-section">
      <div className="section-heading" style={{ marginBottom: "14px" }}>
        <div>
          <div className="eyebrow" style={{ color: "var(--accent-primary)" }}>
            STAGE 2 • WHAT DOES THIS MEAN?
          </div>
          <h3 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-primary)", marginTop: "2px" }}>
            Understanding the Evaluated Findings
          </h3>
        </div>
      </div>

      <p
        style={{
          fontSize: "13.5px",
          color: "var(--text-secondary)",
          lineHeight: "1.6",
          marginBottom: "16px",
          maxWidth: "820px",
        }}
      >
        Below are clear, plain-language explanations for the <strong>5 conditions</strong> evaluated on your radiograph to help guide your discussion with your healthcare provider.
      </p>

      {/* Tab Filter */}
      <div className="guidance-filter-bar">
        <div className="guidance-tabs-group">
          <button
            type="button"
            className={`btn-guidance-tab ${activeTab === "all" ? "active" : ""}`}
            onClick={() => setActiveTab("all")}
          >
            <span>All 5 Evaluated Findings</span>
          </button>
          <button
            type="button"
            className={`btn-guidance-tab ${activeTab === "detected" ? "active" : ""}`}
            onClick={() => setActiveTab("detected")}
          >
            <span>AI Flagged ({detectedFindings.length})</span>
          </button>
          <button
            type="button"
            className={`btn-guidance-tab ${activeTab === "not_flagged" ? "active" : ""}`}
            onClick={() => setActiveTab("not_flagged")}
          >
            <span>Not Flagged by the AI ({notFlaggedCount})</span>
          </button>
        </div>
      </div>

      {/* Findings Accordion / Card List */}
      <div className="guidance-cards-list">
        {filteredNames.map((findingName) => {
          const exp = explanationMap[findingName];
          const isDetected = exp.detected;
          const isExpanded = expandedFinding === findingName;

          return (
            <div
              key={findingName}
              className={`guidance-explanation-item ${isDetected ? "item-detected-highlight" : ""} ${
                isExpanded ? "item-expanded" : ""
              }`}
            >
              {/* Header Bar */}
              <div
                className="guidance-item-header"
                onClick={() => {
                  setExpandedFinding(isExpanded ? null : findingName);
                  if (onSelectFinding) onSelectFinding(findingName);
                }}
                style={{ cursor: "pointer" }}
              >
                <div className="guidance-header-left">
                  <div className={`guidance-icon-circle ${isDetected ? "icon-amber" : "icon-slate"}`}>
                    <BookOpen size={14} />
                  </div>
                  <div>
                    <h4 className="guidance-item-title">{exp.title}</h4>
                    <span className="guidance-item-sub">
                      {isDetected
                        ? "AI flagged this finding for clinical attention on this view"
                        : "No prominent model signal was detected for this finding on this view."}
                    </span>
                  </div>
                </div>

                <div className="guidance-header-right">
                  <span className={isDetected ? "badge-detected-amber" : "badge-not-detected"}>
                    {isDetected ? "AI FLAGGED" : "NOT FLAGGED BY THE AI"}
                  </span>
                  <ChevronRight
                    size={16}
                    className={`guidance-chevron ${isExpanded ? "chevron-open" : ""}`}
                  />
                </div>
              </div>

              {/* Collapsible Content */}
              {isExpanded && (
                <div className="guidance-expanded-body">
                  <div className="guidance-grid-details">
                    <div className="guidance-detail-col">
                      <span className="guidance-col-label">In Plain Language</span>
                      <p className="guidance-col-text">{exp.simple_explanation}</p>
                    </div>

                    <div className="guidance-detail-col">
                      <span className="guidance-col-label">Radiological Meaning</span>
                      <p className="guidance-col-text">{exp.what_it_means}</p>
                    </div>
                  </div>

                  {exp.possible_causes && exp.possible_causes.length > 0 && (
                    <div className="guidance-causes-wrap">
                      <span className="guidance-col-label">Possible reasons this finding can occur</span>
                      <p className="guidance-col-subnote">
                        This finding can occur for several reasons. The AI cannot determine the specific cause from this X-ray alone.
                      </p>
                      <ul className="guidance-causes-list">
                        {exp.possible_causes.map((cause) => (
                          <li key={cause}>{cause}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {exp.important_note && (
                    <div className="guidance-note-callout">
                      <Info size={14} style={{ flexShrink: 0, marginTop: "2px" }} />
                      <span>{exp.important_note}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
