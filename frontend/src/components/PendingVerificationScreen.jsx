import { useState } from "react";
import {
  Clock,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  LogOut,
  ShieldAlert,
  FileText,
} from "lucide-react";

export default function PendingVerificationScreen({
  currentUser,
  onRefresh,
  onLogout,
}) {
  const [refreshing, setRefreshing] = useState(false);

  const profile = currentUser?.professional_profile || {};
  const status = profile.verification_status || "PENDING";
  const isPending = status === "PENDING";
  const isRejected = status === "REJECTED";
  const isSuspended = status === "SUSPENDED";

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      if (onRefresh) await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="pro-card" style={{ maxWidth: "680px", margin: "40px auto", padding: "32px" }}>
      {/* Header Badge */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: "20px",
        paddingBottom: "16px",
        borderBottom: "1px solid var(--border-subtle)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{
            width: "42px",
            height: "42px",
            borderRadius: "var(--radius-md)",
            background: isPending ? "var(--color-warning-bg)" : isRejected ? "var(--color-danger-bg)" : "var(--surface-secondary)",
            color: isPending ? "var(--color-warning-text)" : isRejected ? "var(--color-danger-text)" : "var(--text-secondary)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}>
            {isPending ? <Clock size={20} /> : <AlertTriangle size={20} />}
          </div>
          <div>
            <h2 style={{ fontSize: "17px", fontWeight: "700", color: "var(--text-primary)" }}>
              {isPending && "Credential Verification Pending"}
              {isRejected && "Verification Request Not Approved"}
              {isSuspended && "Account Suspended"}
            </h2>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
              Healthcare Professional: {currentUser?.full_name || currentUser?.email}
            </p>
          </div>
        </div>

        <span className={`status-tag status-${status.toLowerCase()}`}>
          {status}
        </span>
      </div>

      {/* Main Notice Banner */}
      {isPending && (
        <div style={{
          background: "var(--color-warning-bg)",
          border: "1px solid var(--color-warning-border)",
          borderRadius: "var(--radius-md)",
          padding: "14px 16px",
          marginBottom: "20px",
          color: "var(--color-warning-text)",
          fontSize: "13px",
          lineHeight: "1.5",
        }}>
          <strong>Under Review by Platform Administration:</strong> Your medical registration credentials and verification documents have been received. Clinical workspace tools will unlock once approved.
        </div>
      )}

      {isRejected && (
        <div style={{
          background: "var(--color-danger-bg)",
          border: "1px solid var(--color-danger-border)",
          borderRadius: "var(--radius-md)",
          padding: "14px 16px",
          marginBottom: "20px",
          color: "var(--color-danger-text)",
          fontSize: "13px",
          lineHeight: "1.5",
        }}>
          <strong>Verification Decision: Rejected</strong>
          <p style={{ marginTop: "4px" }}>
            {profile.rejection_reason || "Medical credentials could not be verified at this time."}
          </p>
        </div>
      )}

      {/* Submitted Details Card */}
      <div style={{
        background: "var(--surface-secondary)",
        border: "1px solid var(--border-main)",
        borderRadius: "var(--radius-lg)",
        padding: "16px",
        marginBottom: "22px",
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "12px",
        fontSize: "12px",
      }}>
        <div>
          <span style={{ color: "var(--text-muted)", display: "block" }}>Registration Number</span>
          <strong style={{ color: "var(--text-primary)" }}>{profile.registration_number || profile.license_number || "—"}</strong>
        </div>
        <div>
          <span style={{ color: "var(--text-muted)", display: "block" }}>State Medical Council</span>
          <strong style={{ color: "var(--text-primary)" }}>{profile.state_medical_council || profile.license_country_or_state || "—"}</strong>
        </div>
        <div>
          <span style={{ color: "var(--text-muted)", display: "block" }}>Specialty</span>
          <strong style={{ color: "var(--text-primary)" }}>{profile.specialty || "Radiologist"}</strong>
        </div>
        <div>
          <span style={{ color: "var(--text-muted)", display: "block" }}>Affiliation</span>
          <strong style={{ color: "var(--text-primary)" }}>{profile.hospital_or_clinic || "Independent Practice"}</strong>
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <button
          type="button"
          className="btn-secondary btn-sm"
          onClick={onLogout}
        >
          <LogOut size={13} />
          <span>Sign Out</span>
        </button>

        <button
          type="button"
          className="btn-primary btn-sm"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          <RotateCw size={13} className={refreshing ? "spinner" : ""} />
          <span>{refreshing ? "Checking..." : "Refresh Status"}</span>
        </button>
      </div>
    </div>
  );
}
