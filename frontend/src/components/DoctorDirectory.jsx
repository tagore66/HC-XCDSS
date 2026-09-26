import { useState, useEffect } from "react";
import { getProfessionalsDirectory } from "../services/api";
import {
  Stethoscope,
  Search,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  Building2,
  RotateCw,
  ArrowRight,
  ShieldCheck,
  Check,
} from "lucide-react";

export default function DoctorDirectory({
  selectedProfessional,
  onSelectProfessional,
  onContinue,
  showPoolOption = true,
  showHeader = true,
  actionLabel = "Continue",
}) {
  const [professionals, setProfessionals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cityFilter, setCityFilter] = useState("");
  const [specialtyFilter, setSpecialtyFilter] = useState("");

  const fetchDirectory = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getProfessionalsDirectory({
        city: cityFilter.trim() || undefined,
        specialization: specialtyFilter.trim() || undefined,
      });
      setProfessionals(data?.professionals || []);
    } catch (err) {
      console.error("Doctor Directory fetch error:", err);
      setError("Unable to load verified professionals right now. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDirectory();
  }, [cityFilter, specialtyFilter]);

  const handleClearFilters = () => {
    setCityFilter("");
    setSpecialtyFilter("");
  };

  const hasActiveFilters = Boolean(cityFilter.trim() || specialtyFilter.trim());

  return (
    <div className="doctor-directory-container">
      {showHeader && (
        <div className="directory-header-section">
          <div className="eyebrow">
            <Stethoscope size={12} />
            <span>VERIFIED SPECIALISTS</span>
          </div>
          <h3 className="directory-title">Find a Verified Professional</h3>
          <p className="directory-subtitle">
            Select a verified healthcare professional for an independent second opinion, or choose the open clinical review pool.
          </p>
        </div>
      )}

      {/* FILTER CONTROLS */}
      <div className="directory-filter-bar">
        <div className="filter-field">
          <label htmlFor="directoryCityFilter" className="filter-label">
            Location (City / Region)
          </label>
          <input
            id="directoryCityFilter"
            type="text"
            className="filter-input"
            placeholder="Search by city (e.g. Mumbai, Delhi)"
            value={cityFilter}
            onChange={(e) => setCityFilter(e.target.value)}
          />
        </div>

        <div className="filter-field">
          <label htmlFor="directorySpecialtyFilter" className="filter-label">
            Specialization
          </label>
          <input
            id="directorySpecialtyFilter"
            type="text"
            className="filter-input"
            placeholder="Search by specialty (e.g. Radiology, Pulmonology)"
            value={specialtyFilter}
            onChange={(e) => setSpecialtyFilter(e.target.value)}
          />
        </div>

        {hasActiveFilters && (
          <button
            type="button"
            className="btn-clear-filters"
            onClick={handleClearFilters}
            aria-label="Clear all directory filters"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* LOADING STATE */}
      {loading && (
        <div className="directory-cards-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="doctor-card" style={{ height: "180px", opacity: 0.6 }} />
          ))}
        </div>
      )}

      {/* ERROR STATE */}
      {!loading && error && (
        <div className="validation-error-card" role="alert">
          <div className="val-error-header">
            <AlertTriangle size={16} />
            <strong>Unable to load directory</strong>
          </div>
          <p className="val-error-desc">{error}</p>
          <button type="button" className="btn-secondary btn-sm" onClick={fetchDirectory}>
            Try Again
          </button>
        </div>
      )}

      {/* DOCTORS LIST */}
      {!loading && !error && (
        <div className="directory-cards-grid">
          {/* Default Any Available Doctor Option */}
          {showPoolOption && (
            <div
              className={`doctor-card pool-card ${!selectedProfessional ? "is-selected" : ""}`}
              onClick={() => onSelectProfessional(null)}
            >
              <div className="doctor-card-header">
                <div className="doctor-avatar-circle pool-avatar">
                  <Building2 size={20} />
                </div>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <div className="doctor-name-row">
                    <h4 className="doctor-name">Any Available Verified Doctor</h4>
                    <span className="badge-recommended">Recommended</span>
                  </div>
                  <p className="doctor-qualification">Fastest Matching Pool</p>
                </div>
              </div>

              <div className="doctor-card-body">
                <p style={{ color: "var(--text-secondary)", lineHeight: "1.5" }}>
                  Your case will be instantly dispatched to all active verified radiologists for prompt clinical assessment.
                </p>

                <div className="doctor-meta-grid">
                  <div className="meta-item">
                    <span className="meta-label">Coverage</span>
                    <span style={{ fontWeight: "600", color: "var(--text-primary)" }}>All Verified Doctors</span>
                  </div>
                  <div className="meta-item">
                    <span className="meta-label">Review Fee</span>
                    <span className="meta-val fee">₹499.00</span>
                  </div>
                </div>
              </div>

              <div style={{ marginTop: "auto" }}>
                <button
                  type="button"
                  className={`btn-select-doctor ${!selectedProfessional ? "btn-selected" : ""}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectProfessional(null);
                  }}
                >
                  {!selectedProfessional ? "✓ Selected (Fastest Pool)" : "Select Any Doctor"}
                </button>
              </div>
            </div>
          )}

          {/* List of Verified Doctors */}
          {professionals.map((doctor) => {
            const isSelected = selectedProfessional?.id === doctor.id;
            return (
              <div
                key={doctor.id}
                className={`doctor-card ${isSelected ? "is-selected" : ""}`}
                onClick={() => onSelectProfessional(doctor)}
              >
                <div className="doctor-card-header">
                  <div className="doctor-avatar-circle">
                    <Stethoscope size={20} />
                  </div>
                  <div style={{ display: "flex", flexDirection: "column" }}>
                    <div className="doctor-name-row">
                      <h4 className="doctor-name">{doctor.full_name || doctor.name || "Doctor"}</h4>
                      <span className="badge-verified-pro">
                        <CheckCircle2 size={10} />
                        <span>Verified</span>
                      </span>
                    </div>
                    {doctor.qualification && (
                      <p className="doctor-qualification">{doctor.qualification}</p>
                    )}
                  </div>
                </div>

                <div className="doctor-card-body">
                  <div className="doctor-details-block">
                    <div className="detail-row">
                      <span>Specialization:</span>
                      <strong>{doctor.specialization || doctor.specialty || "Radiology"}</strong>
                    </div>

                    {doctor.hospital_or_clinic && (
                      <div className="detail-row">
                        <span>Affiliation:</span>
                        <span>{doctor.hospital_or_clinic}</span>
                      </div>
                    )}

                    {(doctor.city || doctor.state) && (
                      <div className="detail-row">
                        <span>Location:</span>
                        <span>{[doctor.city, doctor.state].filter(Boolean).join(", ")}</span>
                      </div>
                    )}
                  </div>

                  <div className="doctor-meta-grid">
                    <div className="meta-item">
                      <span className="meta-label">Status</span>
                      <span style={{ color: "var(--color-success)", fontWeight: "600" }}>Active & Verified</span>
                    </div>
                    <div className="meta-item">
                      <span className="meta-label">Review Fee</span>
                      <span className="meta-val fee">
                        {doctor.consultation_fee ? `₹${Number(doctor.consultation_fee).toFixed(2)}` : "₹499.00"}
                      </span>
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: "auto" }}>
                  <button
                    type="button"
                    className={`btn-select-doctor ${isSelected ? "btn-selected" : ""}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectProfessional(doctor);
                    }}
                  >
                    {isSelected ? "✓ Selected Specialist" : "Select Doctor"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* CONTINUATION BUTTON */}
      {onContinue && (
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "10px" }}>
          <button
            type="button"
            className="btn-primary"
            onClick={onContinue}
          >
            <span>{actionLabel}</span>
            <ArrowRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
