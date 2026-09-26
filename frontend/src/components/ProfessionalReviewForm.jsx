import { useState } from "react";
import { submitProfessionalReview } from "../services/api";

export default function ProfessionalReviewForm({
  reviewId,
  detectedFindings = [],
  onCompleteSuccess,
  onCancel,
}) {
  const [clinicalSummary, setClinicalSummary] = useState("");
  const [findingValidations, setFindingValidations] = useState({});
  const [recommendations, setRecommendations] = useState("");
  const [professionalNotes, setProfessionalNotes] = useState("");
  const [limitations, setLimitations] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleValidationChange = (findingName, value) => {
    setFindingValidations((prev) => ({
      ...prev,
      [findingName]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!clinicalSummary.trim() || clinicalSummary.trim().length < 5) {
      setError("Please provide a clinical summary of at least 5 characters.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const payload = {
        clinical_summary: clinicalSummary.trim(),
        finding_validations: findingValidations,
        recommendations: recommendations.trim() || undefined,
        professional_notes: professionalNotes.trim() || undefined,
        limitations: limitations.trim() || undefined,
      };

      const result = await submitProfessionalReview(reviewId, payload);
      if (onCompleteSuccess) {
        onCompleteSuccess(result);
      }
    } catch (err) {
      console.error("Submit professional review error:", err);
      setError(err.message || "Failed to submit professional review.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="professional-review-form-card">
      <div className="form-header">
        <div className="section-badge doctor-badge">PHYSICIAN ASSESSMENT</div>
        <h3>Submit Signed Clinical Review</h3>
        <p className="form-notice-warning">
          <strong>Notice:</strong> This response will be delivered directly to the patient as an independent second opinion. It does not overwrite the AI model probabilities or report.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="review-form-body">
        {/* FINDING VALIDATION MATRIX */}
        {detectedFindings && detectedFindings.length > 0 && (
          <div className="form-group">
            <label>AI Finding Validation</label>
            <div className="finding-validations-table">
              {detectedFindings.map((finding) => (
                <div key={finding} className="validation-row">
                  <span className="finding-name-label">{finding}</span>
                  <div className="validation-btn-group">
                    <button
                      type="button"
                      className={`btn-val ${findingValidations[finding] === "AGREED" ? "selected agreed" : ""}`}
                      onClick={() => handleValidationChange(finding, "AGREED")}
                    >
                      ✓ Agree
                    </button>
                    <button
                      type="button"
                      className={`btn-val ${findingValidations[finding] === "DISAGREED" ? "selected disagreed" : ""}`}
                      onClick={() => handleValidationChange(finding, "DISAGREED")}
                    >
                      ✗ Disagree
                    </button>
                    <button
                      type="button"
                      className={`btn-val ${findingValidations[finding] === "INCONCLUSIVE" ? "selected inconclusive" : ""}`}
                      onClick={() => handleValidationChange(finding, "INCONCLUSIVE")}
                    >
                      ? Inconclusive
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="form-group">
          <label htmlFor="clinicalSummary">
            Clinical Summary <span className="required-star">*</span>
          </label>
          <textarea
            id="clinicalSummary"
            rows="4"
            required
            value={clinicalSummary}
            onChange={(e) => setClinicalSummary(e.target.value)}
            placeholder="e.g. Findings demonstrate right middle lobe airspace consolidation consistent with acute bacterial pneumonia. No evidence of pneumothorax or pleural effusion..."
            className="form-textarea"
          />
        </div>

        <div className="form-group">
          <label htmlFor="clinicalRecommendations">
            Recommendations & Next Steps (Optional)
          </label>
          <textarea
            id="clinicalRecommendations"
            rows="3"
            value={recommendations}
            onChange={(e) => setRecommendations(e.target.value)}
            placeholder="e.g. Recommend clinical correlation, sputum cultures, outpatient antibiotic therapy, and repeat PA/lateral chest radiograph in 4 to 6 weeks..."
            className="form-textarea"
          />
        </div>

        <div className="form-group">
          <label htmlFor="professionalNotes">
            Technical & Radiographic Notes (Optional)
          </label>
          <textarea
            id="professionalNotes"
            rows="2"
            value={professionalNotes}
            onChange={(e) => setProfessionalNotes(e.target.value)}
            placeholder="e.g. DenseNet121 Grad-CAM overlay accurately highlights the anatomical area of opacity..."
            className="form-textarea"
          />
        </div>

        <div className="form-group">
          <label htmlFor="clinicalLimitations">
            Limitations (Optional)
          </label>
          <textarea
            id="clinicalLimitations"
            rows="2"
            value={limitations}
            onChange={(e) => setLimitations(e.target.value)}
            placeholder="e.g. Suboptimal inspiration or slight patient rotation noted..."
            className="form-textarea"
          />
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="form-actions-row">
          {onCancel && (
            <button
              type="button"
              className="btn-secondary"
              onClick={onCancel}
              disabled={submitting}
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            className="btn-primary btn-complete"
            disabled={submitting}
          >
            {submitting ? "Signing & Submitting..." : "✓ Sign & Lock Review"}
          </button>
        </div>
      </form>
    </div>
  );
}
