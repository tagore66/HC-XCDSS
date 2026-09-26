import { useState, useRef, useEffect } from "react";
import { askAssistant } from "../services/api";
import {
  Sparkles,
  User,
  Stethoscope,
  Send,
  AlertTriangle,
  HelpCircle,
  Shield,
  MessageSquare,
  X,
  ChevronDown,
  Maximize2,
  Minimize2,
} from "lucide-react";

/**
 * Lightweight, zero-dependency clinical Markdown renderer for Gemini responses.
 */
function ClinicalMarkdown({ content }) {
  if (!content) return null;

  const lines = content.split("\n");
  const blocks = [];
  let currentList = null;
  let listType = null;

  const flushList = () => {
    if (currentList && currentList.length > 0) {
      if (listType === "ol") {
        blocks.push(
          <ol key={`ol-${blocks.length}`} style={{ paddingLeft: "18px", margin: "6px 0" }}>
            {currentList.map((item, idx) => (
              <li key={idx} style={{ marginBottom: "3px" }}>{parseInlineFormatting(item)}</li>
            ))}
          </ol>
        );
      } else {
        blocks.push(
          <ul key={`ul-${blocks.length}`} style={{ paddingLeft: "18px", margin: "6px 0" }}>
            {currentList.map((item, idx) => (
              <li key={idx} style={{ marginBottom: "3px" }}>{parseInlineFormatting(item)}</li>
            ))}
          </ul>
        );
      }
      currentList = null;
      listType = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (!line) {
      flushList();
      continue;
    }

    if (line === "---" || line === "***" || line === "___") {
      flushList();
      blocks.push(<hr key={`hr-${i}`} style={{ border: "none", borderTop: "1px solid var(--border-subtle)", margin: "10px 0" }} />);
      continue;
    }

    if (line.startsWith("### ")) {
      flushList();
      blocks.push(
        <h4 key={`h4-${i}`} style={{ fontSize: "13px", fontWeight: "700", margin: "10px 0 4px", color: "var(--text-primary)" }}>
          {parseInlineFormatting(line.replace(/^###\s+/, ""))}
        </h4>
      );
      continue;
    }
    if (line.startsWith("## ")) {
      flushList();
      blocks.push(
        <h3 key={`h3-${i}`} style={{ fontSize: "14px", fontWeight: "700", margin: "12px 0 4px", color: "var(--text-primary)" }}>
          {parseInlineFormatting(line.replace(/^##\s+/, ""))}
        </h3>
      );
      continue;
    }

    const bulletMatch = line.match(/^[-*]\s+(.*)$/);
    if (bulletMatch) {
      if (listType !== "ul") {
        flushList();
        listType = "ul";
        currentList = [];
      }
      currentList.push(bulletMatch[1]);
      continue;
    }

    const numberMatch = line.match(/^(\d+)\.\s+(.*)$/);
    if (numberMatch) {
      if (listType !== "ol") {
        flushList();
        listType = "ol";
        currentList = [];
      }
      currentList.push(numberMatch[2]);
      continue;
    }

    flushList();
    blocks.push(
      <p key={`p-${i}`} style={{ margin: "4px 0", lineHeight: "1.5", fontSize: "13px" }}>
        {parseInlineFormatting(line)}
      </p>
    );
  }

  flushList();
  return <div className="clinical-md-container">{blocks}</div>;
}

function parseInlineFormatting(text) {
  if (!text) return "";

  const tokens = [];
  let lastIndex = 0;
  const pattern = /(\*\*(.*?)\*\*|\*(.*?)\*|`(.*?)`)/g;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push(text.substring(lastIndex, match.index));
    }

    if (match[2] !== undefined) {
      tokens.push(<strong key={match.index} style={{ fontWeight: "700", color: "var(--text-primary)" }}>{match[2]}</strong>);
    } else if (match[3] !== undefined) {
      tokens.push(<em key={match.index}>{match[3]}</em>);
    } else if (match[4] !== undefined) {
      tokens.push(
        <code key={match.index} style={{ background: "var(--surface-tertiary)", padding: "1px 5px", borderRadius: "3px", fontSize: "12px" }}>
          {match[4]}
        </code>
      );
    }

    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    tokens.push(text.substring(lastIndex));
  }

  return tokens.length > 0 ? tokens : text;
}

function formatCaseId(id) {
  if (!id) return "—";
  const clean = String(id).replace(/^#/, "");
  return `Case #${clean.substring(0, 8).toUpperCase()}`;
}

/**
 * AIAssistant - Floating Bottom-Right Clinical AI Assistant
 * 
 * Collapsed: High-end floating trigger button.
 * Expanded: Floating side drawer (390-430px) anchored at bottom-right.
 */
export default function AIAssistant({ analysis, initialRole = "patient" }) {
  const [isOpen, setIsOpen] = useState(false);
  const [role, setRole] = useState(initialRole);
  const [messages, setMessages] = useState([]);
  const [inputQuestion, setInputQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const chatMessagesRef = useRef(null);

  const scrollToBottom = () => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTo({
        top: chatMessagesRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen, loading]);

  const handleOpen = () => {
    setIsOpen(true);
    if (messages.length === 0) {
      const detectedCount = analysis?.detected_findings?.length || 0;
      const detectedList = analysis?.detected_findings?.join(", ") || "none";
      const greeting =
        detectedCount > 0
          ? `Hello! I have loaded the clinical context for this **${analysis?.view || "Frontal"}** chest radiograph (**${formatCaseId(analysis?.analysis_id)}**).\n\n` +
            `### Active Radiographic Findings:\n` +
            `* **${detectedCount} finding(s) detected above threshold:** ${detectedList}\n\n` +
            `You can ask me to explain what these findings mean, review visual Grad-CAM focus areas, or suggest questions to discuss with your healthcare provider.`
          : `Hello! I have loaded the clinical context for this **${analysis?.view || "Frontal"}** chest radiograph (**${formatCaseId(analysis?.analysis_id)}**).\n\n` +
            `No acute findings were detected above operating thresholds. What questions can I answer about the evaluated thoracic conditions or report summary?`;

      setMessages([
        {
          role: "model",
          content: greeting,
          provider: "gemini",
          model: "gemini-3.7-flash",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    }
  };

  const handleSend = async (e) => {
    if (e) e.preventDefault();
    if (!inputQuestion.trim() || loading) return;

    const userText = inputQuestion.trim();
    setInputQuestion("");
    setError("");

    const newTurn = {
      role: "user",
      content: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const updatedMessages = [...messages, newTurn];
    setMessages(updatedMessages);
    setLoading(true);

    try {
      const historyForApi = updatedMessages.map((m) => ({
        role: m.role === "model" ? "model" : "user",
        content: m.content,
      }));

      const res = await askAssistant(analysis.analysis_id, userText, role, historyForApi);

      const aiTurn = {
        role: "model",
        content: res.answer,
        provider: res.provider,
        model: res.model,
        safety_status: res.safety_status,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages([...updatedMessages, aiTurn]);
    } catch (err) {
      console.error("AI Assistant request failure:", err);
      setError(err.message || "Unable to contact the AI assistant service. Please check your network connection.");
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionClick = (questionText) => {
    setInputQuestion(questionText);
  };

  return (
    <aside aria-label="AI Clinical Assistant" className="floating-assistant-wrapper">
      {/* 1. FLOATING LAUNCHER BUTTON (COLLAPSED STATE) */}
      {!isOpen && (
        <button
          type="button"
          className="floating-ai-launcher"
          onClick={handleOpen}
          title="Open AI Clinical Assistant"
          aria-expanded="false"
        >
          <div className="launcher-icon-badge">
            <Sparkles size={16} />
          </div>
          <span className="launcher-text">Ask about this X-ray</span>
          <span className="launcher-case-pill">{formatCaseId(analysis?.analysis_id)}</span>
        </button>
      )}

      {/* 2. FLOATING EXPANDED CHAT PANEL */}
      {isOpen && (
        <div className="floating-ai-panel" role="dialog" aria-modal="false" aria-label="AI Clinical Assistant">
          {/* Panel Header */}
          <div className="floating-panel-header">
            <div className="panel-header-title-block">
              <div className="ai-status-indicator">
                <span className="ai-live-pulse" />
                <Sparkles size={15} color="var(--accent-primary)" />
              </div>
              <div>
                <h3 className="panel-title">AI Clinical Assistant</h3>
                <span className="panel-subtitle">Context Linked • {formatCaseId(analysis?.analysis_id)}</span>
              </div>
            </div>

            <button
              type="button"
              className="panel-close-btn"
              onClick={() => setIsOpen(false)}
              aria-label="Minimize AI Assistant"
              title="Minimize panel"
            >
              <X size={16} />
            </button>
          </div>

          {/* Role Mode Selector Toolbar */}
          <div className="panel-mode-bar">
            <span className="mode-label">Audience Mode:</span>
            <div className="mode-toggle-group">
              <button
                type="button"
                className={`btn-mode-toggle ${role === "patient" ? "active" : ""}`}
                onClick={() => setRole("patient")}
              >
                <User size={12} />
                <span>Patient</span>
              </button>
              <button
                type="button"
                className={`btn-mode-toggle ${role === "professional" ? "active" : ""}`}
                onClick={() => setRole("professional")}
              >
                <Stethoscope size={12} />
                <span>Physician</span>
              </button>
            </div>
          </div>

          {/* Chat Message Scroll Thread */}
          <div className="floating-chat-scroll" ref={chatMessagesRef}>
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`chat-bubble-row ${msg.role === "user" ? "user-row" : "ai-row"}`}
              >
                <div className="chat-avatar-badge">
                  {msg.role === "user" ? <User size={12} /> : <Sparkles size={12} color="var(--accent-primary)" />}
                </div>

                <div className={`chat-bubble ${msg.role === "user" ? "user-bubble" : "ai-bubble"}`}>
                  <div className="bubble-content">
                    {msg.role === "model" ? (
                      <ClinicalMarkdown content={msg.content} />
                    ) : (
                      <p style={{ margin: 0 }}>{msg.content}</p>
                    )}
                  </div>

                  <div className="bubble-footer">
                    <span>{msg.timestamp}</span>
                    {msg.model && <span>• Gemini 3.7 Flash</span>}
                  </div>
                </div>
              </div>
            ))}

            {loading && (
              <div className="chat-bubble-row ai-row">
                <div className="chat-avatar-badge">
                  <Sparkles size={12} color="var(--accent-primary)" />
                </div>
                <div className="chat-bubble ai-bubble loading-bubble">
                  <span className="spinner-dots" />
                  <span>Synthesizing radiographic report context...</span>
                </div>
              </div>
            )}
          </div>

          {/* Suggested Quick Question Prompts */}
          <div className="floating-suggestions-strip">
            <div className="suggestions-scroll">
              {role === "professional" ? (
                <>
                  <button
                    type="button"
                    className="suggestion-chip"
                    onClick={() => handleSuggestionClick("Evaluate radiological correlation with operating thresholds.")}
                  >
                    Operating Thresholds
                  </button>
                  <button
                    type="button"
                    className="suggestion-chip"
                    onClick={() => handleSuggestionClick("Explain the Grad-CAM spatial activation on this view.")}
                  >
                    Grad-CAM Activation
                  </button>
                  <button
                    type="button"
                    className="suggestion-chip"
                    onClick={() => handleSuggestionClick("What are the clinical limitations of this AI prediction?")}
                  >
                    Model Limitations
                  </button>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    className="suggestion-chip"
                    onClick={() => handleSuggestionClick("Explain my chest X-ray report in simple terms.")}
                  >
                    Explain findings simply
                  </button>
                  <button
                    type="button"
                    className="suggestion-chip"
                    onClick={() => handleSuggestionClick("What does the highlighted region on my scan mean?")}
                  >
                    What does highlighted region mean?
                  </button>
                  <button
                    type="button"
                    className="suggestion-chip"
                    onClick={() => handleSuggestionClick("What questions should I ask my doctor about these results?")}
                  >
                    Questions for my doctor
                  </button>
                </>
              )}
            </div>
          </div>

          {error && (
            <div className="floating-error-notice">
              <AlertTriangle size={13} />
              <span>{error}</span>
            </div>
          )}

          {/* Input Form */}
          <form onSubmit={handleSend} className="floating-chat-form">
            <input
              type="text"
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              placeholder={
                role === "professional"
                  ? "Ask technical/clinical questions on this case..."
                  : "Ask a question about your X-ray results..."
              }
              className="floating-chat-input"
              disabled={loading}
            />
            <button
              type="submit"
              className="floating-send-btn"
              disabled={loading || !inputQuestion.trim()}
              aria-label="Send question"
            >
              <Send size={13} />
            </button>
          </form>

          {/* Safety Disclaimer Footer */}
          <div className="floating-safety-note">
            <span>🛡️ AI decision support. Not a confirmed medical diagnosis.</span>
          </div>
        </div>
      )}
    </aside>
  );
}
