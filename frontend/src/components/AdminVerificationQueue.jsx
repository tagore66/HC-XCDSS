import { useState, useEffect } from "react";
import {
  getAdminVerificationRequests,
  getAdminProfessionalDetails,
  approveProfessionalVerification,
  rejectProfessionalVerification,
  fetchDocumentBlobUrl,
} from "../services/api";
import {
  Shield,
  RotateCw,
  CheckCircle2,
  AlertTriangle,
  X,
  FileText,
  FileCheck2,
  Search,
  ExternalLink,
  Check,
} from "lucide-react";

export default function AdminVerificationQueue({ onNavigate }) {
  const [professionals, setProfessionals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("PENDING");

  // Selected professional modal state
  const [selectedItem, setSelectedItem] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Document preview modal state
  const [previewDoc, setPreviewDoc] = useState({
    isOpen: false,
    title: "",
    url: null,
    isPdf: false,
    loading: false,
    error: "",
  });

  // Rejection reason prompt modal state
  const [rejectModal, setRejectModal] = useState({
    isOpen: false,
    userId: null,
    doctorName: "",
    reason: "",
    submitting: false,
    error: "",
  });

  // Action status message
  const [actionFeedback, setActionFeedback] = useState(null);

  const fetchQueue = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getAdminVerificationRequests(statusFilter);
      setProfessionals(data || []);
    } catch (err) {
      console.error("Error loading verification queue:", err);
      setError(err.message || "Failed to load verification queue.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [statusFilter]);

  const handleInspect = async (user) => {
    setDetailLoading(true);
    setError("");
    try {
      const details = await getAdminProfessionalDetails(user.id);
      setSelectedItem(details);
    } catch (err) {
      console.error("Error loading details:", err);
      setError(err.message || "Could not load professional details.");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleApprove = async (userId, doctorName) => {
    if (!window.confirm(`Are you sure you want to approve medical credentials for ${doctorName}? This will unlock full clinical review access.`)) {
      return;
    }

    try {
      await approveProfessionalVerification(userId);
      setActionFeedback({
        type: "success",
        message: `Successfully verified Dr. ${doctorName}. Clinical review capabilities are now unlocked.`,
      });
      setSelectedItem(null);
      await fetchQueue();
    } catch (err) {
      console.error("Approval error:", err);
      alert(`Approval failed: ${err.message}`);
    }
  };

  const handleOpenReject = (userId, doctorName) => {
    setRejectModal({
      isOpen: true,
      userId,
      doctorName,
      reason: "",
      submitting: false,
      error: "",
    });
  };

  const handleSubmitReject = async (e) => {
    e.preventDefault();
    if (!rejectModal.reason.trim() || rejectModal.reason.trim().length < 5) {
      setRejectModal((prev) => ({
        ...prev,
        error: "Please provide a clear rejection reason (minimum 5 characters).",
      }));
      return;
    }

    setRejectModal((prev) => ({ ...prev, submitting: true, error: "" }));

    try {
      await rejectProfessionalVerification(rejectModal.userId, rejectModal.reason.trim());
      setActionFeedback({
        type: "info",
        message: `Verification application for ${rejectModal.doctorName} was rejected with recorded reason.`,
      });
      setRejectModal({ isOpen: false, userId: null, doctorName: "", reason: "", submitting: false, error: "" });
      setSelectedItem(null);
      await fetchQueue();
    } catch (err) {
      console.error("Rejection error:", err);
      setRejectModal((prev) => ({ ...prev, submitting: false, error: err.message || "Failed to reject application." }));
    }
  };

  const handleViewDocument = async (userId, docType, docTitle, filename) => {
    setPreviewDoc({
      isOpen: true,
      title: docTitle,
      url: null,
      isPdf: filename ? filename.toLowerCase().endsWith(".pdf") : false,
      loading: true,
      error: "",
    });

    try {
      const blobUrl = await fetchDocumentBlobUrl(userId, docType);
      setPreviewDoc((prev) => ({
        ...prev,
        url: blobUrl,
        loading: false,
      }));
    } catch (err) {
      console.error("Document fetch error:", err);
      setPreviewDoc((prev) => ({
        ...prev,
        loading: false,
        error: err.message || "Failed to retrieve document from secure storage.",
      }));
    }
  };

  const closePreviewDoc = () => {
    if (previewDoc.url) {
      URL.revokeObjectURL(previewDoc.url);
    }
    setPreviewDoc({
      isOpen: false,
      title: "",
      url: null,
      isPdf: false,
      loading: false,
      error: "",
    });
  };

  return (
    <div className="results-screen-container" style={{ maxWidth: "1200px", margin: "20px auto" }}>
      {/* Header Bar */}
      <div className="results-top-bar">
        <div>
          <div className="eyebrow" style={{ color: "var(--color-info-text)" }}>
            <Shield size={12} />
            <span>CLINICAL GOVERNANCE & VERIFICATION</span>
          </div>
          <h2>Professional Verification Administration</h2>
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "2px" }}>
            Inspect medical registration credentials, examine council certificates, and authorize physician review permissions.
          </p>
        </div>

        <button
          type="button"
          className="btn-secondary btn-sm"
          onClick={fetchQueue}
          disabled={loading}
        >
          <RotateCw size={13} className={loading ? "spinner" : ""} />
          <span>{loading ? "Refreshing..." : "Refresh Queue"}</span>
        </button>
      </div>

      {/* Action Feedback Banner */}
      {actionFeedback && (
        <div style={{
          padding: "10px 14px",
          borderRadius: "var(--radius-md)",
          background: actionFeedback.type === "success" ? "var(--color-success-bg)" : "var(--color-info-bg)",
          border: `1px solid ${actionFeedback.type === "success" ? "var(--color-success-border)" : "var(--color-info-border)"}`,
          color: actionFeedback.type === "success" ? "var(--color-success-text)" : "var(--color-info-text)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: "13px",
          fontWeight: "500",
        }}>
          <span>{actionFeedback.message}</span>
          <button
            type="button"
            onClick={() => setActionFeedback(null)}
            style={{ background: "none", border: "none", cursor: "pointer", color: "inherit" }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="portal-tab-bar" style={{ margin: 0 }}>
        {[
          { key: "PENDING", label: "Pending Verification" },
          { key: "VERIFIED", label: "Verified Physicians" },
          { key: "REJECTED", label: "Rejected" },
          { key: "ALL", label: "All Applicants" },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            className={`portal-tab ${statusFilter === tab.key ? "active" : ""}`}
            onClick={() => setStatusFilter(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="validation-error-card">
          <div className="val-error-header">
            <AlertTriangle size={15} />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Table of Verification Requests */}
      <div className="pro-card" style={{ padding: 0 }}>
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
            Loading professional verification queue...
          </div>
        ) : professionals.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
            No healthcare professionals found matching the selected filter ({statusFilter}).
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "13px" }}>
            <thead>
              <tr style={{ background: "var(--surface-secondary)", borderBottom: "1px solid var(--border-main)", color: "var(--text-muted)", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                <th style={{ padding: "12px 16px" }}>Professional</th>
                <th style={{ padding: "12px 16px" }}>Registration & Council</th>
                <th style={{ padding: "12px 16px" }}>Specialty</th>
                <th style={{ padding: "12px 16px" }}>Documents</th>
                <th style={{ padding: "12px 16px" }}>Status</th>
                <th style={{ padding: "12px 16px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {professionals.map(({ user, profile }) => {
                const status = profile?.verification_status || "PENDING";
                return (
                  <tr key={user.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    <td style={{ padding: "12px 16px" }}>
                      <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{user.full_name || "Doctor"}</div>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>{user.email}</div>
                    </td>

                    <td style={{ padding: "12px 16px" }}>
                      <div style={{ fontWeight: 500, color: "var(--text-primary)" }}>{profile?.registration_number || profile?.license_number || "—"}</div>
                      <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>{profile?.state_medical_council || profile?.license_country_or_state || "—"}</div>
                    </td>

                    <td style={{ padding: "12px 16px", color: "var(--text-secondary)" }}>
                      {profile?.specialty || "General Medicine"}
                      {profile?.qualification && <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{profile.qualification}</div>}
                    </td>

                    <td style={{ padding: "12px 16px" }}>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <span
                          title={profile?.has_registration_certificate ? "Registration Certificate Uploaded" : "Missing"}
                          className="status-tag"
                          style={{
                            background: profile?.has_registration_certificate ? "var(--color-success-bg)" : "var(--surface-secondary)",
                            color: profile?.has_registration_certificate ? "var(--color-success-text)" : "var(--text-muted)",
                            fontSize: "10px",
                          }}
                        >
                          📜 Cert
                        </span>
                        <span
                          title={profile?.has_identity_document ? "Medical ID Uploaded" : "Missing"}
                          className="status-tag"
                          style={{
                            background: profile?.has_identity_document ? "var(--color-success-bg)" : "var(--surface-secondary)",
                            color: profile?.has_identity_document ? "var(--color-success-text)" : "var(--text-muted)",
                            fontSize: "10px",
                          }}
                        >
                          🪪 ID
                        </span>
                      </div>
                    </td>

                    <td style={{ padding: "12px 16px" }}>
                      <span className={`status-tag status-${status.toLowerCase()}`}>
                        {status}
                      </span>
                    </td>

                    <td style={{ padding: "12px 16px", textAlign: "right" }}>
                      <div style={{ display: "flex", justifyContent: "flex-end", gap: "6px" }}>
                        <button
                          type="button"
                          className="btn-secondary btn-sm"
                          onClick={() => handleInspect(user)}
                        >
                          Inspect
                        </button>

                        {status === "PENDING" && (
                          <>
                            <button
                              type="button"
                              className="btn-primary btn-sm"
                              onClick={() => handleApprove(user.id, user.full_name || "Doctor")}
                              title="Approve credentials"
                            >
                              <Check size={13} />
                              <span>Approve</span>
                            </button>
                            <button
                              type="button"
                              className="btn-danger btn-sm"
                              onClick={() => handleOpenReject(user.id, user.full_name || "Doctor")}
                              title="Reject application"
                            >
                              <X size={13} />
                              <span>Reject</span>
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Inspection Detail Modal */}
      {selectedItem && (
        <div className="modal-overlay" onClick={() => setSelectedItem(null)}>
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: "600px", maxHeight: "90vh", overflowY: "auto" }}
          >
            <div className="modal-header">
              <div>
                <span className="eyebrow">APPLICANT CREDENTIALS</span>
                <h3 style={{ fontSize: "16px", fontWeight: "700" }}>{selectedItem.user.full_name || "Doctor"}</h3>
              </div>
              <button className="modal-close-btn" onClick={() => setSelectedItem(null)}>
                <X size={16} />
              </button>
            </div>

            <div className="modal-body">
              <div style={{
                background: "var(--surface-secondary)",
                border: "1px solid var(--border-main)",
                borderRadius: "var(--radius-lg)",
                padding: "16px",
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "12px",
                fontSize: "12px",
              }}>
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>Registration Number</span>
                  <strong style={{ color: "var(--text-primary)" }}>{selectedItem.profile.registration_number || "—"}</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>State Council</span>
                  <strong style={{ color: "var(--text-primary)" }}>{selectedItem.profile.state_medical_council || "—"}</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>Specialty</span>
                  <strong style={{ color: "var(--text-primary)" }}>{selectedItem.profile.specialty || "—"}</strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", display: "block" }}>Affiliation</span>
                  <strong style={{ color: "var(--text-primary)" }}>{selectedItem.profile.hospital_or_clinic || "Independent Practice"}</strong>
                </div>
              </div>

              {/* Document Review Buttons */}
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "10px" }}>
                <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-primary)" }}>Uploaded Verification Documents</span>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={() => handleViewDocument(selectedItem.user.id, "registration_certificate", "Medical Council Registration Certificate", selectedItem.profile.registration_certificate_filename)}
                  >
                    <FileText size={13} />
                    <span>View Registration Certificate ↗</span>
                  </button>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={() => handleViewDocument(selectedItem.user.id, "identity_document", "Medical Council ID / Government ID", selectedItem.profile.identity_document_filename)}
                  >
                    <FileText size={13} />
                    <span>View ID Document ↗</span>
                  </button>
                </div>
              </div>

              {selectedItem.profile.verification_status === "PENDING" && (
                <div className="modal-actions" style={{ marginTop: "16px" }}>
                  <button
                    type="button"
                    className="btn-danger btn-sm"
                    onClick={() => handleOpenReject(selectedItem.user.id, selectedItem.user.full_name || "Doctor")}
                  >
                    Reject Application
                  </button>
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    onClick={() => handleApprove(selectedItem.user.id, selectedItem.user.full_name || "Doctor")}
                  >
                    Approve Credentials
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Document Preview Lightbox Modal */}
      {previewDoc.isOpen && (
        <div className="modal-overlay" onClick={closePreviewDoc}>
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: "800px", maxHeight: "90vh", display: "flex", flexDirection: "column" }}
          >
            <div className="modal-header">
              <h3 style={{ fontSize: "15px", fontWeight: "700" }}>{previewDoc.title}</h3>
              <button className="modal-close-btn" onClick={closePreviewDoc}>
                <X size={16} />
              </button>
            </div>
            <div className="modal-body" style={{ flex: 1, minHeight: "450px", display: "flex", alignItems: "center", justifyContent: "center" }}>
              {previewDoc.loading ? (
                <div style={{ textAlign: "center", color: "var(--text-muted)" }}>
                  <span className="spinner" style={{ width: "20px", height: "20px" }} />
                  <p style={{ marginTop: "8px", fontSize: "12px" }}>Loading document from encrypted storage...</p>
                </div>
              ) : previewDoc.error ? (
                <div className="validation-error-card">{previewDoc.error}</div>
              ) : previewDoc.isPdf ? (
                <iframe src={previewDoc.url} title={previewDoc.title} style={{ width: "100%", height: "480px", border: "none" }} />
              ) : (
                <img src={previewDoc.url} alt={previewDoc.title} style={{ maxHeight: "480px", objectFit: "contain", margin: "0 auto" }} />
              )}
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {rejectModal.isOpen && (
        <div className="modal-overlay" onClick={() => setRejectModal((prev) => ({ ...prev, isOpen: false }))}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "460px" }}>
            <div className="modal-header">
              <h3 style={{ fontSize: "15px", fontWeight: "700", color: "var(--color-danger-text)" }}>
                Reject Verification Application
              </h3>
              <button className="modal-close-btn" onClick={() => setRejectModal((prev) => ({ ...prev, isOpen: false }))}>
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleSubmitReject} className="modal-body">
              <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                State reason for rejecting credentials for <strong>{rejectModal.doctorName}</strong>. This feedback will be recorded in their portal.
              </p>
              <textarea
                rows="3"
                className="form-textarea"
                placeholder="e.g. Medical registration certificate could not be verified with state council records..."
                value={rejectModal.reason}
                onChange={(e) => setRejectModal((prev) => ({ ...prev, reason: e.target.value }))}
                required
              />
              {rejectModal.error && (
                <div className="validation-error-card">{rejectModal.error}</div>
              )}
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => setRejectModal((prev) => ({ ...prev, isOpen: false }))}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-danger btn-sm"
                  disabled={rejectModal.submitting}
                >
                  {rejectModal.submitting ? "Rejecting..." : "Confirm Rejection"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
