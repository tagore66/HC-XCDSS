import { useState } from "react";
import ProfessionalSelector from "./ProfessionalSelector";
import { createReview, createPaymentCheckout, simulatePaymentWebhook } from "../services/api";
import {
  Stethoscope,
  X,
  CreditCard,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Building2,
} from "lucide-react";

export default function RequestReviewModal({
  analysis,
  onClose,
  onSuccess,
}) {
  const [selectedProfessional, setSelectedProfessional] = useState(null);
  const [patientMessage, setPatientMessage] = useState(
    "I would like a professional second-opinion review of the findings in my chest X-ray."
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Payment checkout flow state
  const [step, setStep] = useState("form"); // 'form', 'checkout', 'paid'
  const [createdReview, setCreatedReview] = useState(null);
  const [paymentData, setPaymentData] = useState(null);
  const [paymentProcessing, setPaymentProcessing] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!analysis?.analysis_id) {
      setError("Cannot request review: missing valid analysis ID.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const payload = {
        analysis_id: analysis.analysis_id,
        patient_message: patientMessage.trim() || undefined,
        preferred_professional_id: selectedProfessional ? selectedProfessional.id : undefined,
      };

      // 1. Create Review Request
      const reviewResult = await createReview(payload);
      setCreatedReview(reviewResult);

      // 2. Initiate Consultation Checkout
      const checkoutResult = await createPaymentCheckout(reviewResult.id, "XRAY_PROFESSIONAL_REVIEW");
      setPaymentData(checkoutResult);

      // If Stripe-hosted checkout URL is returned, directly redirect browser to Stripe checkout
      if (
        checkoutResult?.checkout_url &&
        (checkoutResult.checkout_url.startsWith("http://") ||
         checkoutResult.checkout_url.startsWith("https://")) &&
        (checkoutResult.provider === "stripe" || checkoutResult.checkout_url.includes("checkout.stripe.com"))
      ) {
        window.location.href = checkoutResult.checkout_url;
        return;
      }

      setStep("checkout");
    } catch (err) {
      console.error("Review request error:", err);
      let errorMsg = err.message || "Failed to submit review request.";
      if (errorMsg.includes("401")) {
        errorMsg = "You must be signed in to request a doctor review.";
      } else if (errorMsg.includes("403")) {
        errorMsg = "Access denied: you can only request reviews for your own analyses.";
      } else if (errorMsg.includes("409") || errorMsg.includes("already exists")) {
        errorMsg = "An active review request is already in progress for this analysis.";
      }
      setError(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSimulatePayment = async (action = "success") => {
    if (!paymentData?.payment_id) return;
    setPaymentProcessing(true);
    setError("");

    try {
      const result = await simulatePaymentWebhook(paymentData.payment_id, action);
      if (result.status === "PAID") {
        setStep("paid");
        if (onSuccess) {
          onSuccess({ ...createdReview, payment_status: "PAID" });
        }
      } else {
        setError("Payment was declined in test simulator. Please try again.");
      }
    } catch (err) {
      setError(err.message || "Payment simulation failed.");
    } finally {
      setPaymentProcessing(false);
    }
  };

  const feeAmount = selectedProfessional?.consultation_fee
    ? `₹${Number(selectedProfessional.consultation_fee).toFixed(2)}`
    : "₹499.00";

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: "640px", maxHeight: "90vh", overflowY: "auto" }}
      >
        <div className="modal-header">
          <div>
            <div className="eyebrow" style={{ color: "var(--accent-primary)" }}>
              <Stethoscope size={12} />
              <span>PHYSICIAN SECOND OPINION</span>
            </div>
            <h3 style={{ fontSize: "17px", fontWeight: "700", color: "var(--text-primary)" }}>
              Request Professional Review
            </h3>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            disabled={submitting || paymentProcessing}
            aria-label="Close modal"
          >
            <X size={16} />
          </button>
        </div>

        {/* STEP 1: CONFIGURATION FORM */}
        {step === "form" && (
          <form onSubmit={handleSubmit} className="modal-body">
            {/* Analysis Case Summary Strip */}
            <div style={{
              background: "var(--surface-secondary)",
              border: "1px solid var(--border-main)",
              borderRadius: "var(--radius-md)",
              padding: "10px 14px",
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "8px",
              fontSize: "12px",
            }}>
              <div>
                <span style={{ color: "var(--text-muted)" }}>Case: </span>
                <strong style={{ color: "var(--text-primary)" }}>
                  Case #{analysis?.analysis_id ? String(analysis.analysis_id).substring(0, 8).toUpperCase() : "—"}
                </strong>
              </div>
              <div>
                <span style={{ color: "var(--text-muted)" }}>View: </span>
                <strong style={{ color: "var(--text-primary)" }}>{analysis.view || "Frontal"} Projection</strong>
              </div>
              <div style={{ gridColumn: "1 / -1" }}>
                <span style={{ color: "var(--text-muted)" }}>Detected: </span>
                <strong style={{ color: "var(--text-primary)" }}>
                  {analysis.detected_findings && analysis.detected_findings.length > 0
                    ? analysis.detected_findings.join(", ")
                    : "No acute abnormalities detected"}
                </strong>
              </div>
            </div>

            {/* Pricing Banner */}
            <div style={{
              background: "linear-gradient(135deg, var(--accent-light) 0%, #FFFFFF 100%)",
              border: "1px solid var(--accent-light-border)",
              borderRadius: "var(--radius-md)",
              padding: "12px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}>
              <div>
                <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--accent-active)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  {selectedProfessional ? "Specialist Consultation" : "Verified Review Pool"}
                </span>
                <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                  {selectedProfessional
                    ? `Independent assessment by ${selectedProfessional.full_name || selectedProfessional.name || "selected doctor"}.`
                    : "Instant assignment to all active verified radiologists."}
                </p>
              </div>
              <span style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-primary)" }}>
                {feeAmount}
              </span>
            </div>

            {/* Doctor Selection */}
            <div>
              <div className="field-label">Select Reviewing Physician</div>
              <ProfessionalSelector
                selectedProfessional={selectedProfessional}
                onSelectProfessional={setSelectedProfessional}
              />
            </div>

            {/* Message Input */}
            <div className="form-group">
              <label htmlFor="patientMessage" className="form-label">
                Clinical Note or Question for the Doctor (Optional)
              </label>
              <textarea
                id="patientMessage"
                rows="3"
                value={patientMessage}
                onChange={(e) => setPatientMessage(e.target.value)}
                placeholder="Mention any relevant symptoms, clinical history, or specific questions..."
                maxLength="1000"
                className="form-textarea"
              />
            </div>

            {error && (
              <div className="validation-error-card" role="alert">
                <div className="val-error-header">
                  <AlertTriangle size={15} />
                  <span>{error}</span>
                </div>
              </div>
            )}

            <div className="modal-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={onClose}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn-primary"
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <span className="spinner" />
                    <span>Initiating Checkout...</span>
                  </>
                ) : (
                  <>
                    <span>Continue to Payment ({feeAmount})</span>
                    <ArrowRight size={14} />
                  </>
                )}
              </button>
            </div>
          </form>
        )}

        {/* STEP 2: PAYMENT CHECKOUT */}
        {step === "checkout" && (
          <div className="modal-body">
            <div style={{
              background: "var(--surface-secondary)",
              border: "1px solid var(--border-main)",
              borderRadius: "var(--radius-lg)",
              padding: "16px 20px",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h4 style={{ fontSize: "14px", fontWeight: "700", color: "var(--text-primary)" }}>
                  Order Summary
                </h4>
                <span className="badge-recommended">
                  {paymentData?.provider === "stripe" ? "Stripe Sandbox" : "Test Mode"}
                </span>
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", color: "var(--text-secondary)" }}>
                <span>Professional Chest X-Ray Review</span>
                <strong style={{ color: "var(--text-primary)" }}>{paymentData?.amount_formatted || feeAmount}</strong>
              </div>

              <div style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "15px",
                fontWeight: "700",
                color: "var(--text-primary)",
                paddingTop: "8px",
                borderTop: "1px solid var(--border-subtle)",
              }}>
                <span>Total Due</span>
                <span style={{ color: "var(--accent-primary)" }}>{paymentData?.amount_formatted || feeAmount}</span>
              </div>
            </div>

            {paymentData?.checkout_url && (paymentData.checkout_url.startsWith("http://") || paymentData.checkout_url.startsWith("https://")) ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
                  Complete your consultation payment on Stripe's hosted test checkout page. You can use standard Stripe test cards.
                </p>
                {error && <div className="validation-error-card">{error}</div>}
                <div className="modal-actions">
                  <button type="button" className="btn-secondary" onClick={onClose}>
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => {
                      if (paymentData?.checkout_url) {
                        window.location.href = paymentData.checkout_url;
                      }
                    }}
                  >
                    <CreditCard size={15} />
                    <span>Pay with Stripe Checkout ↗</span>
                  </button>
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: "1.5" }}>
                  <strong>Test Payment Simulator:</strong> No real bank card will be charged. Click below to simulate checkout authorization.
                </p>
                {error && <div className="validation-error-card">{error}</div>}
                <div className="modal-actions">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => handleSimulatePayment("fail")}
                    disabled={paymentProcessing}
                  >
                    Simulate Decline
                  </button>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => handleSimulatePayment("success")}
                    disabled={paymentProcessing}
                  >
                    {paymentProcessing ? (
                      <>
                        <span className="spinner" />
                        <span>Authorizing...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 size={15} />
                        <span>Confirm Test Payment ({feeAmount})</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* STEP 3: SUCCESSFUL CONFIRMATION */}
        {step === "paid" && (
          <div className="modal-body" style={{ textAlign: "center", padding: "32px 20px" }}>
            <div style={{
              width: "48px",
              height: "48px",
              borderRadius: "var(--radius-full)",
              background: "var(--color-success-bg)",
              color: "var(--color-success)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 12px",
            }}>
              <CheckCircle2 size={28} />
            </div>
            <h4 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "4px" }}>
              Consultation Authorized & Dispatched
            </h4>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", maxWidth: "420px", margin: "0 auto 20px" }}>
              Your consultation fee has been authorized. The case is dispatched to verified physicians for clinical assessment.
            </p>

            <button
              type="button"
              className="btn-primary"
              onClick={onClose}
              style={{ margin: "0 auto" }}
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
