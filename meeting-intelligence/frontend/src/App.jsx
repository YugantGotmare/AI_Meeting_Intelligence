import { useState, useEffect, useRef } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ─── Polling hook ────────────────────────────────────────────
function useMeetingStatus(meetingId) {
  const [data, setData] = useState(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!meetingId) return;

    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/meetings/${meetingId}`);
        const json = await res.json();
        setData(json);
        if (json.status === "done" || json.status === "failed") {
          clearInterval(intervalRef.current);
        }
      } catch (e) {
        console.error(e);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2500);
    return () => clearInterval(intervalRef.current);
  }, [meetingId]);

  return data;
}

// ─── Components ──────────────────────────────────────────────
function StatusBadge({ status }) {
  const map = {
    pending:     { label: "Queued",       color: "#a0aec0" },
    processing:  { label: "Processing…",  color: "#f6ad55" },
    transcribed: { label: "Transcribed",  color: "#68d391" },
    diarized:    { label: "Diarized",     color: "#68d391" },
    extracted:   { label: "Extracted",    color: "#63b3ed" },
    checked:     { label: "Checking…",   color: "#f6ad55" },
    done:        { label: "Complete",     color: "#48bb78" },
    failed:      { label: "Failed",       color: "#fc8181" },
  };
  const s = map[status] || { label: status, color: "#a0aec0" };
  return (
    <span style={{
      display: "inline-block",
      padding: "2px 10px",
      borderRadius: "99px",
      fontSize: "11px",
      fontWeight: 700,
      letterSpacing: "0.08em",
      textTransform: "uppercase",
      background: s.color + "22",
      color: s.color,
      border: `1px solid ${s.color}55`,
    }}>
      {s.label}
    </span>
  );
}

function ActionItems({ items }) {
  if (!items?.length) return <p style={styles.empty}>No action items found.</p>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {items.map((item, i) => (
        <div key={i} style={styles.card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <span style={{ fontWeight: 600, color: "#e2e8f0", flex: 1 }}>{item.task}</span>
            <span style={{
              marginLeft: "12px",
              padding: "1px 8px",
              borderRadius: "4px",
              fontSize: "11px",
              fontWeight: 700,
              background: item.priority === "high" ? "#fc818133" : item.priority === "low" ? "#68d39133" : "#f6ad5533",
              color: item.priority === "high" ? "#fc8181" : item.priority === "low" ? "#68d391" : "#f6ad55",
            }}>
              {item.priority}
            </span>
          </div>
          <div style={{ marginTop: "6px", fontSize: "13px", color: "#a0aec0" }}>
            <span>👤 {item.owner}</span>
            {item.deadline && <span style={{ marginLeft: "14px" }}>📅 {item.deadline}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

function Decisions({ items }) {
  if (!items?.length) return <p style={styles.empty}>No decisions recorded.</p>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {items.map((d, i) => (
        <div key={i} style={styles.card}>
          <div style={{ fontWeight: 600, color: "#e2e8f0" }}>{d.decision}</div>
          <div style={{ marginTop: "4px", fontSize: "13px", color: "#a0aec0" }}>{d.context}</div>
          {d.made_by && <div style={{ marginTop: "4px", fontSize: "12px", color: "#718096" }}>By: {d.made_by}</div>}
        </div>
      ))}
    </div>
  );
}

function OpenQuestions({ items }) {
  if (!items?.length) return <p style={styles.empty}>No open questions.</p>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {items.map((q, i) => (
        <div key={i} style={{ ...styles.card, display: "flex", gap: "10px", alignItems: "flex-start" }}>
          <span style={{ color: "#f6ad55", marginTop: "1px" }}>?</span>
          <span style={{ color: "#cbd5e0" }}>{q}</span>
        </div>
      ))}
    </div>
  );
}

function FollowUpEmail({ text }) {
  const [copied, setCopied] = useState(false);
  if (!text) return null;

  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ position: "relative" }}>
      <button onClick={copy} style={styles.copyBtn}>
        {copied ? "✓ Copied" : "Copy"}
      </button>
      <pre style={styles.emailBox}>{text}</pre>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>{title}</h3>
      {children}
    </div>
  );
}

// ─── Upload screen ────────────────────────────────────────────
function UploadScreen({ onUploaded }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const upload = async (file) => {
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_BASE}/meetings/upload`, { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }
      const data = await res.json();
      onUploaded(data.meeting_id, file.name);
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) upload(file);
  };

  return (
    <div style={styles.uploadWrapper}>
      <div
        style={{ ...styles.dropZone, ...(dragging ? styles.dropZoneActive : {}) }}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp3,.mp4,.wav,.m4a,.webm,.ogg"
          style={{ display: "none" }}
          onChange={(e) => { if (e.target.files[0]) upload(e.target.files[0]); }}
        />
        {uploading ? (
          <div style={styles.uploadInner}>
            <div style={styles.spinner} />
            <p style={styles.uploadLabel}>Uploading…</p>
          </div>
        ) : (
          <div style={styles.uploadInner}>
            <div style={styles.uploadIcon}>🎙</div>
            <p style={styles.uploadLabel}>Drop a meeting recording here</p>
            <p style={styles.uploadSub}>or click to browse · mp3, mp4, wav, m4a, webm</p>
          </div>
        )}
      </div>
      {error && <p style={styles.errorMsg}>{error}</p>}
    </div>
  );
}

