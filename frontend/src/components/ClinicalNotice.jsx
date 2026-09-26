import { ShieldAlert, ShieldCheck } from "lucide-react";

/**
 * ClinicalNotice component.
 * Displays medical disclaimer and clinical usage instructions.
 */
export default function ClinicalNotice() {
  return (
    <div style={{
      background: "var(--surface-primary)",
      border: "1px solid var(--border-main)",
      borderRadius: "var(--radius-lg)",
      padding: "16px 20px",
      display: "flex",
      alignItems: "flex-start",
      gap: "14px",
      marginTop: "12px",
    }}>
      <div style={{
        width: "32px",
        height: "32px",
        borderRadius: "var(--radius-md)",
        background: "var(--color-info-bg)",
        color: "var(--color-info-text)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        marginTop: "2px",
      }}>
        <ShieldCheck size={18} />
      </div>

      <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
        <strong style={{ color: "var(--text-primary)", display: "block", marginBottom: "2px", fontSize: "13px" }}>
          Important Clinical Decision Support Notice
        </strong>
        <p style={{ margin: "2px 0" }}>
          HC-XCDSS provides AI-assisted radiographic findings to support clinical evaluation. It does not replace comprehensive evaluation, diagnosis, or personalized treatment by a qualified healthcare professional.
        </p>
        <p style={{ margin: "2px 0", color: "var(--text-muted)" }}>
          Model predictions should be interpreted alongside clinical examination, history, and relevant diagnostic tests.
        </p>
      </div>
    </div>
  );
}
