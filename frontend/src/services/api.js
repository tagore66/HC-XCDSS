const rawApiUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_BASE_URL = String(rawApiUrl).trim().replace(/\/+$/, "");


const AUTH_TOKEN_KEY = "hc_xcdss_auth_token";

/**
 * Store JWT auth token in localStorage.
 */
export function setAuthToken(token) {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

/**
 * Retrieve current JWT auth token.
 */
export function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

/**
 * Helper to generate request headers with auth token and ngrok interstitial bypass.
 */
function getAuthHeaders(extraHeaders = {}) {
  const token = getAuthToken();
  const headers = { ...extraHeaders };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  // Bypass ngrok free tier browser warning interstitial for API requests
  headers["ngrok-skip-browser-warning"] = "true";
  return headers;
}

/**
 * Robust extraction of backend error detail into human-readable string.
 */
export function formatApiErrorMessage(err, fallback = "An error occurred") {
  if (!err) return fallback;
  if (typeof err === "string") return err;
  if (typeof err.detail === "string") return err.detail;
  if (Array.isArray(err.detail)) {
    return err.detail.map((e) => e.msg || e.message || JSON.stringify(e)).join("; ");
  }
  if (err.detail && typeof err.detail === "object") {
    return err.detail.msg || err.detail.message || JSON.stringify(err.detail);
  }
  if (err.message && typeof err.message === "string") return err.message;
  return fallback;
}

// --------------------------------------------------
// Auth & Profile APIs
// --------------------------------------------------

export async function loginUser(email, password) {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    let message = "Login failed";
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  const data = await response.json();
  if (data.access_token) {
    setAuthToken(data.access_token);
  }
  return data;
}

export async function registerUser(payload) {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = "Registration failed";
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getAuthUserMe() {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = "Unable to fetch authenticated user";
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getMyProfile() {
  const response = await fetch(`${API_BASE_URL}/api/profile`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = "Unable to load profile";
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export function logoutUser() {
  setAuthToken(null);
}

// --------------------------------------------------
// Analysis & History APIs
// --------------------------------------------------

export async function analyzeXray(file, view) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("view", view);

  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData,
  });

  if (!response.ok) {
    let message = `Analysis failed: ${response.status}`;
    let isValidationError = false;
    let reason = null;

    try {
      const errorData = await response.json();
      if (errorData.detail) {
        if (typeof errorData.detail === "object") {
          message = errorData.detail.message || errorData.detail.error || message;
          reason = errorData.detail.reason || null;
          isValidationError = errorData.detail.error === "INVALID_XRAY";
        } else {
          message = errorData.detail;
        }
      }
    } catch { /* ignore parse error */ }

    const err = new Error(message);
    err.isValidationError = isValidationError;
    err.reason = reason;
    throw err;
  }

  return await response.json();
}

export async function getPatientDashboard() {
  const response = await fetch(`${API_BASE_URL}/api/patient/dashboard`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Unable to load patient dashboard: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getAnalyses() {
  const response = await fetch(`${API_BASE_URL}/api/analyses`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Unable to load history: ${response.status}`);
  }

  return await response.json();
}

export async function getAnalysis(id) {
  const response = await fetch(`${API_BASE_URL}/api/analyses/${id}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Unable to load analysis: ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) message = errorData.detail;
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function deleteAnalysis(id) {
  const response = await fetch(`${API_BASE_URL}/api/analyses/${id}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Unable to delete analysis: ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) message = errorData.detail;
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

// --------------------------------------------------
// Doctor Directory & Review Workflow APIs (Patient & Professional)
// --------------------------------------------------

export async function getProfessionalsDirectory(params = {}) {
  const query = new URLSearchParams();
  if (params.city) query.append("city", params.city);
  if (params.region) query.append("region", params.region);
  if (params.specialty) query.append("specialty", params.specialty);
  if (params.specialization) query.append("specialization", params.specialization);

  const url = `${API_BASE_URL}/api/professionals/directory${query.toString() ? "?" + query.toString() : ""}`;
  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Failed to load doctor directory: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function searchProfessionals(params = {}) {
  const query = new URLSearchParams();
  if (params.specialty) query.append("specialty", params.specialty);
  if (params.city) query.append("city", params.city);
  if (params.state) query.append("state", params.state);
  if (params.country) query.append("country", params.country);

  const url = `${API_BASE_URL}/api/professionals/search${query.toString() ? "?" + query.toString() : ""}`;
  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Search failed: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function createReview(payload) {
  const response = await fetch(`${API_BASE_URL}/api/reviews`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = `Failed to create review request: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getMyReviews() {
  const response = await fetch(`${API_BASE_URL}/api/reviews/my`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Unable to load reviews: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getReview(reviewId) {
  const response = await fetch(`${API_BASE_URL}/api/reviews/${reviewId}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Unable to load review details: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getPatientProfessionalReview(reviewId) {
  const response = await fetch(`${API_BASE_URL}/api/patient/review-requests/${reviewId}/professional-review`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = "Unable to load professional review";
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function downloadProfessionalReviewReport(reviewId) {
  const response = await fetch(`${API_BASE_URL}/api/patient/review-requests/${reviewId}/report/download`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = "Unable to download professional review report";
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.style.display = "none";
  a.href = url;
  a.download = `HC-XCDSS-Professional-Review-${reviewId.substring(0, 8)}.html`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
  return true;
}

export async function createReviewRequest(analysisId, payload = {}) {
  const response = await fetch(`${API_BASE_URL}/api/analyses/${analysisId}/review-request`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = "Failed to request review";
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getMyReviewRequests() {
  return await getMyReviews();
}

export async function getAnalysisReview(analysisId) {
  const response = await fetch(`${API_BASE_URL}/api/analyses/${analysisId}/review`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = "Unable to load analysis review";
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function cancelReview(reviewId) {
  const response = await fetch(`${API_BASE_URL}/api/reviews/${reviewId}/cancel`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Cancellation failed: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function cancelReviewRequest(reviewId) {
  return await cancelReview(reviewId);
}

export async function getProfessionalReviews(filter = "all") {
  const response = await fetch(`${API_BASE_URL}/api/professional/review-requests?filter=${filter}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Unable to load professional reviews: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getProfessionalReviewRequests(filter = "all") {
  return await getProfessionalReviews(filter);
}

export async function getProfessionalCaseWorkspace(reviewId) {
  const response = await fetch(`${API_BASE_URL}/api/professional/review-requests/${reviewId}/case`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Failed to load case workspace: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return await response.json();
}

export async function acceptReview(reviewId) {
  const response = await fetch(`${API_BASE_URL}/api/professional/review-requests/${reviewId}/accept`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Accept failed: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function acceptReviewRequest(reviewId) {
  return await acceptReview(reviewId);
}

export async function startReview(reviewId) {
  const response = await fetch(`${API_BASE_URL}/api/professional/review-requests/${reviewId}/start`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Start failed: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function startProfessionalReview(reviewId) {
  return await startReview(reviewId);
}

export async function getProfessionalAssessment(reviewId) {
  const response = await fetch(`${API_BASE_URL}/api/professional/review-requests/${reviewId}/assessment`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Failed to get assessment: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return await response.json();
}

export async function saveProfessionalAssessmentDraft(reviewId, payload) {
  const response = await fetch(`${API_BASE_URL}/api/professional/review-requests/${reviewId}/assessment/draft`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = `Failed to save draft: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return await response.json();
}

export async function submitProfessionalAssessment(reviewId, payload) {
  const response = await fetch(`${API_BASE_URL}/api/professional/review-requests/${reviewId}/assessment/submit`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = `Failed to submit review: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return await response.json();
}

export async function completeReview(reviewId, payload) {
  return await submitProfessionalAssessment(reviewId, payload);
}

export async function submitProfessionalReview(reviewId, payload) {
  return await submitProfessionalAssessment(reviewId, payload);
}

export async function declineReview(reviewId) {
  const response = await fetch(`${API_BASE_URL}/api/professional/review-requests/${reviewId}/decline`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Decline failed: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function declineReviewRequest(reviewId) {
  return await declineReview(reviewId);
}

// --------------------------------------------------
// AI Assistant API
// --------------------------------------------------

/**
 * Send a question about a specific analysis to the Context-Aware AI Assistant.
 * @param {string} analysisId - Unique 12-char analysis ID
 * @param {string} message - User query text
 * @param {string} role - Audience role: 'patient' or 'professional'
 * @param {Array} conversationHistory - Optional list of previous chat turns
 * @returns {Promise<Object>} Assistant response object
 */
export async function askAssistant(analysisId, message, role = "patient", conversationHistory = []) {
  const response = await fetch(`${API_BASE_URL}/api/assistant/${analysisId}`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      message,
      role,
      conversation_history: conversationHistory,
    }),
  });

  if (!response.ok) {
    let errMessage = `Assistant request failed: ${response.status}`;
    try {
      const err = await response.json();
      if (err.detail) errMessage = err.detail;
    } catch { /* ignore parse error */ }
    throw new Error(errMessage);
  }

  return await response.json();
}

// --------------------------------------------------
// Utilities
// --------------------------------------------------

export function getHeatmapUrl(path) {
  if (!path) {
    return null;
  }

  const normalizedPath = String(path).replaceAll("\\", "/");

  let url;
  if (
    normalizedPath.startsWith("http://") ||
    normalizedPath.startsWith("https://")
  ) {
    url = normalizedPath;
  } else if (normalizedPath.startsWith("/")) {
    url = API_BASE_URL + normalizedPath;
  } else {
    const outputsIndex = normalizedPath.toLowerCase().indexOf("/outputs/");
    if (outputsIndex !== -1) {
      url = API_BASE_URL + normalizedPath.substring(outputsIndex);
    } else {
      url = API_BASE_URL + "/" + normalizedPath;
    }
  }

  const token = getAuthToken();
  if (token && !url.includes("token=")) {
    const separator = url.includes("?") ? "&" : "?";
    url = `${url}${separator}token=${encodeURIComponent(token)}`;
  }

  return url;
}

export { API_BASE_URL };


// --------------------------------------------------
// In-App Notifications & Activity Center APIs (Milestone 12)
// --------------------------------------------------

export async function getNotifications(limit = 20, offset = 0) {
  const response = await fetch(`${API_BASE_URL}/api/notifications?limit=${limit}&offset=${offset}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Failed to load notifications: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getUnreadCount() {
  const response = await fetch(`${API_BASE_URL}/api/notifications/unread-count`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    return { count: 0 };
  }

  return await response.json();
}

export async function markNotificationRead(notificationId) {
  const response = await fetch(`${API_BASE_URL}/api/notifications/${notificationId}/read`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Failed to mark notification read: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function markAllNotificationsRead() {
  const response = await fetch(`${API_BASE_URL}/api/notifications/read-all`, {
    method: "POST",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Failed to mark all read: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function deleteNotification(notificationId) {
  const response = await fetch(`${API_BASE_URL}/api/notifications/${notificationId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Failed to delete notification: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}


// --------------------------------------------------
// Payments & Checkout APIs (Milestone 13)
// --------------------------------------------------

export async function getPaymentCatalog() {
  const response = await fetch(`${API_BASE_URL}/api/payments/catalog`);
  if (!response.ok) {
    return { services: [] };
  }
  return await response.json();
}

export async function createPaymentCheckout(reviewRequestId, serviceId = "XRAY_PROFESSIONAL_REVIEW") {
  const response = await fetch(`${API_BASE_URL}/api/payments/checkout`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      review_request_id: reviewRequestId,
      service_id: serviceId,
    }),
  });

  if (!response.ok) {
    let message = `Checkout initiation failed: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getPaymentStatus(paymentId) {
  const response = await fetch(`${API_BASE_URL}/api/payments/${paymentId}/status`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Failed to get payment status: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function verifyPaymentSession(sessionId) {
  const response = await fetch(`${API_BASE_URL}/api/payments/verify-session`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ session_id: sessionId }),
  });

  if (!response.ok) {
    let message = `Payment verification failed: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function simulatePaymentWebhook(paymentId, action = "success") {
  const response = await fetch(`${API_BASE_URL}/api/payments/webhook/mock`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      payment_id: paymentId,
      action: action,
    }),
  });

  if (!response.ok) {
    let message = `Payment processing simulation failed: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getProfessionalEarnings() {
  const response = await fetch(`${API_BASE_URL}/api/professional/earnings`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Failed to load physician earnings: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

// --------------------------------------------------
// Professional Registration & Admin Verification APIs (Milestone 1)
// --------------------------------------------------

export async function registerProfessional(formData) {
  const response = await fetch(`${API_BASE_URL}/api/auth/register-professional`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let message = "Professional registration failed";
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getAdminVerificationRequests(status = "ALL") {
  const url = status && status !== "ALL"
    ? `${API_BASE_URL}/api/admin/professionals/verification-requests?status=${encodeURIComponent(status)}`
    : `${API_BASE_URL}/api/admin/professionals/verification-requests`;

  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Failed to load verification requests: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function getAdminProfessionalDetails(userId) {
  const response = await fetch(`${API_BASE_URL}/api/admin/professionals/${userId}/verification-details`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = `Failed to load professional details: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function approveProfessionalVerification(userId) {
  const response = await fetch(`${API_BASE_URL}/api/admin/professionals/${userId}/approve`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
  });

  if (!response.ok) {
    let message = `Approval failed: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function rejectProfessionalVerification(userId, reason) {
  const response = await fetch(`${API_BASE_URL}/api/admin/professionals/${userId}/reject`, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ reason }),
  });

  if (!response.ok) {
    let message = `Rejection failed: ${response.status}`;
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  return await response.json();
}

export async function fetchDocumentBlobUrl(userId, docType) {
  const response = await fetch(`${API_BASE_URL}/api/admin/professionals/${userId}/documents/${docType}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    let message = "Failed to load verification document";
    try {
      const err = await response.json();
      message = formatApiErrorMessage(err, message);
    } catch { /* ignore parse error */ }
    throw new Error(message);
  }

  const blob = await response.blob();
  return URL.createObjectURL(blob);
}