// ─── Results screen ───────────────────────────────────────────
function ResultsScreen({ meetingId, filename, onReset }) {
  const data = useMeetingStatus(meetingId);
  const [tab, setTab] = useState("actions");

  const tabs = [
    { id: "actions",   label: `Actions (${data?.action_items?.length ?? "…"})` },
    { id: "decisions", label: `Decisions (${data?.decisions?.length ?? "…"})` },
    { id: "questions", label: `Questions (${data?.open_questions?.length ?? "…"})` },
    { id: "email",     label: "Follow-up Email" },
  ];

  return (
    <div style={styles.resultsWrapper}>
      <div style={styles.resultHeader}>
        <div>
          <h2 style={styles.filename}>{filename}</h2>
          <div style={{ marginTop: "6px", display: "flex", alignItems: "center", gap: "10px" }}>
            {data && <StatusBadge status={data.status} />}
            {data?.quality_score != null && (
              <span style={{ fontSize: "12px", color: "#718096" }}>
                Quality score: {Math.round(data.quality_score * 100)}%
              </span>
            )}
          </div>
        </div>
        <button onClick={onReset} style={styles.resetBtn}>← New Meeting</button>
      </div>

      {(!data || data.status === "pending" || data.status === "processing") && (
        <div style={styles.processingBox}>
          <div style={styles.spinner} />
          <p style={{ color: "#a0aec0", marginTop: "14px" }}>
            {!data ? "Connecting…" : "Agent is analyzing your meeting…"}
          </p>
          <p style={{ color: "#4a5568", fontSize: "13px", marginTop: "6px" }}>
            Transcribing → Diarizing speakers → Extracting intelligence → Quality checking
          </p>
        </div>
      )}

      {data?.status === "failed" && (
        <div style={styles.errorBox}>
          <p style={{ color: "#fc8181", fontWeight: 600 }}>Processing failed</p>
          <p style={{ color: "#a0aec0", fontSize: "13px", marginTop: "4px" }}>{data.error}</p>
        </div>
      )}

      {data?.status === "done" && (
        <>
          <div style={styles.tabBar}>
            {tabs.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                style={{ ...styles.tab, ...(tab === t.id ? styles.tabActive : {}) }}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div style={{ marginTop: "20px" }}>
            {tab === "actions"   && <ActionItems items={data.action_items} />}
            {tab === "decisions" && <Decisions items={data.decisions} />}
            {tab === "questions" && <OpenQuestions items={data.open_questions} />}
            {tab === "email"     && <FollowUpEmail text={data.follow_up_email} />}
          </div>
        </>
      )}
    </div>
  );
}

// ─── App ──────────────────────────────────────────────────────
export default function App() {
  const [meetingId, setMeetingId] = useState(null);
  const [filename, setFilename] = useState(null);

  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <div style={styles.logo}>⚡ MeetingMind</div>
        <p style={styles.tagline}>Drop a recording. Get structured intelligence.</p>
      </header>

      <main style={styles.main}>
        {!meetingId ? (
          <UploadScreen onUploaded={(id, name) => { setMeetingId(id); setFilename(name); }} />
        ) : (
          <ResultsScreen
            meetingId={meetingId}
            filename={filename}
            onReset={() => { setMeetingId(null); setFilename(null); }}
          />
        )}
      </main>
    </div>
  );
}

