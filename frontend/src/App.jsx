import { useEffect, useState } from "react";
import "./App.css";
import Header from "./components/Header";
import PatientDashboard from "./components/PatientDashboard";
import UploadScreen from "./components/UploadScreen";
import HistoryScreen from "./components/HistoryScreen";
import ResultsScreen from "./components/ResultsScreen";
import PatientReviewsScreen from "./components/PatientReviewsScreen";
import ReviewDetailScreen from "./components/ReviewDetailScreen";
import ProfessionalDashboard from "./components/ProfessionalDashboard";
import ProfessionalCaseWorkspace from "./components/ProfessionalCaseWorkspace";
import PendingVerificationScreen from "./components/PendingVerificationScreen";
import AdminVerificationQueue from "./components/AdminVerificationQueue";
import AuthModal from "./components/AuthModal";
import GuestLanding from "./components/GuestLanding";
import PaymentSuccessModal from "./components/PaymentSuccessModal";
import {
  analyzeXray as apiAnalyzeXray,
  getAnalyses as apiGetAnalyses,
  getAnalysis as apiGetAnalysis,
  getMyReviews as apiGetMyReviews,
  getReview as apiGetReview,
  getProfessionalReviews as apiGetProfessionalReviews,
  getMyProfile as apiGetMyProfile,
  verifyPaymentSession as apiVerifyPaymentSession,
  logoutUser as apiLogoutUser,
  getAuthToken,
} from "./services/api";

const STORAGE_KEYS = {
  screen: "hc_xcdss_screen",
  analysisId: "hc_xcdss_active_analysis_id",
  reviewId: "hc_xcdss_active_review_id",
  userId: "hc_xcdss_session_user_id",
  userRole: "hc_xcdss_session_user_role",
};

