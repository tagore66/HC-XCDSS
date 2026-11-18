import { ShieldAlert, ShieldCheck, AlertCircle } from "lucide-react";

/**
 * ClinicalNotice component.
 * Displays explicit clinical safety, interpretation guidelines, and decision support boundaries.
 */
export default function ClinicalNotice() {
  return (
    <div className="clinical-safety-card">
      <div className="safety-card-header">
        <div className="safety-icon-badge">
          <ShieldCheck size={18} />
        </div>
        <div>
          <span className="safety-eyebrow">STAGE 5 • WHAT SHOULD I KNOW?</span>
          <h4 className="safety-title">Important Medical Decision Support Notice</h4>
        </div>
      </div>

      <div className="safety-card-body">
        <p className="safety-main-text">
          These are AI-generated findings, not a medical diagnosis. Their clinical significance depends on your symptoms, medical history, physical examination, and other diagnostic information.
        </p>

        <div className="safety-guidelines-grid">
          <div className="safety-guideline-item">
            <span className="guideline-bullet">•</span>
            <div>
              <strong>Clinical Correlation Required:</strong> All AI findings must be evaluated in consultation with a qualified doctor alongside your full medical history and physical exam.
            </div>
          </div>

          <div className="safety-guideline-item">
            <span className="guideline-bullet">•</span>
            <div>
              <strong>AI Flagged Findings:</strong> An AI-flagged pattern indicates model visual feature alignment above an operating threshold. It is <em>not a definitive confirmation</em> of active disease or pathology.
            </div>
          </div>

          <div className="safety-guideline-item">
            <span className="guideline-bullet">•</span>
            <div>
              <strong>Findings Not Flagged:</strong> When a condition is not flagged by the AI, it means the model did not detect a prominent pattern above its threshold on this view. It <em>does not rule out all medical conditions</em> or subtle abnormalities.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
