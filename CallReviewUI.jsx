import React, { useState, useRef } from "react";
import { ChevronDown, ChevronUp, Upload, RotateCcw, Loader2, FileAudio, Printer } from "lucide-react";

const API_URL = "http://localhost:8000";


const theme = {
  bg: "#14161B",
  surface: "#1B1E24",
  surfaceRaised: "#22262E",
  border: "#2B2F38",
  textPrimary: "#EAEAEA",
  textMuted: "#8B909B",
  accent: "#E3A542",
  high: "#6FAE8B",
  mid: "#E3A542",
  low: "#C15C4F",
};

const sans = "'IBM Plex Sans', system-ui, sans-serif";
const mono = "'IBM Plex Mono', ui-monospace, monospace";

function scoreColor(score) {
  if (score >= 8) return theme.high;
  if (score >= 5) return theme.mid;
  return theme.low;
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const SAMPLE_DATA = {
  journey: [
    {
      timestamp: 4.2,
      speaker: "SALES",
      statement: "Hi, thanks for taking the time today. Before I dive in, can I ask what's prompting you to look at a new solution right now?",
      analysis: {
        what_was_said: "Opens by asking about the customer's motivation rather than pitching.",
        tone_estimate: "Warm, unhurried",
        message_classification: ["Consultative", "Customer-focused"],
        customer_reaction: "Customer opened up about a specific pain point, indicating trust was established early.",
        score: 9,
        explanation: "Diagnostic opening creates space for the customer to lead.",
        better_alternative: "Strong as-is",
      },
    },
    {
      timestamp: 11.8,
      speaker: "CUSTOMER",
      statement: "Honestly, our current tool just can't keep up with our reporting needs. We're stitching together spreadsheets every week.",
    },
    {
      timestamp: 19.5,
      speaker: "SALES",
      statement: "We have a really powerful reporting suite that automates all of that, with over forty prebuilt templates.",
      analysis: {
        what_was_said: "Pivots immediately into a product feature dump instead of exploring the pain point further.",
        tone_estimate: "Confident, slightly rushed",
        message_classification: ["Product-focused", "Salesy"],
        customer_reaction: "Customer's response was short and non-committal, a sign of disengagement.",
        score: 4,
        explanation: "Jumping to features before understanding scope of the reporting problem reads as scripted.",
        better_alternative: "What does that weekly spreadsheet process actually look like for your team right now?",
      },
    },
    {
      timestamp: 27.1,
      speaker: "CUSTOMER",
      statement: "Sure, sounds useful I guess. What's the pricing look like?",
    },
    {
      timestamp: 34.6,
      speaker: "SALES",
      statement: "Given what you've described, a lot of teams in your position start with our mid-tier plan since it covers the automated reporting without the enterprise overhead.",
      analysis: {
        what_was_said: "Reconnects the pricing answer back to the customer's stated need before naming a number.",
        tone_estimate: "Steady, measured",
        message_classification: ["Consultative", "Credible"],
        customer_reaction: "Customer asked a specific follow-up question about implementation time, signaling renewed interest.",
        score: 8,
        explanation: "Recovers well by tying the recommendation to the earlier pain point.",
        better_alternative: "Strong as-is",
      },
    },
  ],
  final_report: {
    overall_score: 68,
    scoring_explanation: "Weighted toward the back half of the call, since the recovery after the mid-call dip mattered more than the early stumble.",
    what_you_did_well: [
      "Opened with a diagnostic question instead of a pitch",
      "Reconnected the pricing conversation to the customer's actual stated pain point",
    ],
    where_you_lost_the_customer: [
      "Jumped into a feature list before fully exploring the reporting pain point",
    ],
    where_it_improved: [
      "Tying the mid-tier plan recommendation directly to the spreadsheet problem re-engaged the customer",
    ],
    what_to_do_differently: [
      "Before listing features, ask one more question about the current process, e.g. \"What does that weekly spreadsheet process actually look like?\"",
    ],
    top_3_recommendations: [
      "Slow down between diagnosis and pitch — earn one more question before naming a feature",
      "Keep tying any product mention back to a specific thing the customer already said",
      "Watch for short, non-committal replies as an early signal to pull back and re-ask",
    ],
  },
};

function ReportSection({ title, items, color }) {
  if (!items || items.length === 0) return null;
  return (
    <div style={{ marginBottom: "20px" }}>
      <div style={{ fontSize: "13px", color: theme.textMuted, marginBottom: "8px" }}>
        {title}
      </div>
      <ul style={{ margin: 0, paddingLeft: "18px" }}>
        {items.map((item, i) => (
          <li
            key={i}
            style={{
              fontSize: "14px",
              lineHeight: 1.6,
              color: theme.textPrimary,
              marginBottom: "4px",
            }}
          >
            <span style={{ color }}>▸</span> {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function TranscriptTurn({ turn, isOpen, onToggle }) {
  const isSales = turn.speaker === "SALES";
  const score = turn.analysis?.score;
  const color = isSales && score != null ? scoreColor(score) : theme.border;

  return (
    <div
      className="turn-block"
      style={{
        borderLeft: `3px solid ${color}`,
        paddingLeft: "16px",
        marginBottom: "4px",
      }}
    >
      <div
        onClick={isSales ? onToggle : undefined}
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: "16px",
          padding: "14px 12px 14px 4px",
          cursor: isSales ? "pointer" : "default",
        }}
      >
        <span
          style={{
            fontFamily: mono,
            fontSize: "12px",
            color: theme.textMuted,
            paddingTop: "2px",
            width: "40px",
            flexShrink: 0,
          }}
        >
          {formatTime(turn.timestamp)}
        </span>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: "12px",
              color: isSales ? theme.accent : theme.textMuted,
              marginBottom: "4px",
            }}
          >
            {isSales ? "Sales" : "Customer"}
          </div>
          <div style={{ fontSize: "15px", lineHeight: 1.55, color: theme.textPrimary }}>
            {turn.statement}
          </div>
        </div>

        {isSales && score != null && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              flexShrink: 0,
              paddingTop: "2px",
            }}
          >
            <span style={{ fontFamily: mono, fontSize: "16px", color }}>{score}</span>
            {isOpen ? (
              <ChevronUp size={15} color={theme.textMuted} />
            ) : (
              <ChevronDown size={15} color={theme.textMuted} />
            )}
          </div>
        )}
      </div>

      {isSales && isOpen && turn.analysis && (
        <div
          style={{
            background: theme.surfaceRaised,
            borderRadius: "4px",
            padding: "16px 18px",
            marginLeft: "4px",
            marginBottom: "12px",
            marginRight: "12px",
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "14px" }}>
            <div>
              <div style={{ fontSize: "12px", color: theme.textMuted, marginBottom: "4px" }}>
                Tone
              </div>
              <div style={{ fontSize: "14px", color: theme.textPrimary }}>
                {turn.analysis.tone_estimate}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "12px", color: theme.textMuted, marginBottom: "4px" }}>
                Classification
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                {(turn.analysis.message_classification || []).map((label, i) => (
                  <span
                    key={i}
                    style={{
                      fontSize: "12px",
                      color: theme.textPrimary,
                      border: `1px solid ${theme.border}`,
                      borderRadius: "3px",
                      padding: "2px 8px",
                    }}
                  >
                    {label}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div style={{ marginBottom: "14px" }}>
            <div style={{ fontSize: "12px", color: theme.textMuted, marginBottom: "4px" }}>
              Customer reaction
            </div>
            <div style={{ fontSize: "14px", lineHeight: 1.55, color: theme.textPrimary }}>
              {turn.analysis.customer_reaction}
            </div>
          </div>

          <div>
            <div style={{ fontSize: "12px", color: theme.textMuted, marginBottom: "4px" }}>
              {turn.analysis.better_alternative === "Strong as-is" ? "Assessment" : "Try instead"}
            </div>
            <div
              style={{
                fontSize: "14px",
                lineHeight: 1.55,
                color: turn.analysis.better_alternative === "Strong as-is" ? theme.high : theme.textPrimary,
                fontStyle: turn.analysis.better_alternative === "Strong as-is" ? "normal" : "italic",
              }}
            >
              {turn.analysis.better_alternative === "Strong as-is"
                ? turn.analysis.explanation
                : `"${turn.analysis.better_alternative}"`}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function CallReviewUI() {
  const [data, setData] = useState(SAMPLE_DATA);
  const [openIndex, setOpenIndex] = useState(null);
  const [error, setError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingFileName, setProcessingFileName] = useState(null);
  const [expandAllForPrint, setExpandAllForPrint] = useState(false);
  const fileInputRef = useRef(null);
  const audioInputRef = useRef(null);

  const handleFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target.result);
        if (!parsed.journey || !parsed.final_report) {
          throw new Error("Missing journey or final_report field");
        }
        setData(parsed);
        setOpenIndex(null);
        setError(null);
      } catch (err) {
        setError("Couldn't read that file — expected the report JSON from analyze.py.");
      }
    };
    reader.readAsText(file);
  };

  const handleAudioUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsProcessing(true);
    setProcessingFileName(file.name);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_URL}/process-call`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => null);
        throw new Error(errBody?.detail || `Server returned ${response.status}`);
      }

      const result = await response.json();
      setData(result);
      setOpenIndex(null);
    } catch (err) {
      setError(
        err.message.includes("fetch")
          ? "Couldn't reach the pipeline server. Make sure it's running: uvicorn server:app --reload --port 8000"
          : `Processing failed: ${err.message}`
      );
    } finally {
      setIsProcessing(false);
      setProcessingFileName(null);
      e.target.value = "";
    }
  };


  const overall = data.final_report.overall_score;
  const overallColor = scoreColor(overall / 10);

  return (
    <div
      style={{
        fontFamily: sans,
        background: theme.bg,
        color: theme.textPrimary,
        minHeight: "100vh",
        padding: "40px 20px",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        @media print {
          /* Force a light theme on paper: the dark UI would either burn
             through ink or get stripped by the browser's background removal. */
          * {
            background: #fff !important;
            color: #111 !important;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
          /* Keep the score colours, which carry meaning. */
          .score-value { color: inherit !important; }
          .no-print { display: none !important; }
          button { display: none !important; }
          /* Avoid splitting a statement and its analysis across pages. */
          .turn-block {
            break-inside: avoid;
            page-break-inside: avoid;
          }
          @page { margin: 16mm; }
        }
      `}</style>

      <div style={{ maxWidth: "720px", margin: "0 auto" }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: "36px",
            paddingBottom: "28px",
            borderBottom: `1px solid ${theme.border}`,
          }}
        >
          <div>
            <div style={{ fontSize: "13px", color: theme.textMuted, marginBottom: "10px" }}>
              Call review
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "10px" }}>
              <span style={{ fontFamily: mono, fontSize: "48px", fontWeight: 500, color: overallColor }}>
                {overall}
              </span>
              <span style={{ fontSize: "14px", color: theme.textMuted }}>/ 100</span>
            </div>
            <div style={{ fontSize: "13px", color: theme.textMuted, marginTop: "10px", maxWidth: "480px", lineHeight: 1.5 }}>
              {data.final_report.scoring_explanation}
            </div>
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            <button
              onClick={() => audioInputRef.current?.click()}
              disabled={isProcessing}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                background: theme.accent,
                border: "none",
                borderRadius: "4px",
                color: theme.bg,
                fontSize: "13px",
                fontWeight: 500,
                padding: "8px 12px",
                cursor: isProcessing ? "default" : "pointer",
                fontFamily: sans,
                opacity: isProcessing ? 0.6 : 1,
              }}
            >
              <FileAudio size={14} />
              Process recording
            </button>
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isProcessing}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                background: "none",
                border: `1px solid ${theme.border}`,
                borderRadius: "4px",
                color: theme.textPrimary,
                fontSize: "13px",
                padding: "8px 12px",
                cursor: isProcessing ? "default" : "pointer",
                fontFamily: sans,
                opacity: isProcessing ? 0.6 : 1,
              }}
            >
              <Upload size={14} />
              Load report
            </button>
            <button
              className="no-print"
              onClick={() => {
                // Collapsed turns aren't in the DOM, so expand everything
                // first or the printed PDF would omit most of the analysis.
                setExpandAllForPrint(true);
                setTimeout(() => {
                  window.print();
                  setExpandAllForPrint(false);
                }, 100);
              }}
              disabled={isProcessing}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                background: "none",
                border: `1px solid ${theme.border}`,
                borderRadius: "4px",
                color: theme.textPrimary,
                fontSize: "13px",
                padding: "8px 12px",
                cursor: isProcessing ? "default" : "pointer",
                fontFamily: sans,
                opacity: isProcessing ? 0.6 : 1,
              }}
            >
              <Printer size={14} />
              Save as PDF
            </button>
            {data !== SAMPLE_DATA && (
              <button
                onClick={() => { setData(SAMPLE_DATA); setOpenIndex(null); setError(null); }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "none",
                  border: `1px solid ${theme.border}`,
                  borderRadius: "4px",
                  color: theme.textMuted,
                  fontSize: "13px",
                  padding: "8px 12px",
                  cursor: "pointer",
                  fontFamily: sans,
                }}
              >
                <RotateCcw size={14} />
                Reset
              </button>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,application/json"
              onChange={handleFile}
              style={{ display: "none" }}
            />
            <input
              ref={audioInputRef}
              type="file"
              accept="audio/*,video/*"
              onChange={handleAudioUpload}
              style={{ display: "none" }}
            />
          </div>
        </div>

        {isProcessing && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              fontSize: "13px",
              color: theme.textMuted,
              marginBottom: "24px",
              padding: "12px 14px",
              border: `1px solid ${theme.border}`,
              borderRadius: "4px",
            }}
          >
            <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} color={theme.accent} />
            Processing {processingFileName} — transcribing, identifying speakers, and analyzing. This can take a few minutes.
          </div>
        )}


        {error && (
          <div style={{ fontSize: "13px", color: theme.low, marginBottom: "24px" }}>
            {error}
          </div>
        )}

        {/* Report summary */}
        <div style={{ marginBottom: "40px" }}>
          <ReportSection title="What went well" items={data.final_report.what_you_did_well} color={theme.high} />
          <ReportSection title="Where the customer disengaged" items={data.final_report.where_you_lost_the_customer} color={theme.low} />
          <ReportSection title="Where it improved" items={data.final_report.where_it_improved} color={theme.high} />
          <ReportSection title="Top recommendations" items={data.final_report.top_3_recommendations} color={theme.accent} />
        </div>

        {/* Transcript */}
        <div>
          <div style={{ fontSize: "13px", color: theme.textMuted, marginBottom: "12px" }}>
            Transcript
          </div>
          <div>
            {data.journey.map((turn, i) => (
              <TranscriptTurn
                key={i}
                turn={turn}
                isOpen={expandAllForPrint || openIndex === i}
                onToggle={() => setOpenIndex(openIndex === i ? null : i)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}