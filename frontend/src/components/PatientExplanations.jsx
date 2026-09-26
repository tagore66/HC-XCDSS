import React from "react";
import { BookOpen, Info } from "lucide-react";

/**
 * PatientExplanations component.
 * Displays accessible lay explanations for detected findings in a calm, readable format.
 */
export default function PatientExplanations({ patientExplanations }) {
  if (!patientExplanations || patientExplanations.length === 0) {
    return null;
  }

  return (
    <div className="patient-guidance-section">
      <div className="section-heading" style={{ marginBottom: "12px" }}>
        <div>
          <div className="eyebrow" style={{ color: "var(--accent-primary)" }}>
            CLINICAL REPORT GUIDANCE
          </div>
          <h3 style={{ fontSize: "17px", fontWeight: "700", color: "var(--text-primary)" }}>
            Understanding Detected Radiographic Findings
          </h3>
        </div>
      </div>

      <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.6", marginBottom: "16px", maxWidth: "780px" }}>
        The explanations below describe common clinical characteristics of observations noted in this radiograph to assist your consultation with a physician.
      </p>

      <div className="guidance-cards-list">
        {patientExplanations.map((explanation) => (
          <div key={explanation.finding} className="guidance-explanation-item">
            <div className="guidance-item-header">
              <div className="guidance-icon-circle">
                <BookOpen size={14} />
              </div>
              <h4 className="guidance-item-title">{explanation.title}</h4>
            </div>

            <div className="guidance-grid-details">
              <div className="guidance-detail-col">
                <span className="guidance-col-label">In Simple Terms</span>
                <p className="guidance-col-text">{explanation.simple_explanation}</p>
              </div>

              <div className="guidance-detail-col">
                <span className="guidance-col-label">Clinical Context</span>
                <p className="guidance-col-text">{explanation.what_it_means}</p>
              </div>
            </div>

            {explanation.possible_causes && explanation.possible_causes.length > 0 && (
              <div className="guidance-causes-wrap">
                <span className="guidance-col-label">Possible Clinical Considerations</span>
                <ul className="guidance-causes-list">
                  {explanation.possible_causes.map((cause) => (
                    <li key={cause}>{cause}</li>
                  ))}
                </ul>
              </div>
            )}

            {explanation.important_note && (
              <div className="guidance-note-callout">
                <Info size={13} style={{ flexShrink: 0, marginTop: "2px" }} />
                <span>{explanation.important_note}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