// ─── Styles ───────────────────────────────────────────────────
const styles = {
  root: {
    minHeight: "100vh",
    background: "#0d1117",
    color: "#e2e8f0",
    fontFamily: "'IBM Plex Mono', 'Fira Code', monospace",
  },
  header: {
    padding: "40px 40px 0",
    borderBottom: "1px solid #1e2733",
    paddingBottom: "24px",
  },
  logo: {
    fontSize: "22px",
    fontWeight: 700,
    color: "#63b3ed",
    letterSpacing: "-0.02em",
  },
  tagline: {
    margin: "6px 0 0",
    fontSize: "13px",
    color: "#4a5568",
  },
  main: {
    maxWidth: "780px",
    margin: "0 auto",
    padding: "40px 20px",
  },
  uploadWrapper: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "16px",
  },
  dropZone: {
    width: "100%",
    border: "2px dashed #2d3748",
    borderRadius: "12px",
    padding: "60px 40px",
    cursor: "pointer",
    transition: "border-color 0.2s, background 0.2s",
    textAlign: "center",
    background: "#111827",
  },
  dropZoneActive: {
    borderColor: "#63b3ed",
    background: "#0d1f35",
  },
  uploadInner: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "10px",
  },
  uploadIcon: {
    fontSize: "40px",
  },
  uploadLabel: {
    margin: 0,
    fontSize: "16px",
    color: "#a0aec0",
    fontWeight: 500,
  },
  uploadSub: {
    margin: 0,
    fontSize: "12px",
    color: "#4a5568",
  },
  resultsWrapper: {
    width: "100%",
  },
  resultHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: "28px",
  },
  filename: {
    margin: 0,
    fontSize: "18px",
    fontWeight: 600,
    color: "#e2e8f0",
  },
  resetBtn: {
    background: "none",
    border: "1px solid #2d3748",
    borderRadius: "6px",
    padding: "6px 14px",
    color: "#718096",
    cursor: "pointer",
    fontSize: "13px",
    fontFamily: "inherit",
  },
  tabBar: {
    display: "flex",
    gap: "4px",
    borderBottom: "1px solid #1e2733",
    paddingBottom: "0",
  },
  tab: {
    background: "none",
    border: "none",
    borderBottom: "2px solid transparent",
    padding: "8px 16px",
    color: "#718096",
    cursor: "pointer",
    fontSize: "13px",
    fontFamily: "inherit",
    marginBottom: "-1px",
    transition: "color 0.15s",
  },
  tabActive: {
    color: "#63b3ed",
    borderBottomColor: "#63b3ed",
  },
  card: {
    background: "#111827",
    border: "1px solid #1e2733",
    borderRadius: "8px",
    padding: "14px 16px",
  },
  section: {
    marginBottom: "32px",
  },
  sectionTitle: {
    margin: "0 0 14px",
    fontSize: "12px",
    fontWeight: 700,
    letterSpacing: "0.1em",
    textTransform: "uppercase",
    color: "#4a5568",
  },
  empty: {
    margin: 0,
    fontSize: "14px",
    color: "#4a5568",
    fontStyle: "italic",
  },
  processingBox: {
    textAlign: "center",
    padding: "60px 20px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  errorBox: {
    background: "#1a0e0e",
    border: "1px solid #fc818133",
    borderRadius: "8px",
    padding: "20px",
    marginTop: "20px",
  },
  errorMsg: {
    color: "#fc8181",
    fontSize: "14px",
    margin: 0,
  },
  emailBox: {
    background: "#111827",
    border: "1px solid #1e2733",
    borderRadius: "8px",
    padding: "20px",
    fontSize: "13px",
    lineHeight: 1.7,
    color: "#a0aec0",
    whiteSpace: "pre-wrap",
    overflowX: "auto",
    margin: 0,
  },
  copyBtn: {
    position: "absolute",
    top: "12px",
    right: "12px",
    background: "#1e2733",
    border: "1px solid #2d3748",
    borderRadius: "5px",
    padding: "4px 12px",
    color: "#a0aec0",
    cursor: "pointer",
    fontSize: "12px",
    fontFamily: "inherit",
  },
  spinner: {
    width: "28px",
    height: "28px",
    border: "3px solid #1e2733",
    borderTop: "3px solid #63b3ed",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
};

// inject keyframes
const style = document.createElement("style");
style.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
document.head.appendChild(style);