function App() {
  const [activeScreen, setActiveScreen] = useState(() => {
    const token = getAuthToken();
    if (!token) return "landing";
    return localStorage.getItem(STORAGE_KEYS.screen) || "dashboard";
  });
  
  // Current user & profile state
  const [currentUser, setCurrentUser] = useState(null);

  // Analysis / Upload state
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [view, setView] = useState("Frontal");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  // History state
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");

  // Patient Reviews state
  const [patientReviews, setPatientReviews] = useState([]);
  const [reviewsLoading, setReviewsLoading] = useState(false);
  const [reviewsError, setReviewsError] = useState("");

  // Single Review Detail state
  const [activeReviewId, setActiveReviewId] = useState(null);
  const [reviewDetailData, setReviewDetailData] = useState(null);
  const [reviewDetailLoading, setReviewDetailLoading] = useState(false);
  const [reviewDetailError, setReviewDetailError] = useState("");

  // Professional Portal state
  const [proReviews, setProReviews] = useState([]);
  const [proReviewsLoading, setProReviewsLoading] = useState(false);
  const [proReviewsError, setProReviewsError] = useState("");

  // Auth Modal Config
  const [authModalConfig, setAuthModalConfig] = useState({
    isOpen: false,
    mode: "login",
    role: "PATIENT",
  });

  // Auth checking state on application boot (true only if token is present in storage to verify)
  const [authChecking, setAuthChecking] = useState(() => {
    return !!getAuthToken();
  });

  // Payment Success / Notice Modal & Banner state
  const [paymentSuccessModalConfig, setPaymentSuccessModalConfig] = useState({
    isOpen: false,
    payment: null,
    review: null,
  });
  const [paymentNotice, setPaymentNotice] = useState(null);

  // History stack for seamless SPA back navigation
  const [historyStack, setHistoryStack] = useState([]);

  // --------------------------------------------------
  // Cleanup preview URL on unmount or file replace
  // --------------------------------------------------
  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);

  // --------------------------------------------------
  // Initial profile & screen restoration (Strict Auth Gate)
  // --------------------------------------------------
  useEffect(() => {
    bootstrapSession();
  }, []);

  async function bootstrapSession() {
    const token = getAuthToken();

    // 1. If no token in storage, immediately establish unauthenticated guest state
    if (!token) {
      handleUnauthenticatedState();
      setAuthChecking(false);
      return;
    }

    setAuthChecking(true);

    // 2. If token exists, verify with backend profile endpoint
    try {
      const data = await apiGetMyProfile();
      if (data?.user) {
        const userObj = {
          ...data.user,
          patient_profile: data.patient_profile,
          professional_profile: data.professional_profile,
        };
        setCurrentUser(userObj);

        // 1. Immediately record authenticated user session to localStorage
        const storedUserId = localStorage.getItem(STORAGE_KEYS.userId);
        const storedUserRole = localStorage.getItem(STORAGE_KEYS.userRole);
        const isSameUserSession = storedUserId === userObj.id && storedUserRole === userObj.role;

        localStorage.setItem(STORAGE_KEYS.userId, userObj.id);
        localStorage.setItem(STORAGE_KEYS.userRole, userObj.role);

        if (!isSameUserSession) {
          localStorage.removeItem(STORAGE_KEYS.analysisId);
          localStorage.removeItem(STORAGE_KEYS.reviewId);
          setHistoryStack([]);
        }

        // Role-based routing and verification check
        const isProVerified = userObj.role === "PROFESSIONAL" && userObj.professional_profile?.verification_status === "VERIFIED";
        const isProUnverified = userObj.role === "PROFESSIONAL" && !isProVerified;
        const isAdmin = userObj.role === "ADMIN";
        const isPatient = userObj.role === "PATIENT";

        const defaultScreen = isAdmin ? "admin-verification" : isProUnverified ? "pro-pending" : isProVerified ? "pro-dashboard" : "dashboard";

        if (isProUnverified) {
          navigateTo("pro-pending", { replace: true });
          return;
        }

        // 2. Check for Stripe return parameters in URL
        const urlParams = new URLSearchParams(window.location.search);
        const sessionId = urlParams.get("session_id");
        const paymentStatus = urlParams.get("payment_status");

        if (paymentStatus === "cancelled") {
          window.history.replaceState({}, document.title, window.location.pathname);
          setPaymentNotice({
            type: "info",
            message: "Stripe checkout was cancelled. No charges were made to your account.",
          });
          navigateTo("reviews");
          return;
        }

        if (sessionId || paymentStatus === "success") {
          window.history.replaceState({}, document.title, window.location.pathname);
          if (sessionId) {
            try {
              const verifyRes = await apiVerifyPaymentSession(sessionId);
              if (verifyRes?.success && verifyRes?.status === "PAID") {
                setPaymentSuccessModalConfig({
                  isOpen: true,
                  payment: verifyRes.payment,
                  review: verifyRes.review_request,
                });
                await loadPatientReviews();
                if (verifyRes.review_request?.id) {
                  openReviewDetail(verifyRes.review_request.id);
                  return;
                }
              } else {
                setPaymentNotice({
                  type: "info",
                  message: `Payment status: ${verifyRes?.status || "Processing"}. Your review will update shortly.`,
                });
              }
            } catch (verErr) {
              console.error("Payment session verification error:", verErr);
              setPaymentNotice({
                type: "error",
                message: `Unable to verify payment session: ${verErr.message || "Please refresh or contact support."}`,
              });
            }
          }
        }

        // 3. If user account or role changed, immediately route to the authorized default dashboard and reset stale state
        if (!isSameUserSession) {
          navigateTo(defaultScreen, { replace: true });
          return;
        }

        // 4. Restore saved screen ONLY if valid for this authenticated role within the same session
        const savedScreen = localStorage.getItem(STORAGE_KEYS.screen) || defaultScreen;
        const savedAnalysisId = localStorage.getItem(STORAGE_KEYS.analysisId);
        const savedReviewId = localStorage.getItem(STORAGE_KEYS.reviewId);

        if (isPatient) {
          if (savedReviewId && savedScreen === "review-detail") {
            openReviewDetail(savedReviewId, { replace: true });
          } else if (savedAnalysisId && savedScreen === "result") {
            openHistoricalAnalysis(savedAnalysisId, { replace: true });
          } else if (["history", "reviews", "upload", "dashboard"].includes(savedScreen)) {
            navigateTo(savedScreen, { replace: true });
          } else {
            navigateTo("dashboard", { replace: true });
          }
        } else if (isProVerified) {
          if (savedReviewId && savedScreen === "pro-review") {
            openProfessionalReview(savedReviewId, { replace: true });
          } else if (savedScreen === "pro-dashboard") {
            navigateTo("pro-dashboard", { replace: true });
          } else {
            navigateTo("pro-dashboard", { replace: true });
          }
        } else if (isAdmin) {
          navigateTo("admin-verification", { replace: true });
        } else {
          navigateTo(defaultScreen, { replace: true });
        }
      } else {
        handleUnauthenticatedState();
      }
    } catch {
      // 401 or invalid token
      handleUnauthenticatedState();
    } finally {
      setAuthChecking(false);
    }
  };

  const handleUnauthenticatedState = () => {
    apiLogoutUser();
    setCurrentUser(null);
    localStorage.removeItem(STORAGE_KEYS.screen);
    localStorage.removeItem(STORAGE_KEYS.analysisId);
    localStorage.removeItem(STORAGE_KEYS.reviewId);
    localStorage.removeItem(STORAGE_KEYS.userId);
    localStorage.removeItem(STORAGE_KEYS.userRole);
    setHistoryStack([]);
    setActiveScreen("landing");
    setResult(null);
    setFile(null);
    setPreview(null);
    setActiveReviewId(null);
    setReviewDetailData(null);
  };

  // --------------------------------------------------
  // Navigation Handlers (Stack-Based Seamless SPA)
  // --------------------------------------------------
  const navigateTo = (screenName, options = {}) => {
    const { replace = false, fromBack = false } = options;
    if (!fromBack && !replace && activeScreen && activeScreen !== screenName) {
      setHistoryStack((prev) => [
        ...prev,
        {
          screen: activeScreen,
          reviewId: activeReviewId,
          analysisId: result?.analysis_id,
        },
      ]);
    }

    setActiveScreen(screenName);
    localStorage.setItem(STORAGE_KEYS.screen, screenName);
    setError("");

    if (screenName === "dashboard" || screenName === "upload") {
      localStorage.removeItem(STORAGE_KEYS.analysisId);
      localStorage.removeItem(STORAGE_KEYS.reviewId);
      if (screenName === "upload" && !options.keepResult) {
        setResult(null);
      }
    } else if (screenName === "history") {
      localStorage.removeItem(STORAGE_KEYS.analysisId);
      localStorage.removeItem(STORAGE_KEYS.reviewId);
      loadHistory();
    } else if (screenName === "reviews") {
      localStorage.removeItem(STORAGE_KEYS.analysisId);
      localStorage.removeItem(STORAGE_KEYS.reviewId);
      loadPatientReviews();
    } else if (screenName === "pro-dashboard") {
      localStorage.removeItem(STORAGE_KEYS.analysisId);
      localStorage.removeItem(STORAGE_KEYS.reviewId);
      loadProfessionalReviews();
    }
  };

  const navigateBack = () => {
    if (historyStack.length > 0) {
      const prev = historyStack[historyStack.length - 1];
      setHistoryStack((old) => old.slice(0, old.length - 1));

      if (prev.screen === "review-detail" && prev.reviewId) {
        openReviewDetail(prev.reviewId, { fromBack: true });
      } else if (prev.screen === "result" && prev.analysisId) {
        openHistoricalAnalysis(prev.analysisId, { fromBack: true });
      } else if (prev.screen === "pro-review" && prev.reviewId) {
        openProfessionalReview(prev.reviewId, { fromBack: true });
      } else {
        navigateTo(prev.screen, { replace: true, fromBack: true });
      }
    } else {
      // Safe fallback based on authenticated role
      if (currentUser?.role === "ADMIN") {
        navigateTo("admin-verification", { replace: true });
      } else if (currentUser?.role === "PROFESSIONAL") {
        const isVerified = currentUser.professional_profile?.verification_status === "VERIFIED";
        navigateTo(isVerified ? "pro-dashboard" : "pro-pending", { replace: true });
      } else if (currentUser?.role === "PATIENT") {
        navigateTo("dashboard", { replace: true });
      } else {
        navigateTo("landing", { replace: true });
      }
    }
  };

  // --------------------------------------------------
  // Load analysis history
  // --------------------------------------------------
  const loadHistory = async () => {
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const data = await apiGetAnalyses();
      setHistory(data.analyses || []);
    } catch (err) {
      console.error("History error:", err);
      setHistoryError(err.message || "Unable to load analysis history.");
    } finally {
      setHistoryLoading(false);
    }
  };

  // --------------------------------------------------
  // Load patient reviews
  // --------------------------------------------------
  const loadPatientReviews = async () => {
    setReviewsLoading(true);
    setReviewsError("");
    try {
      const data = await apiGetMyReviews();
      setPatientReviews(data || []);
    } catch (err) {
      console.error("Patient reviews error:", err);
      setReviewsError(err.message || "Unable to load your clinical reviews.");
    } finally {
      setReviewsLoading(false);
    }
  };

  // --------------------------------------------------
  // Load professional reviews
  // --------------------------------------------------
  const loadProfessionalReviews = async () => {
    setProReviewsLoading(true);
    setProReviewsError("");
    try {
      const data = await apiGetProfessionalReviews();
      setProReviews(data || []);
    } catch (err) {
      console.error("Professional reviews error:", err);
      setProReviewsError(err.message || "Unable to load professional review queue.");
    } finally {
      setProReviewsLoading(false);
    }
  };

  // --------------------------------------------------
  // Open historical analysis
  // --------------------------------------------------
  const openHistoricalAnalysis = async (analysisId, options = {}) => {
    if (!options.fromBack && !options.replace && activeScreen !== "result") {
      setHistoryStack((prev) => [
        ...prev,
        { screen: activeScreen, reviewId: activeReviewId, analysisId: result?.analysis_id },
      ]);
    }
    setLoading(true);
    setError("");
    try {
      const data = await apiGetAnalysis(analysisId);
      setResult(data);
      setFile(null);
      setPreview(null);
      setView(data.view || "Frontal");
      setActiveScreen("result");
      localStorage.setItem(STORAGE_KEYS.screen, "result");
      localStorage.setItem(STORAGE_KEYS.analysisId, data.analysis_id);
    } catch (err) {
      console.error("Historical analysis error:", err);
      setError(err.message || "Unable to load this analysis.");
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------
  // Open review detail
  // --------------------------------------------------
  const openReviewDetail = async (reviewId, options = {}) => {
    if (!options.fromBack && !options.replace && activeScreen !== "review-detail") {
      setHistoryStack((prev) => [
        ...prev,
        { screen: activeScreen, reviewId: activeReviewId, analysisId: result?.analysis_id },
      ]);
    }
    setActiveReviewId(reviewId);
    setActiveScreen("review-detail");
    localStorage.setItem(STORAGE_KEYS.screen, "review-detail");
    localStorage.setItem(STORAGE_KEYS.reviewId, reviewId);
    setReviewDetailLoading(true);
    setReviewDetailError("");

    try {
      const data = await apiGetReview(reviewId);
      setReviewDetailData(data);
    } catch (err) {
      console.error("Review detail error:", err);
      setReviewDetailError(err.message || "Failed to load review details.");
    } finally {
      setReviewDetailLoading(false);
    }
  };

  // --------------------------------------------------
  // Notification Navigation Handler (Safe Deep-Link Router)
  // --------------------------------------------------
  const handleNavigateToEntity = (entityType, entityId) => {
    if (!entityType || !entityId || typeof entityId !== "string" || !entityId.trim()) {
      return;
    }

    const cleanId = entityId.trim();

    if (entityType === "ANALYSIS") {
      if (currentUser?.role === "PATIENT") {
        openHistoricalAnalysis(cleanId);
      }
    } else if (entityType === "REVIEW_REQUEST" || entityType === "PROFESSIONAL_REVIEW") {
      if (currentUser?.role === "PROFESSIONAL") {
        openProfessionalReview(cleanId);
      } else if (currentUser?.role === "PATIENT") {
        openReviewDetail(cleanId);
      }
    } else if (entityType === "PAYMENT") {
      if (currentUser?.role === "PATIENT") {
        navigateTo("reviews");
      }
    }
  };

  // --------------------------------------------------
  // Open professional review screen
  // --------------------------------------------------
  const openProfessionalReview = (reviewId, options = {}) => {
    if (!options.fromBack && !options.replace && activeScreen !== "pro-review") {
      setHistoryStack((prev) => [
        ...prev,
        { screen: activeScreen, reviewId: activeReviewId, analysisId: result?.analysis_id },
      ]);
    }
    setActiveReviewId(reviewId);
    setActiveScreen("pro-review");
    localStorage.setItem(STORAGE_KEYS.screen, "pro-review");
    localStorage.setItem(STORAGE_KEYS.reviewId, reviewId);
  };

  // --------------------------------------------------
  // File selection
  // --------------------------------------------------
  const handleFileChange = (event) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    const filename = selectedFile.name.toLowerCase();
    if (filename.includes("lateral")) {
      setView("Lateral");
    } else if (filename.includes("frontal")) {
      setView("Frontal");
    }

    const allowedTypes = ["image/jpeg", "image/jpg", "image/png"];
    if (!allowedTypes.includes(selectedFile.type)) {
      setError("Please select a JPG or PNG chest X-ray image.");
      return;
    }

    if (preview) {
      URL.revokeObjectURL(preview);
    }

    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
    setResult(null);
    setError("");
  };

  // --------------------------------------------------
  // Analyze X-ray
  // --------------------------------------------------
  const analyzeXray = async () => {
    if (!file) {
      setError("Please select an X-ray image first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const data = await apiAnalyzeXray(file, view);
      setResult(data);
      setActiveScreen("result");
      localStorage.setItem(STORAGE_KEYS.screen, "result");
      if (data.analysis_id) {
        localStorage.setItem(STORAGE_KEYS.analysisId, data.analysis_id);
      }
    } catch (err) {
      console.error("Analysis error:", err);
      setError(err.message || "Unable to connect to the HC-XCDSS backend.");
    } finally {
      setLoading(false);
    }
  };

  const resetAnalysis = () => {
    if (preview) {
      URL.revokeObjectURL(preview);
    }
    navigateTo("upload");
  };

  const handleLogout = () => {
    handleUnauthenticatedState();
  };

  const handleAuthSuccess = () => {
    bootstrapSession();
  };

  const handleOpenAuth = (mode = "login", role = "PATIENT") => {
    setAuthModalConfig({
      isOpen: true,
      mode: mode,
      role: role,
    });
  };

  const isGuestLanding = !currentUser && (!getAuthToken() || !authChecking);

  useEffect(() => {
    if (isGuestLanding) {
      document.documentElement.classList.add("theme-guest-landing");
      document.documentElement.classList.remove("theme-app-authenticated");
      document.body.classList.add("theme-guest-landing");
      document.body.classList.remove("theme-app-authenticated");
    } else {
      document.documentElement.classList.remove("theme-guest-landing");
      document.documentElement.classList.add("theme-app-authenticated");
      document.body.classList.remove("theme-guest-landing");
      document.body.classList.add("theme-app-authenticated");
    }
  }, [isGuestLanding]);

  if (authChecking && getAuthToken()) {
    return (
      <div className="auth-loading-screen">
        <div className="spinner"></div>
        <p>Verifying secure session...</p>
      </div>
    );
  }

  return (
    <div className={`app ${isGuestLanding ? "app-guest-mode" : "app-authenticated-mode"}`}>
      {/* HEADER (Only for authenticated sessions or non-guest screens) */}
      {!isGuestLanding && (
        <Header
          activeScreen={activeScreen}
          onNavigate={navigateTo}
          loading={loading}
          currentUser={currentUser}
          onOpenAuth={handleOpenAuth}
          onLogout={handleLogout}
          onNavigateToEntity={handleNavigateToEntity}
        />
      )}

      {/* AUTH MODAL */}
      <AuthModal
        isOpen={authModalConfig.isOpen}
        initialMode={authModalConfig.mode}
        initialRole={authModalConfig.role}
        onClose={() => setAuthModalConfig((prev) => ({ ...prev, isOpen: false }))}
        onAuthSuccess={handleAuthSuccess}
      />

      {/* PAYMENT SUCCESS CONFIRMATION MODAL */}
      <PaymentSuccessModal
        isOpen={paymentSuccessModalConfig.isOpen}
        paymentData={paymentSuccessModalConfig.payment}
        reviewData={paymentSuccessModalConfig.review}
        onClose={() => setPaymentSuccessModalConfig((prev) => ({ ...prev, isOpen: false }))}
        onViewReviewDetails={(reviewId) => {
          setPaymentSuccessModalConfig((prev) => ({ ...prev, isOpen: false }));
          openReviewDetail(reviewId);
        }}
        onViewAllReviews={() => {
          setPaymentSuccessModalConfig((prev) => ({ ...prev, isOpen: false }));
          navigateTo("reviews");
        }}
      />

      {/* MAIN CONTAINER */}
      <main className={isGuestLanding ? "guest-main-fullwidth" : "container"}>
        {/* PAYMENT NOTIFICATION BANNER */}
        {paymentNotice && (
          <div
            className={`payment-notice-banner ${paymentNotice.type === "error" ? "error-banner" : "info-banner"}`}
            style={{
              margin: "16px 0",
              padding: "12px 16px",
              borderRadius: "8px",
              background: paymentNotice.type === "error" ? "#fff5f5" : "#ebf8ff",
              border: `1px solid ${paymentNotice.type === "error" ? "#feb2b2" : "#bee3f8"}`,
              color: paymentNotice.type === "error" ? "#c53030" : "#2b6cb0",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: "13px",
              fontWeight: 500,
            }}
          >
            <span>{paymentNotice.message}</span>
            <button
              type="button"
              onClick={() => setPaymentNotice(null)}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: "18px",
                color: "inherit",
                lineHeight: 1,
              }}
              aria-label="Dismiss notice"
            >
              ×
            </button>
          </div>
        )}

        {/* GUEST LANDING SCREEN */}
        {!currentUser && (!getAuthToken() || !authChecking) && (
          <GuestLanding onOpenAuth={handleOpenAuth} currentUser={currentUser} />
        )}

        {/* PATIENT DASHBOARD (MILESTONE 4B) & SAFE FALLBACK */}
        {currentUser && currentUser.role === "PATIENT" && (
          activeScreen === "dashboard" ||
          (activeScreen === "result" && !result) ||
          !["dashboard", "upload", "result", "history", "reviews", "review-detail"].includes(activeScreen)
        ) && (
          <PatientDashboard
            currentUser={currentUser}
            onNewAnalysis={resetAnalysis}
            onOpenAnalysis={openHistoricalAnalysis}
            onOpenReviewDetail={openReviewDetail}
            onViewAllHistory={() => navigateTo("history")}
            onViewAllReviews={() => navigateTo("reviews")}
          />
        )}

        {/* UPLOAD SCREEN */}
        {currentUser && activeScreen === "upload" && (
          <UploadScreen
            file={file}
            preview={preview}
            view={view}
            setView={setView}
            onFileChange={handleFileChange}
            onAnalyze={analyzeXray}
            loading={loading}
            error={error}
          />
        )}

        {/* RESULTS SCREEN */}
        {currentUser && activeScreen === "result" && result && (
          <ResultsScreen
            result={result}
            preview={preview}
            view={view}
            onResetAnalysis={resetAnalysis}
            onBackToHistory={navigateBack}
            onOpenMyReviews={() => navigateTo("reviews")}
          />
        )}

        {/* HISTORY SCREEN */}
        {currentUser && activeScreen === "history" && (
          <HistoryScreen
            history={history}
            loading={historyLoading}
            error={historyError}
            onOpenAnalysis={openHistoricalAnalysis}
            onNewAnalysis={resetAnalysis}
          />
        )}

        {/* PATIENT REVIEWS SCREEN */}
        {currentUser && activeScreen === "reviews" && (
          <PatientReviewsScreen
            reviews={patientReviews}
            loading={reviewsLoading}
            error={reviewsError}
            onOpenReviewDetail={openReviewDetail}
            onRefreshReviews={loadPatientReviews}
            onNewAnalysis={resetAnalysis}
          />
        )}

        {/* REVIEW DETAIL SCREEN */}
        {currentUser && activeScreen === "review-detail" && (
          <ReviewDetailScreen
            reviewData={reviewDetailData}
            loading={reviewDetailLoading}
            error={reviewDetailError}
            onBack={navigateBack}
            onRefresh={() => openReviewDetail(activeReviewId, { replace: true })}
          />
        )}

        {/* PENDING / UNVERIFIED PROFESSIONAL SCREEN */}
        {currentUser && activeScreen === "pro-pending" && (
          <PendingVerificationScreen
            currentUser={currentUser}
            onRefresh={async () => {
              const data = await apiGetMyProfile();
              if (data?.user) {
                const updated = {
                  ...data.user,
                  patient_profile: data.patient_profile,
                  professional_profile: data.professional_profile,
                };
                setCurrentUser(updated);
                if (updated.professional_profile?.verification_status === "VERIFIED") {
                  navigateTo("pro-dashboard");
                }
              }
            }}
            onLogout={handleLogout}
          />
        )}

        {/* ADMIN VERIFICATION QUEUE */}
        {currentUser && currentUser.role === "ADMIN" && activeScreen === "admin-verification" && (
          <AdminVerificationQueue onNavigate={navigateTo} />
        )}

        {/* PROFESSIONAL DASHBOARD & SAFE FALLBACK */}
        {currentUser && currentUser.role === "PROFESSIONAL" && currentUser.professional_profile?.verification_status === "VERIFIED" && (
          activeScreen === "pro-dashboard" ||
          (activeScreen === "pro-review" && !activeReviewId) ||
          !["pro-dashboard", "pro-review", "pro-pending"].includes(activeScreen)
        ) && (
          <ProfessionalDashboard
            currentUser={currentUser}
            reviews={proReviews}
            loading={proReviewsLoading}
            error={proReviewsError}
            onOpenReview={openProfessionalReview}
            onRefresh={loadProfessionalReviews}
          />
        )}

        {/* PROFESSIONAL CASE WORKSPACE (MILESTONE 3B) */}
        {currentUser && activeScreen === "pro-review" && activeReviewId && (
          <ProfessionalCaseWorkspace
            reviewId={activeReviewId}
            onBack={navigateBack}
            onWorkflowComplete={loadProfessionalReviews}
          />
        )}
      </main>

      {/* FOOTER (Only for authenticated sessions) */}
      {!isGuestLanding && (
        <footer>
          <div className="footer-brand">HC-XCDSS</div>
          <p>AI-assisted chest X-ray decision support</p>
          <p className="footer-disclaimer">
            AI output is not a confirmed medical diagnosis. Professional clinical
            review is required.
          </p>
        </footer>
      )}
    </div>
  );
}

export default App;