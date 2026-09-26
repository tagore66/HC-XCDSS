import React from "react";
import { CheckCircle2, X, Stethoscope, ArrowRight } from "lucide-react";

export default function PaymentSuccessModal({
  isOpen,
  paymentData,
  reviewData,
  onClose,
  onViewReviewDetails,
  onViewAllReviews,
}) {
  if (!isOpen) return null;

  const rawReviewId = reviewData?.id || paymentData?.review_request_id || "—";
  const reviewRef = rawReviewId.length > 8 ? rawReviewId.substring(0, 8).toUpperCase() : rawReviewId;
  const amountFormatted = paymentData?.amount_formatted || "₹499.00";
  const doctorName = reviewData?.professional?.full_name || "Any Available Verified Doctor";

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "480px" }}>
        <div className="modal-header">
          <div>
            <div className="eyebrow" style={{ color: "var(--color-success)" }}>
              <CheckCircle2 size={12} />
              <span>PAYMENT CONFIRMED</span>
            </div>
            <h3 style={{ fontSize: "17px", fontWeight: "700", color: "var(--text-primary)" }}>
              Consultation Authorized
            </h3>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>

        <div className="modal-body" style={{ textAlign: "center", padding: "24px 20px" }}>
          <div style={{
            width: "44px",
            height: "44px",
            borderRadius: "var(--radius-full)",
            background: "var(--color-success-bg)",
            color: "var(--color-success)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 12px",
          }}>
            <CheckCircle2 size={24} />
          </div>

          <h4 style={{ fontSize: "16px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "4px" }}>
            Your review request has been submitted
          </h4>
          <p style={{ color: "var(--text-secondary)", fontSize: "13px", marginBottom: "18px" }}>
            Payment has been securely processed. An independent specialist will evaluate your chest radiograph and report findings.
          </p>

          <div style={{
            background: "var(--surface-secondary)",
            border: "1px solid var(--border-main)",
            borderRadius: "var(--radius-lg)",
            padding: "14px 16px",
            textAlign: "left",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            fontSize: "12px",
            marginBottom: "20px",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Consultation Amount:</span>
              <strong style={{ color: "var(--text-primary)" }}>{amountFormatted}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Payment Status:</span>
              <span className="status-tag status-completed">PAID (Authorized)</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Review Reference:</span>
              <span className="review-ref-tag">Case #{reviewRef}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Assigned Specialist:</span>
              <strong style={{ color: "var(--text-primary)" }}>{doctorName}</strong>
            </div>
          </div>

          <div className="modal-actions" style={{ justifyContent: "center", gap: "10px" }}>
            {reviewData?.id && onViewReviewDetails ? (
              <button
                type="button"
                className="btn-primary"
                onClick={() => onViewReviewDetails(reviewData.id)}
              >
                <span>View Review Details</span>
                <ArrowRight size={13} />
              </button>
            ) : null}
            <button
              type="button"
              className={reviewData?.id && onViewReviewDetails ? "btn-secondary" : "btn-primary"}
              onClick={onViewAllReviews || onClose}
            >
              Go to My Doctor Reviews
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
