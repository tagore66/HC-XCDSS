import { useState } from "react";
import {
  UploadCloud,
  ScanLine,
  Activity,
  CheckCircle2,
  AlertTriangle,
  FileImage,
  ArrowRight,
  Shield,
  X,
} from "lucide-react";

const VIEWS = [
  {
    value: "Frontal",
    label: "Frontal View",
    description: "AP / PA thoracic projection",
  },
  {
    value: "Lateral",
    label: "Lateral View",
    description: "Sagittal thoracic projection",
  },
];

export default function UploadScreen({
  file,
  preview,
  view,
  setView,
  onFileChange,
  onAnalyze,
  loading,
  error,
}) {
  const [dragOver, setDragOver] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const syntheticEvent = { target: { files: e.dataTransfer.files } };
      onFileChange(syntheticEvent);
    }
  };

  const fileSizeFormatted = file
    ? `${(file.size / (1024 * 1024)).toFixed(2)} MB`
    : "";

  return (
    <section className="upload-section">
      <div className="upload-card">
        <div className="upload-icon-wrap">
          <ScanLine size={24} />
        </div>

        <div className="eyebrow" style={{ justifyContent: "center" }}>
          <Activity size={12} />
          <span>CHEST RADIOGRAPH INGESTION</span>
        </div>

        <h2>Upload Chest X-Ray</h2>

        <p className="upload-description">
          Select thoracic projection and upload a chest radiograph in PNG or JPEG format for AI inference and explainability.
        </p>

        {/* VIEW SELECTION */}
        <div className="view-selector">
          <div className="field-label">Projection View</div>

          <div className="view-options">
            {VIEWS.map((option) => (
              <button
                type="button"
                key={option.value}
                className={
                  view === option.value
                    ? "view-option selected"
                    : "view-option"
                }
                onClick={() => setView(option.value)}
                disabled={loading}
              >
                <span className="view-radio">
                  {view === option.value && <span />}
                </span>

                <span className="view-option-content">
                  <strong>{option.label}</strong>
                  <small>{option.description}</small>
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* DIAGNOSTIC DROP ZONE */}
        {!file && (
          <label
            className={`diagnostic-drop-zone ${dragOver ? "drag-over" : ""}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              type="file"
              accept=".jpg,.jpeg,.png,image/jpeg,image/png"
              onChange={onFileChange}
              style={{ display: "none" }}
              disabled={loading}
            />
            <div className="drop-zone-icon">
              <UploadCloud size={32} />
            </div>
            <div className="drop-zone-text">
              <strong>Drag & drop chest radiograph here</strong>
              <span>or click to browse files (PNG, JPEG)</span>
            </div>
          </label>
        )}

        {/* SELECTED FILE BADGE */}
        {file && (
          <div className="selected-file-badge">
            <div className="selected-file-info">
              <FileImage size={18} color="var(--accent-primary)" />
              <div>
                <span className="selected-file-name">{file.name}</span>
                <span className="selected-file-view"> • {fileSizeFormatted} • {view}</span>
              </div>
            </div>

            <label style={{ cursor: "pointer", fontSize: "12px", color: "var(--accent-primary)", fontWeight: "600" }}>
              <span>Replace</span>
              <input
                type="file"
                accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                onChange={onFileChange}
                style={{ display: "none" }}
              />
            </label>
          </div>
        )}

        {/* PREVIEW */}
        {preview && (
          <div className="preview-container">
            <div className="preview-header">
              <span>Radiograph Preview</span>
              <span className="status-tag">
                {view} Projection
              </span>
            </div>

            <img
              src={preview}
              alt="Selected chest X-ray"
              className="xray-preview"
            />
          </div>
        )}

        {/* ANALYZE BUTTON */}
        <button
          className="analyze-button"
          onClick={onAnalyze}
          disabled={!file || loading}
        >
          {loading ? (
            <>
              <span className="spinner" />
              <span>Running DenseNet121 Analysis...</span>
            </>
          ) : (
            <>
              <span>Analyze X-Ray</span>
              <ArrowRight size={15} />
            </>
          )}
        </button>

        {/* VALIDATION OR REJECTION STATE (INLINE DIAGNOSTIC WARNING) */}
        {error && (
          <div className="validation-error-card" role="alert">
            <div className="val-error-header">
              <AlertTriangle size={16} />
              <strong>That image doesn't appear to be a chest radiograph</strong>
            </div>
            <p className="val-error-desc">
              {typeof error === "string" && (error.includes("does not appear") || error.includes("lacks") || error.includes("out-of-domain"))
                ? error
                : "Please upload a clear frontal or lateral chest X-ray in PNG or JPEG format."}
            </p>
            <label className="btn-choose-another">
              <span>Choose Another Image</span>
              <input
                type="file"
                accept=".jpg,.jpeg,.png,image/jpeg,image/png"
                onChange={onFileChange}
                style={{ display: "none" }}
              />
            </label>
          </div>
        )}

        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "6px",
          marginTop: "18px",
          fontSize: "11px",
          color: "var(--text-muted)",
        }}>
          <Shield size={13} color="var(--accent-primary)" />
          <span>Validated with local radiometric texture analysis & lightweight OOD filter.</span>
        </div>
      </div>
    </section>
  );
}
