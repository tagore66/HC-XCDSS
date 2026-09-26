import { useState, useEffect, useRef } from "react";
import { loginUser, registerUser, registerProfessional } from "../services/api";
import {
  Activity,
  X,
  Eye,
  EyeOff,
  User,
  Stethoscope,
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
  FileText,
  UploadCloud,
} from "lucide-react";

export default function AuthModal({
  isOpen,
  onClose,
  onAuthSuccess,
  initialMode = "login",
  initialRole = "PATIENT",
}) {
  const [isRegister, setIsRegister] = useState(initialMode === "register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [role, setRole] = useState(initialRole || "PATIENT"); // "PATIENT" or "PROFESSIONAL"

  // Professional Credentials state
  const [registrationNumber, setRegistrationNumber] = useState("");
  const [stateMedicalCouncil, setStateMedicalCouncil] = useState("");
  const [registrationYear, setRegistrationYear] = useState("");
  const [specialty, setSpecialty] = useState("Radiologist");
  const [qualification, setQualification] = useState("");
  const [hospitalOrClinic, setHospitalOrClinic] = useState("");
  const [locationCity, setLocationCity] = useState("");
  const [locationState, setLocationState] = useState("");
  const [regCertFile, setRegCertFile] = useState(null);
  const [idDocFile, setIdDocFile] = useState(null);
  const [suppDocFile, setSuppDocFile] = useState(null);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const modalRef = useRef(null);

  // Sync mode and role when opened
  useEffect(() => {
    if (isOpen) {
      setIsRegister(initialMode === "register");
      if (initialRole) setRole(initialRole);
      setError("");
      setShowPassword(false);
    }
  }, [initialMode, initialRole, isOpen]);

  // Keyboard accessibility: Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen && !loading) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, loading, onClose]);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (isRegister && !fullName.trim()) {
      setError("Please enter your full name.");
      return;
    }

    if (!email.trim() || !password) {
      setError("Please fill in all required fields.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    // Professional verification validations
    if (isRegister && role === "PROFESSIONAL") {
      if (!registrationNumber.trim()) {
        setError("Medical Council Registration Number is required.");
        return;
      }
      if (!stateMedicalCouncil.trim()) {
        setError("State Medical Council / Licensing Authority is required.");
        return;
      }
      if (!regCertFile) {
        setError("Medical Registration Certificate document is required for verification.");
        return;
      }
      if (!idDocFile) {
        setError("Medical Identity ID / Government ID document is required for verification.");
        return;
      }
    }

    setLoading(true);

    try {
      if (isRegister) {
        if (role === "PROFESSIONAL") {
          const formData = new FormData();
          formData.append("full_name", fullName.trim());
          formData.append("email", email.trim());
          formData.append("password", password);
          if (username.trim()) formData.append("username", username.trim());
          formData.append("registration_number", registrationNumber.trim());
          formData.append("state_medical_council", stateMedicalCouncil.trim());
          if (registrationYear.trim()) formData.append("registration_year", registrationYear.trim());
          formData.append("specialty", specialty || "Radiologist");
          if (qualification.trim()) formData.append("qualification", qualification.trim());
          if (hospitalOrClinic.trim()) formData.append("hospital_or_clinic", hospitalOrClinic.trim());
          if (locationCity.trim()) formData.append("location_city", locationCity.trim());
          if (locationState.trim()) formData.append("location_state", locationState.trim());
          formData.append("location_country", "India");
          formData.append("registration_certificate", regCertFile);
          formData.append("identity_document", idDocFile);
          if (suppDocFile) formData.append("supporting_document", suppDocFile);

          await registerProfessional(formData);
        } else {
          const regPayload = {
            email: email.trim(),
            password,
            full_name: fullName.trim(),
            role: "PATIENT",
          };
          if (username.trim()) {
            regPayload.username = username.trim();
          }
          await registerUser(regPayload);
        }

        // Auto-login after registration
        const loginData = await loginUser(email.trim(), password);
        onAuthSuccess(loginData);
      } else {
        const loginData = await loginUser(email.trim(), password);
        onAuthSuccess(loginData);
      }
      onClose();
    } catch (err) {
      console.error("Auth error:", err);
      setError(err.message || "Authentication failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="auth-modal-overlay"
      onClick={!loading ? onClose : undefined}
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
    >
      <div
        className="auth-modal-card"
        onClick={(e) => e.stopPropagation()}
        ref={modalRef}
        style={isRegister && role === "PROFESSIONAL" ? { maxWidth: "600px", maxHeight: "90vh", overflowY: "auto" } : { maxWidth: "440px" }}
      >
        {/* Modal Header */}
        <div className="auth-card-header">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <div className="brand-mark" style={{ width: "28px", height: "28px" }}>
              <Activity size={14} />
            </div>
            <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--text-muted)", letterSpacing: "0.5px" }}>
              HC-XCDSS
            </span>
          </div>

          <button
            type="button"
            className="auth-close-btn"
            onClick={onClose}
            disabled={loading}
            aria-label="Close authentication dialog"
          >
            <X size={16} />
          </button>
        </div>

        {/* Title & Subtitle */}
        <div style={{ padding: "20px 24px 10px" }}>
          <h2 id="auth-modal-title" style={{ fontSize: "20px", fontWeight: "700", color: "var(--text-primary)", letterSpacing: "-0.3px" }}>
            {isRegister
              ? (role === "PROFESSIONAL" ? "Physician Registration" : "Create Account")
              : "Sign In"}
          </h2>
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "3px" }}>
            {isRegister
              ? (role === "PROFESSIONAL"
                  ? "Submit medical credentials for clinical review verification."
                  : "Access your personal clinical chest X-ray workspace.")
              : "Sign in to your HC-XCDSS workspace."}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ padding: "10px 24px 24px", display: "flex", flexDirection: "column", gap: "14px" }} noValidate>
          {error && (
            <div className="validation-error-card" role="alert" style={{ margin: 0 }}>
              <div className="val-error-header">
                <AlertTriangle size={15} />
                <span>{error}</span>
              </div>
            </div>
          )}

          {/* Role Toggle for Registration */}
          {isRegister && (
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Account Type</label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                <button
                  type="button"
                  className={`portal-tab ${role === "PATIENT" ? "active" : ""}`}
                  style={{ width: "100%", justifyContent: "center", display: "flex", alignItems: "center", gap: "6px" }}
                  onClick={() => setRole("PATIENT")}
                  disabled={loading}
                >
                  <User size={14} />
                  <span>Patient</span>
                </button>
                <button
                  type="button"
                  className={`portal-tab ${role === "PROFESSIONAL" ? "active" : ""}`}
                  style={{ width: "100%", justifyContent: "center", display: "flex", alignItems: "center", gap: "6px" }}
                  onClick={() => setRole("PROFESSIONAL")}
                  disabled={loading}
                >
                  <Stethoscope size={14} />
                  <span>Physician</span>
                </button>
              </div>
            </div>
          )}

          {isRegister && (
            <div className="form-group" style={{ margin: 0 }}>
              <label htmlFor="authFullName" className="form-label">
                Full Name
              </label>
              <input
                id="authFullName"
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder={role === "PROFESSIONAL" ? "e.g. Dr. Jane Smith, MD" : "e.g. John Doe"}
                className="form-textarea"
                style={{ height: "40px", resize: "none" }}
                disabled={loading}
                autoFocus
              />
            </div>
          )}

          {isRegister && (
            <div className="form-group" style={{ margin: 0 }}>
              <label htmlFor="authUsername" className="form-label">
                Username <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: "normal" }}>(Optional)</span>
              </label>
              <input
                id="authUsername"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_.-]/g, ""))}
                placeholder={role === "PROFESSIONAL" ? "e.g. dr_smith" : "e.g. tagore"}
                className="form-textarea"
                style={{ height: "40px", resize: "none" }}
                disabled={loading}
              />
            </div>
          )}

          <div className="form-group" style={{ margin: 0 }}>
            <label htmlFor="authEmailInput" className="form-label">
              Email Address
            </label>
            <input
              id="authEmailInput"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@organization.com"
              className="form-textarea"
              style={{ height: "40px", resize: "none" }}
              disabled={loading}
              autoComplete="email"
            />
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <label htmlFor="authPasswordInput" className="form-label">
                Password
              </label>
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{ fontSize: "11px", color: "var(--text-muted)", cursor: "pointer" }}
                tabIndex="-1"
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            <input
              id="authPasswordInput"
              type={showPassword ? "text" : "password"}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              className="form-textarea"
              style={{ height: "40px", resize: "none" }}
              disabled={loading}
              autoComplete={isRegister ? "new-password" : "current-password"}
            />
          </div>

          {/* Professional Credentials Section */}
          {isRegister && role === "PROFESSIONAL" && (
            <div style={{
              background: "var(--surface-secondary)",
              border: "1px solid var(--border-main)",
              borderRadius: "var(--radius-lg)",
              padding: "16px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}>
              <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--text-primary)" }}>
                Medical Credentials & Documents
              </span>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Registration No. *</label>
                  <input
                    type="text"
                    required
                    value={registrationNumber}
                    onChange={(e) => setRegistrationNumber(e.target.value)}
                    placeholder="e.g. MMC-12345"
                    className="form-textarea"
                    style={{ height: "36px", resize: "none", fontSize: "12px" }}
                    disabled={loading}
                  />
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Medical Council *</label>
                  <input
                    type="text"
                    required
                    value={stateMedicalCouncil}
                    onChange={(e) => setStateMedicalCouncil(e.target.value)}
                    placeholder="e.g. State Medical Council"
                    className="form-textarea"
                    style={{ height: "36px", resize: "none", fontSize: "12px" }}
                    disabled={loading}
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Specialty</label>
                  <select
                    value={specialty}
                    onChange={(e) => setSpecialty(e.target.value)}
                    className="form-select"
                    style={{ fontSize: "12px" }}
                    disabled={loading}
                  >
                    <option value="Radiologist">Radiologist</option>
                    <option value="Pulmonologist">Pulmonologist</option>
                    <option value="General Physician">General Physician</option>
                    <option value="Thoracic Specialist">Thoracic Specialist</option>
                    <option value="Internal Medicine">Internal Medicine</option>
                  </select>
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Qualifications</label>
                  <input
                    type="text"
                    value={qualification}
                    onChange={(e) => setQualification(e.target.value)}
                    placeholder="e.g. MBBS, MD"
                    className="form-textarea"
                    style={{ height: "36px", resize: "none", fontSize: "12px" }}
                    disabled={loading}
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">City</label>
                  <input
                    type="text"
                    value={locationCity}
                    onChange={(e) => setLocationCity(e.target.value)}
                    placeholder="e.g. Mumbai"
                    className="form-textarea"
                    style={{ height: "36px", resize: "none", fontSize: "12px" }}
                    disabled={loading}
                  />
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Hospital / Practice</label>
                  <input
                    type="text"
                    value={hospitalOrClinic}
                    onChange={(e) => setHospitalOrClinic(e.target.value)}
                    placeholder="e.g. City Hospital"
                    className="form-textarea"
                    style={{ height: "36px", resize: "none", fontSize: "12px" }}
                    disabled={loading}
                  />
                </div>
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Registration Certificate (PDF/PNG/JPG) *</label>
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  required
                  onChange={(e) => setRegCertFile(e.target.files[0] || null)}
                  disabled={loading}
                  style={{ fontSize: "12px" }}
                />
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Medical Council ID / Identity Document *</label>
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg"
                  required
                  onChange={(e) => setIdDocFile(e.target.files[0] || null)}
                  disabled={loading}
                  style={{ fontSize: "12px" }}
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            className="btn-primary"
            style={{ width: "100%", padding: "11px", marginTop: "6px" }}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner" />
                <span>{isRegister ? "Submitting..." : "Signing in..."}</span>
              </>
            ) : (
              <>
                <span>{isRegister ? (role === "PROFESSIONAL" ? "Submit Registration" : "Create Account") : "Sign In"}</span>
                <ArrowRight size={14} />
              </>
            )}
          </button>

          {/* Toggle Register / Sign In */}
          <div style={{ display: "flex", justifyContent: "center", gap: "6px", fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
            <span>{isRegister ? "Already have an account?" : "Don't have an account?"}</span>
            <button
              type="button"
              onClick={() => {
                setIsRegister(!isRegister);
                setError("");
              }}
              style={{ color: "var(--accent-primary)", fontWeight: "600" }}
              disabled={loading}
            >
              {isRegister ? "Sign in" : "Create account"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
