import { useState, useEffect, useCallback } from "react";

// App version shown in the auth screen footer
const version = "1.0.2"

// Backend URL — all fetch calls point here
const API_BASE = "http://100.65.81.57:8000";

// Decodes a JWT's payload (without verifying signature) to read its exp claim
// Returns the expiry as epoch milliseconds, or null if the token can't be parsed
function getTokenExpiryMs(token) {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

// Wrapper around fetch that attaches the stored JWT as a Bearer token.
// On a 401 response, clears the stored session and fires "auth:expired" so
// the App component can drop back to the login screen.
async function authFetch(url, options = {}) {
  const token = localStorage.getItem("token");
  const res = await fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (res.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("userEmail");
    window.dispatchEvent(new Event("auth:expired"));
  }
  return res;
}

// The four fixed alert categories shown as columns on the dashboard
const CATEGORIES = ["Exec Watch", "Fraud", "Threat Intelligence", "Custom"];

// Accent colors for each category (used on card borders, badges, column headers)
const CATEGORY_COLORS = {
  "Exec Watch": "#7F77DD",
  "Fraud": "#D85A30",
  "Threat Intelligence": "#1D9E75",
  "Custom": "#888780",
};

// Translucent version of each accent color used as column header backgrounds
const CATEGORY_BG = {
  "Exec Watch": "rgba(127,119,221,0.12)",
  "Fraud": "rgba(216,90,48,0.12)",
  "Threat Intelligence": "rgba(29,158,117,0.12)",
  "Custom": "rgba(136,135,128,0.12)",
};

// Shared style object for all text inputs and selects across the app
const INPUT_STYLE = {
  width: "100%", background: "#0f0f16", border: "0.5px solid #2a2a38",
  borderRadius: 8, padding: "9px 12px", color: "#e8e6ff",
  fontSize: 13, outline: "none", boxSizing: "border-box",
};

// ─── Utility: timeAgo ────────────────────────────────────────────────────────
// Converts a timestamp string from the DB into a human-readable relative label
// e.g. "3h ago", "just now", "2d ago"
// Handles both "2024-01-01 12:00:00" and ISO formats by normalizing to UTC
function timeAgo(dateStr) {
  if (!dateStr) return "Unknown";
  let str = dateStr;
  if (typeof str === "string") {
    str = str.replace(" ", "T");
    if (/^\d{4}-\d{2}-\d{2}T[\d:.]+$/.test(str)) str += "Z";
  }
  const date = new Date(str);
  if (isNaN(date)) return String(dateStr);
  const diff = Math.max(0, Math.floor((Date.now() - date) / 1000));
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ─── Utility: buildQueryPreview ───────────────────────────────────────────────
// Reconstructs the Google dork query string from a watchlist's query_params object
// Used in AlertPanel ("why it was hit") and WatchlistFormModal (live preview)
function buildQueryPreview(qp) {
  if (!qp) return "";
  const parts = [];
  (qp.keywords || []).forEach(k => parts.push(`"${k}"`));
  const or_kw = qp.or_keywords || [];
  if (or_kw.length) parts.push(`(${or_kw.map(k => `"${k}"`).join(" OR ")})`);
  const inc = qp.include_sites || [];
  if (inc.length) parts.push(`(${inc.map(s => `site:${s}`).join(" OR ")})`);
  (qp.exclude_sites || []).forEach(s => parts.push(`-site:${s}`));
  return parts.join(" ");
}

// ─── Utility: highlightMatches ────────────────────────────────────────────────
// Wraps any keyword matches in the given text with a <mark> element
// Used in AlertPanel to highlight the keywords that caused the result to match
function highlightMatches(text, keywords) {
  if (!text || !keywords || keywords.length === 0) return text;
  const escaped = keywords.map(k => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const regex = new RegExp(`(${escaped.join("|")})`, "gi");
  return String(text).split(regex).map((part, i) =>
    keywords.some(k => k.toLowerCase() === part.toLowerCase())
      ? <mark key={i} style={{ background: "#7F77DD33", color: "#c4bffb", padding: "0 2px", borderRadius: 3 }}>{part}</mark>
      : part
  );
}

// ─── Component: TagInput ──────────────────────────────────────────────────────
// Reusable pill-style tag input. Press Enter or comma to confirm a tag.
// Backspace on empty input removes the last tag.
// Used inside WatchlistFormModal for keywords, exclude keywords, include sites, exclude sites.
function TagInput({ label, placeholder, values, onChange }) {
  const [input, setInput] = useState("");
  function handleKey(e) {
    if ((e.key === "Enter" || e.key === ",") && input.trim()) {
      e.preventDefault();
      const val = input.trim().replace(/,$/, "");
      if (val && !values.includes(val)) onChange([...values, val]);
      setInput("");
    }
    if (e.key === "Backspace" && !input && values.length) onChange(values.slice(0, -1));
  }
  return (
    <div>
      <label style={{ fontSize: 12, color: "#666", display: "block", marginBottom: 6 }}>{label}</label>
      <div style={{ ...INPUT_STYLE, padding: "6px 10px", display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", cursor: "text" }}>
        {values.map(v => (
          <span key={v} style={{ background: "#2a2a38", color: "#a8a4f0", fontSize: 11, padding: "2px 8px", borderRadius: 20, display: "flex", alignItems: "center", gap: 4 }}>
            {v}
            <span onClick={() => onChange(values.filter(x => x !== v))} style={{ cursor: "pointer", color: "#555", fontSize: 13, lineHeight: 1 }}>×</span>
          </span>
        ))}
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKey}
          placeholder={values.length === 0 ? placeholder : ""}
          style={{ background: "transparent", border: "none", outline: "none", color: "#e8e6ff", fontSize: 12, flex: 1, minWidth: 80 }} />
      </div>
      <p style={{ margin: "4px 0 0", fontSize: 10, color: "#444" }}>Press Enter or comma to add</p>
    </div>
  );
}

// ─── Component: AlertCard ─────────────────────────────────────────────────────
// A single search result card shown inside a Column.
// Clicking it opens the full AlertPanel slide-in.
// Shows: title (linked), snippet (2-line clamped), favicon, source, watchlist label, time ago.
// The left border color is the category accent. Dimmed (opacity 0.5) if already read.
function AlertCard({ alert, onOpenAlerts }) {
  const cat = alert.category || "Custom";
  const accent = CATEGORY_COLORS[cat] || CATEGORY_COLORS["Custom"];
  // Fetches the favicon for the alert's source domain via Google's favicon service
  const getFavicon = (url) => {
    try { return `https://www.google.com/s2/favicons?domain=${new URL(url).hostname}&sz=32`; }
    catch { return null; }
  };
  return (
    <div onClick={() => onOpenAlerts(alert)} style={{ background: "#18181f", border: "0.5px solid #2a2a38", borderLeft: `3px solid ${accent}`, borderRadius: "10px", padding: "14px 16px", marginBottom: "10px", opacity: alert.is_read ? 0.5 : 1, cursor: "pointer" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
        {/* Title — wraps naturally; wordBreak prevents long URLs from overflowing the card */}
        <p style={{ margin: 0, fontSize: "13px", fontWeight: 500, color: "#e8e6ff", lineHeight: 1.4, flex: 1, wordBreak: "break-word" }}>
          {alert.link ? (
            <a onClick={e => e.stopPropagation()} href={alert.link} target="_blank" rel="noopener noreferrer"
              style={{ color: "#e8e6ff", textDecoration: "none" }}
              onMouseEnter={e => e.target.style.color = accent}
              onMouseLeave={e => e.target.style.color = "#e8e6ff"}>
              {alert.title || "Untitled"}
            </a>
          ) : (alert.title || "Untitled")}
        </p>
        {/* External link icon — opens the URL directly without opening AlertPanel */}
        {alert.link && (
          <a onClick={e => e.stopPropagation()} href={alert.link} target="_blank" rel="noopener noreferrer" style={{ color: "#555", flexShrink: 0, marginTop: 2 }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
              <polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </a>
        )}
      </div>
      {/* Snippet — clamped to 2 lines max */}
      {alert.snippet && (
        <p style={{ margin: "8px 0 0", fontSize: "12px", color: "#888", lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {alert.snippet}
        </p>
      )}
      {/* Footer row: favicon, source domain, watchlist label, time ago */}
      <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "center" }}>
        {alert.link && getFavicon(alert.link) && (
          <img src={getFavicon(alert.link)} width={14} height={14} style={{ borderRadius: 3, flexShrink: 0 }} onError={e => e.target.style.display = "none"} />
        )}
        {alert.source && <span style={{ fontSize: "11px", color: "#666", fontWeight: 500 }}>{alert.source}</span>}
        <span style={{ fontSize: "11px", color: "#444" }}>·</span>
        <span style={{ fontSize: "11px", color: "#555" }}>{alert.label || "Unnamed Watchlist"}</span>
        <span style={{ fontSize: "11px", color: "#444", marginLeft: "auto" }}>{timeAgo(alert.fetched_at)}</span>
      </div>
    </div>
  );
}

// ─── Component: WatchlistFormModal ────────────────────────────────────────────
// Modal for creating a new watchlist (POST /watchlist) or editing one (PUT /watchlist/:id).
// Contains four TagInput fields for query parameters plus a category dropdown.
// Shows a live dork query preview that updates as you type.
// Validates that at least keywords OR include_sites is provided before submitting.
function WatchlistFormModal({ watchlist, onClose, onSaved }) {
  const isEdit = !!watchlist;
  const qp = watchlist?.query_params || {};
  const [label, setLabel] = useState(watchlist?.label || "");
  const [keywords, setKeywords] = useState(qp.keywords || []);
  const [orKeywords, setOrKeywords] = useState(qp.or_keywords || []);
  const [excludeKeywords, setExcludeKeywords] = useState(qp.exclude_keywords || []);
  const [includeSites, setIncludeSites] = useState(qp.include_sites || []);
  const [excludeSites, setExcludeSites] = useState(qp.exclude_sites || []);
  const [category, setCategory] = useState(watchlist?.category || "Exec Watch");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState("");

  // Rebuild the dork query preview string every time any tag field changes
  useEffect(() => {
    const parts = [];
    keywords.forEach(k => parts.push(`"${k}"`));
    if (orKeywords.length) parts.push(`(${orKeywords.map(k => `"${k}"`).join(" OR ")})`);
    excludeKeywords.forEach(k => parts.push(`-"${k}"`));
    if (includeSites.length) parts.push(`(${includeSites.map(s => `site:${s}`).join(" OR ")})`);
    excludeSites.forEach(s => parts.push(`-site:${s}`));
    setPreview(parts.join(" ") || "");
  }, [keywords, orKeywords, excludeKeywords, includeSites, excludeSites]);

  async function handleSubmit() {
    if (keywords.length === 0 && includeSites.length === 0) {
      setError("At least one of: keywords or include sites is required.");
      return;
    }
    setLoading(true);
    setError("");
    const body = {
      label: label.trim() || undefined,
      keywords: keywords.length ? keywords : undefined,
      or_keywords: orKeywords.length ? orKeywords : undefined,
      exclude_keywords: excludeKeywords.length ? excludeKeywords : undefined,
      include_sites: includeSites.length ? includeSites : undefined,
      exclude_sites: excludeSites.length ? excludeSites : undefined,
      category,
    };
    try {
      const url = isEdit ? `${API_BASE}/watchlist/${watchlist.id}` : `${API_BASE}/watchlist`;
      const method = isEdit ? "PUT" : "POST";
      const res = await authFetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail || "Failed"); }
      onSaved();
      onClose();
    } catch (e) {
      setError(e.message || "Failed. Check your connection.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200 }} onClick={onClose}>
      <div style={{ background: "#13131c", border: "0.5px solid #2a2a38", borderRadius: 16, padding: "28px 28px 24px", width: 460, maxWidth: "90vw", maxHeight: "90vh", overflowY: "auto" }} onClick={e => e.stopPropagation()}>
        <h2 style={{ margin: "0 0 20px", fontSize: 17, fontWeight: 600, color: "#e8e6ff" }}>{isEdit ? "Edit watchlist" : "Add watchlist"}</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label style={{ fontSize: 12, color: "#666", display: "block", marginBottom: 6 }}>Label <span style={{ color: "#444" }}>(optional)</span></label>
            <input value={label} onChange={e => setLabel(e.target.value)} placeholder="e.g. Ransomware Threats" style={INPUT_STYLE} />
          </div>
          <div style={{ borderTop: "0.5px solid #1e1e2e", paddingTop: 14 }}>
            <p style={{ margin: "0 0 12px", fontSize: 11, color: "#555", letterSpacing: "0.04em" }}>QUERY PARAMETERS</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <TagInput label="Keywords" placeholder="e.g. ransomware, data breach" values={keywords} onChange={setKeywords} />
              <TagInput label='OR keywords — any of these must appear  e.g. "lawsuit" OR "address"' placeholder="e.g. lawsuit, fraud, indictment" values={orKeywords} onChange={setOrKeywords} />
              <TagInput label="Exclude keywords" placeholder="e.g. press release, sponsored" values={excludeKeywords} onChange={setExcludeKeywords} />
              <TagInput label="Include sites" placeholder="e.g. sec.gov, reuters.com" values={includeSites} onChange={setIncludeSites} />
              <TagInput label="Exclude sites" placeholder="e.g. instagram.com, linkedin.com" values={excludeSites} onChange={setExcludeSites} />
            </div>
          </div>
          {/* Live dork query preview — shows exactly what will be sent to SerpAPI */}
          {preview && (
            <div style={{ background: "#0a0a12", border: "0.5px solid #2a2a38", borderRadius: 8, padding: "10px 12px" }}>
              <p style={{ margin: "0 0 4px", fontSize: 10, color: "#444", letterSpacing: "0.04em" }}>QUERY PREVIEW</p>
              <p style={{ margin: 0, fontSize: 11, color: "#7F77DD", fontFamily: "monospace", wordBreak: "break-all" }}>{preview}</p>
            </div>
          )}
          <div>
            <label style={{ fontSize: 12, color: "#666", display: "block", marginBottom: 6 }}>Category</label>
            <select value={category} onChange={e => setCategory(e.target.value)} style={INPUT_STYLE}>
              {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          {error && <p style={{ margin: 0, fontSize: 12, color: "#D85A30" }}>{error}</p>}
          <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
            <button onClick={onClose} style={{ flex: 1, padding: "9px", borderRadius: 8, border: "0.5px solid #2a2a38", background: "transparent", color: "#666", fontSize: 13, cursor: "pointer" }}>Cancel</button>
            <button onClick={handleSubmit} disabled={loading} style={{ flex: 1, padding: "9px", borderRadius: 8, border: "none", background: "#7F77DD", color: "#fff", fontSize: 13, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.6 : 1 }}>
              {loading ? "Saving..." : isEdit ? "Save changes" : "Add watchlist"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Component: ConfirmRunModal ───────────────────────────────────────────────
// Simple confirmation dialog shown before triggering POST /run-now.
// Prevents accidental full runs which consume SerpAPI quota.
function ConfirmRunModal({ onConfirm, onClose }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 300 }} onClick={onClose}>
      <div style={{ background: "#13131c", border: "0.5px solid #2a2a38", borderRadius: 16, padding: "28px 28px 24px", width: 380, maxWidth: "90vw" }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
          <span style={{ fontSize: 22, lineHeight: 1 }}>⚡</span>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "#e8e6ff" }}>Run all watchlists now?</h2>
        </div>
        <p style={{ margin: "0 0 24px", fontSize: 12, color: "#666", lineHeight: 1.6 }}>
          This will immediately fetch new alerts for every watchlist and refresh the board. It may take a moment to complete.
        </p>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={onClose} style={{ flex: 1, padding: "9px", borderRadius: 8, border: "0.5px solid #2a2a38", background: "transparent", color: "#666", fontSize: 13, cursor: "pointer" }}>Cancel</button>
          <button onClick={onConfirm} style={{ flex: 1, padding: "9px", borderRadius: 8, border: "none", background: "#7F77DD", color: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>Run now</button>
        </div>
      </div>
    </div>
  );
}

// ─── Component: ManageWatchlistsModal ─────────────────────────────────────────
// Modal opened from the "edit" button in a Column header.
// Lists all watchlists belonging to that category with Edit and Delete buttons.
// Delete uses a two-step confirmation (click Delete → click Confirm) to prevent accidents.
// Clicking Edit swaps this modal out for WatchlistFormModal in edit mode.
function ManageWatchlistsModal({ category, watchlists, onClose, onSaved }) {
  const [editingWatchlist, setEditingWatchlist] = useState(null);
  const accent = CATEGORY_COLORS[category];
  const filtered = watchlists.filter(w => (w.category || "Custom") === category);
  const [confirmingId, setConfirmingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null)

  async function handleDelete(id) {
    setDeletingId(id);
    try {
      const res = await authFetch(`${API_BASE}/watchlist/${id}`, {method: "DELETE"});
      if (!res.ok) throw new Error("Failed to delete");
      onSaved();
    }
    catch (e) {
      console.error("Failed to delete watchlist");
      setDeletingId(null);
      setConfirmingId(null);
    }
  }

  // If editing, swap the whole modal for the edit form
  if (editingWatchlist) {
    return <WatchlistFormModal watchlist={editingWatchlist} onClose={() => setEditingWatchlist(null)} onSaved={() => { setEditingWatchlist(null); onSaved(); }} />;
  }

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }} onClick={onClose}>
      <div style={{ background: "#13131c", border: "0.5px solid #2a2a38", borderRadius: 16, padding: "28px 28px 24px", width: 460, maxWidth: "90vw", maxHeight: "80vh", overflowY: "auto" }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: accent, boxShadow: `0 0 6px ${accent}88`, flexShrink: 0 }} />
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 600, color: "#e8e6ff" }}>{category}</h2>
          <span style={{ marginLeft: "auto", fontSize: 11, color: accent, background: `${accent}22`, padding: "2px 8px", borderRadius: 20, fontWeight: 600 }}>{filtered.length} watchlists</span>
        </div>
        {filtered.length === 0 ? (
          <p style={{ color: "#444", fontSize: 13, textAlign: "center", padding: "20px 0" }}>No watchlists in this category.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {filtered.map(w => (
              <div key={w.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "#0f0f16", border: "0.5px solid #2a2a38", borderRadius: 8, padding: "10px 14px" }}>
                <div>
                  <p style={{ margin: 0, fontSize: 13, color: "#e8e6ff", fontWeight: 500 }}>{w.label}</p>
                  {/* Show excluded sites as a hint so you can see the query at a glance */}
                  {w.query_params?.exclude_sites?.length > 0 && (
                    <p style={{ margin: "3px 0 0", fontSize: 11, color: "#555" }}>excl. {w.query_params.exclude_sites.join(", ")}</p>
                  )}
                </div>
                  <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                    {/* Two-step delete: first click shows Confirm/Cancel, second click calls DELETE */}
                    {confirmingId === w.id ? (
                      <>
                        <button onClick={() => handleDelete(w.id)} disabled={deletingId === w.id}
  style={{ background: "#D85A30", border: "none", borderRadius: 6, padding: "5px 12px", color:
  "#fff", fontSize: 11, fontWeight: 600, cursor: "pointer", opacity: deletingId === w.id ? 0.6 :
  1 }}>
                          {deletingId === w.id ? "Deleting..." : "Confirm"}
                        </button>
                        <button onClick={() => setConfirmingId(null)} disabled={deletingId ===
  w.id} style={{ background: "transparent", border: "0.5px solid #2a2a38", borderRadius: 6,
  padding: "5px 12px", color: "#666", fontSize: 11, cursor: "pointer" }}>
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => { setConfirmingId(null); setEditingWatchlist(w);
  }} style={{ background: "transparent", border: "0.5px solid #2a2a38", borderRadius: 6, padding:
  "5px 12px", color: "#7F77DD", fontSize: 11, cursor: "pointer" }}>
                          Edit
                        </button>
                        <button onClick={() => setConfirmingId(w.id)} style={{ background:
  "transparent", border: "0.5px solid #2a2a38", borderRadius: 6, padding: "5px 12px", color:
  "#D85A30", fontSize: 11, cursor: "pointer" }}>
                          Delete
                        </button>
                      </>
                    )}
                  </div>
              </div>
            ))}
          </div>
        )}
        <button onClick={onClose} style={{ width: "100%", marginTop: 16, padding: "9px", borderRadius: 8, border: "0.5px solid #2a2a38", background: "transparent", color: "#666", fontSize: 13, cursor: "pointer" }}>Close</button>
      </div>
    </div>
  );
}

// ─── Component: Column ────────────────────────────────────────────────────────
// One vertical Kanban column for a single category.
// Header shows the category name, alert count badge, and an "edit" button
// that opens ManageWatchlistsModal for that category.
// Body scrolls independently and renders an AlertCard for each alert.
function Column({ category, alerts, watchlists, loading, onWatchlistSaved, onOpenAlerts, onOpenSummaries }) {
  const accent = CATEGORY_COLORS[category];
  const bg = CATEGORY_BG[category];
  const [showManage, setShowManage] = useState(false);

  return (
    <div style={{ flex: "1 1 0", minHeight: 0, minWidth: 0, display: "flex", flexDirection: "column", background: "#0f0f16", border: "0.5px solid #1e1e2e", borderRadius: "14px", overflow: "hidden", overflowY: "auto"}}>
      {showManage && (
        <ManageWatchlistsModal category={category} watchlists={watchlists} onClose={() => setShowManage(false)} onSaved={() => { setShowManage(false); onWatchlistSaved(); }} />
      )}
      {/* Sticky column header — click anywhere on the bar to open this category's summaries */}
      <div onClick={() => onOpenSummaries(category)} style={{ padding: "14px 18px", borderBottom: "0.5px solid #1e1e2e", background: bg, display: "flex", alignItems: "center", gap: 10, position: "sticky", top: 0, zIndex: 1, cursor: "pointer" }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: accent, flexShrink: 0, boxShadow: `0 0 6px ${accent}88` }} />
        <span style={{ fontSize: "13px", fontWeight: 600, color: "#e8e6ff", letterSpacing: "0.03em" }}>{category}</span>
        <span style={{ marginLeft: "auto", fontSize: "11px", fontWeight: 600, color: accent, background: `${accent}22`, padding: "2px 8px", borderRadius: 20 }}>{alerts.length}</span>
        <button onClick={(e) => { e.stopPropagation(); setShowManage(true); }} title="Manage watchlists" style={{ background: "transparent", border: "none", cursor: "pointer", color: "#555", padding: "2px 4px", fontSize: 13, lineHeight: 1, borderRadius: 4 }}
          onMouseEnter={e => e.target.style.color = accent}
          onMouseLeave={e => e.target.style.color = "#555"}>
          edit
        </button>
      </div>
      {/* Scrollable card list */}
      <div style={{ padding: "12px", overflowY: "auto", flex: 1 }}>
        {loading ? (
          <div style={{ color: "#444", fontSize: "12px", textAlign: "center", paddingTop: 24 }}>Loading...</div>
        ) : alerts.length === 0 ? (
          <div style={{ color: "#333", fontSize: "12px", textAlign: "center", paddingTop: 24 }}>No alerts</div>
        ) : (
          alerts.map(a => <AlertCard key={a.id} alert={a} onOpenAlerts={onOpenAlerts} />)
        )}
      </div>
    </div>
  );
}

// ─── Component: AuthPage ──────────────────────────────────────────────────────
// Full-screen login / register screen shown when no JWT is in localStorage.
// On successful login, stores the JWT and email in localStorage and calls onLogin()
// to swap the app into the main dashboard view.
// On register success, switches back to login mode with a success message.
function AuthPage({ onLogin }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit() {
    setError("");
    setLoading(true);
    const endpoint = isLogin ? "/auth/login" : "/auth/register";
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Something went wrong");
      if (isLogin) {
        localStorage.setItem("token", data.token);
        localStorage.setItem("userEmail", data.email);
        onLogin(data.email);
      } else {
        setIsLogin(true);
        setError("Account created — please log in.");
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a12", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'IBM Plex Mono', 'Courier New', monospace" }}>
      <div style={{ background: "#13131c", border: "0.5px solid #2a2a38", borderRadius: 16, padding: "36px 32px", width: 380, maxWidth: "90vw" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 28 }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="3" fill="#7F77DD" />
            <circle cx="12" cy="12" r="7" stroke="#7F77DD" strokeWidth="1" strokeDasharray="2 2" fill="none" opacity="0.5" />
            <circle cx="12" cy="12" r="11" stroke="#7F77DD" strokeWidth="0.5" fill="none" opacity="0.25" />
          </svg>
          <span style={{ fontSize: 14, fontWeight: 700, color: "#e8e6ff", letterSpacing: "0.05em" }}>
            INDEX<span style={{ color: "#7F77DD" }}>PULSE</span>
          </span>
        </div>
        <h2 style={{ margin: "0 0 20px", fontSize: 16, fontWeight: 600, color: "#e8e6ff" }}>
          {isLogin ? "Sign in" : "Create account"}
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" type="email" style={INPUT_STYLE} />
          {/* Enter key submits the form from the password field */}
          <input value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" type="password" style={INPUT_STYLE}
            onKeyDown={e => e.key === "Enter" && handleSubmit()} />
          {/* Error text is green for "account created" messages, red for actual errors */}
          {error && <p style={{ margin: 0, fontSize: 12, color: error.includes("created") ? "#1D9E75" : "#D85A30" }}>{error}</p>}
          <button onClick={handleSubmit} disabled={loading} style={{ padding: "10px", borderRadius: 8, border: "none", background: "#7F77DD", color: "#fff", fontSize: 13, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.6 : 1, marginTop: 4 }}>
            {loading ? "..." : isLogin ? "Sign in" : "Create account"}
          </button>
          <p style={{ margin: 0, fontSize: 11, color: "#555", textAlign: "center" }}>
            {isLogin ? "No account?" : "Already have an account?"}{" "}
            <span onClick={() => { setIsLogin(!isLogin); setError(""); }} style={{ color: "#7F77DD", cursor: "pointer" }}>
              {isLogin ? "Sign up" : "Sign in"}
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Component: AlertPanel ────────────────────────────────────────────────────
// Slide-in drawer from the right that shows full details for a clicked alert.
// Highlights keyword matches in the title and snippet.
// Shows a "Why it was hit" section with the reconstructed dork query.
// Clicking the backdrop closes the panel.
function AlertPanel({ alert, onClose }) {
  const accent = CATEGORY_COLORS[alert.category] || CATEGORY_COLORS["Custom"];
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", display: "flex", justifyContent: "flex-end", zIndex: 400 }}>
      <div onClick={e => e.stopPropagation()} style={{ width: 440, maxWidth: "90vw", height: "100vh", background: "#13131c", borderLeft: "0.5px solid #2a2a38", padding: "24px 28px", overflowY: "auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18 }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: accent, background: `${accent}22`, padding: "3px 10px", borderRadius: 20 }}>{alert.category}</span>
          <button onClick={onClose} style={{ marginLeft: "auto", background: "transparent", border: "none", color: "#666", fontSize: 18, cursor: "pointer", lineHeight: 1 }}>✕</button>
        </div>

        {/* Full title as a clickable link with keyword highlights */}
        <a href={alert.link} target="_blank" rel="noopener noreferrer" style={{ color: "#e8e6ff", fontSize: 16, fontWeight: 600, textDecoration: "none", lineHeight: 1.4, display: "block", marginBottom: 12 }}>
          {highlightMatches(alert.title || "Untitled", alert.query_params?.keywords)}
        </a>

        {/* Full snippet (not clamped here) with keyword highlights */}
        {alert.snippet && (
          <p style={{ color: "#aaa", fontSize: 13, lineHeight: 1.6, marginBottom: 18 }}>{highlightMatches(alert.snippet, alert.query_params?.keywords)}</p>
        )}

        {/* Metadata row: source domain, watchlist label, time ago */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", fontSize: 11, color: "#666", marginBottom: 18 }}>
          {alert.source && <span>{alert.source}</span>}
          <span>· {alert.label || "Unnamed Watchlist"}</span>
          <span>· {timeAgo(alert.fetched_at)}</span>
        </div>

        {/* "Why it was hit" — shows the dork query that surfaced this result */}
        {buildQueryPreview(alert.query_params) && (
          <div style={{ borderTop: "0.5px solid #1e1e2e", paddingTop: 16 }}>
            <p style={{ margin: "0 0 8px", fontSize: 10, color: "#555", letterSpacing: "0.06em" }}>WHY IT WAS HIT</p>
            <p style={{ margin: "0 0 10px", fontSize: 12, color: "#888", lineHeight: 1.5 }}>
              Surfaced by watchlist <span style={{ color: "#e8e6ff" }}>{alert.label || "Unnamed Watchlist"}</span>. Its query matched this result:
            </p>
            <div style={{ background: "#0a0a12", border: "0.5px solid #2a2a38", borderRadius: 8, padding: "10px 12px" }}>
              <p style={{ margin: "0 0 4px", fontSize: 10, color: "#444", letterSpacing: "0.04em" }}>QUERY</p>
              <p style={{ margin: 0, fontSize: 11, color: "#7F77DD", fontFamily: "monospace", wordBreak: "break-all" }}>{buildQueryPreview(alert.query_params)}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


// ─── Component: SummaryPanel ──────────────────────────────────────────────────
// Right-side slide-out (mirrors AlertPanel) opened by clicking a category header.
// Shows every watchlist in that category with its daily digest + running dossier.
function SummaryPanel({ category, digests, dossiers, onClose }) {
  const accent = CATEGORY_COLORS[category] || CATEGORY_COLORS["Custom"];

  // Narrow both artifact lists to the clicked category.
  const catDigests = digests.filter(d => (d.category || "Custom") === category);
  const catDossiers = dossiers.filter(d => (d.category || "Custom") === category);

  // Collect every watchlist that has either a digest or a dossier in this category,
  // so a watchlist shows up if it has been summarized at all.
  const byId = {};
  for (const d of catDigests) byId[d.watchlist_id] = { label: d.label, digest: d, dossier: null };
  for (const d of catDossiers) {
    byId[d.watchlist_id] = { ...(byId[d.watchlist_id] || { label: d.label }), dossier: d };
  }
  const watchlistSummaries = Object.values(byId);

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 400 }}>
      <div onClick={e => e.stopPropagation()} style={{ width: "90vw", maxWidth: 1100, maxHeight: "85vh", background: "#13131c", border: "0.5px solid #2a2a38", borderRadius: 16, padding: "24px 28px", display: "flex", flexDirection: "column" }}>
        {/* Header: category badge + close */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20, flexShrink: 0 }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: accent, background: `${accent}22`, padding: "3px 10px", borderRadius: 20 }}>{category}</span>
          <span style={{ fontSize: 11, color: "#555" }}>Summaries</span>
          <button onClick={onClose} style={{ marginLeft: "auto", background: "transparent", border: "none", color: "#666", fontSize: 18, cursor: "pointer", lineHeight: 1 }}>✕</button>
        </div>

        {watchlistSummaries.length === 0 ? (
          <p style={{ color: "#444", fontSize: 13, textAlign: "center", paddingTop: 32 }}>No summaries yet for this category.</p>
        ) : (
          /* One column per watchlist, laid out horizontally; scrolls sideways if they overflow */
          <div style={{ display: "flex", gap: 16, overflowX: "auto", flex: 1, minHeight: 0, alignItems: "stretch" }}>
            {watchlistSummaries.map(({ label, digest, dossier }, i) => (
              <div key={i} style={{ flex: "0 0 320px", display: "flex", flexDirection: "column", minHeight: 0, background: "#0f0f16", border: "0.5px solid #1e1e2e", borderRadius: 12, padding: "14px 16px" }}>
                {/* Watchlist label */}
                <p style={{ margin: "0 0 10px", fontSize: 14, fontWeight: 600, color: "#e8e6ff", flexShrink: 0 }}>{label || "Unnamed Watchlist"}</p>

                {/* Column body scrolls on its own so all columns stay the same height */}
                <div style={{ overflowY: "auto", flex: 1, minHeight: 0 }}>
                  {/* Daily digest */}
                  {digest && (
                    <div style={{ background: "#18181f", border: "0.5px solid #2a2a38", borderRadius: 10, padding: "14px 16px", marginBottom: 12 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                        <span style={{ fontSize: 10, fontWeight: 700, color: "#888", background: "#2a2a38", padding: "2px 8px", borderRadius: 20, textTransform: "uppercase", letterSpacing: "0.05em" }}>{digest.severity}</span>
                        <span style={{ fontSize: 10, color: "#555" }}>{timeAgo(digest.generated_at)}</span>
                      </div>
                      <p style={{ margin: "0 0 6px", fontSize: 13, fontWeight: 600, color: "#e8e6ff", lineHeight: 1.4 }}>{digest.headline}</p>
                      <p style={{ margin: 0, fontSize: 12, color: "#aaa", lineHeight: 1.6 }}>{digest.narrative}</p>
                    </div>
                  )}

                  {/* Running dossier */}
                  {dossier && (
                    <div style={{ borderTop: "0.5px solid #1e1e2e", paddingTop: 12 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                        <span style={{ fontSize: 10, color: "#555", letterSpacing: "0.06em" }}>DOSSIER</span>
                        <span style={{ fontSize: 10, color: "#555" }}>updated {timeAgo(dossier.updated_at)}</span>
                      </div>
                      <p style={{ margin: 0, fontSize: 12, color: "#999", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{dossier.summary}</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


// ─── Component: App (root) ────────────────────────────────────────────────────
// Top-level component. Manages global state and orchestrates the whole dashboard.
//
// State:
//   alerts        — all unread results fetched from GET /alerts
//   watchlists    — all saved monitors from GET /watchlists
//   selectedAlert — the alert currently open in AlertPanel (null = closed)
//   currentUser   — email from localStorage; null means the user is logged out
//   showAddModal  — controls WatchlistFormModal visibility
//   showRunConfirm— controls ConfirmRunModal visibility
//   runningNow    — true while POST /run-now is in flight (disables button)
//   status        — short status message shown in the header during a run
//
// Data flow:
//   fetchData() → sets alerts + watchlists → passed down to Column → AlertCard
//   openAlert()  → sets selectedAlert + PATCHes the alert as read
//   runNow()     → POST /run-now → then fetchData() to refresh
export default function App() {
  const [alerts, setAlerts] = useState([]);
  const [selectedAlert, setSelectedAlerts] = useState(null);
  const [watchlists, setWatchlists] = useState([]);
  const [digests, setDigests] = useState([]);
  const [dossiers, setDossiers] = useState([]);
  const [openCategory, setOpenCategory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showRunConfirm, setShowRunConfirm] = useState(false);
  const [runningNow, setRunningNow] = useState(false);
  const [status, setStatus] = useState("");

  // currentUser is seeded from localStorage so the session survives a page reload
  const [currentUser, setCurrentUser] = useState(() => localStorage.getItem("userEmail"));

  function handleLogout() {
    localStorage.removeItem("token");
    localStorage.removeItem("userEmail");
    setCurrentUser(null);
  }

  // Listens for the "auth:expired" event dispatched by authFetch on a 401,
  // so any expired/invalid token anywhere in the app drops back to the login screen
  useEffect(() => {
    function handleExpired() { setCurrentUser(null); }
    window.addEventListener("auth:expired", handleExpired);
    return () => window.removeEventListener("auth:expired", handleExpired);
  }, []);

  // Proactively logs the user out once their JWT's exp claim is reached,
  // rather than waiting for the next authFetch call to hit a 401
  useEffect(() => {
    if (!currentUser) return;
    const token = localStorage.getItem("token");
    if (!token) return;
    const expiryMs = getTokenExpiryMs(token);
    if (!expiryMs) return;
    const msLeft = expiryMs - Date.now();
    if (msLeft <= 0) {
      handleLogout();
      return;
    }
    const timer = setTimeout(handleLogout, msLeft);
    return () => clearTimeout(timer);
  }, [currentUser]);

  // Fetch alerts and watchlists in parallel; wrapped in useCallback so it's
  // stable across renders and can be passed as onSaved/onWatchlistSaved prop
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [alertsRes, watchlistsRes, digestsRes, dossiersRes] = await Promise.all([
        authFetch(`${API_BASE}/alerts`),
        authFetch(`${API_BASE}/watchlists`),
        authFetch(`${API_BASE}/digests`),
        authFetch(`${API_BASE}/dossiers`),
      ]);
      if (alertsRes.ok) setAlerts(await alertsRes.json());
      if (watchlistsRes.ok) setWatchlists(await watchlistsRes.json());
      if (digestsRes.ok) setDigests(await digestsRes.json());
      if (dossiersRes.ok) setDossiers(await dossiersRes.json());
      setLastRefresh(new Date());
    } catch (e) {
      console.error("Failed to fetch data", e);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load data once logged in, and again immediately after a fresh login
  useEffect(() => {
    if (!currentUser) return;
    fetchData();
  }, [currentUser, fetchData]);

  // Triggers an immediate run of all watchlists on the server, then refreshes
  async function runNow() {
    setShowRunConfirm(false);
    setRunningNow(true);
    setStatus("Running all watchlists...");
    try {
      await authFetch(`${API_BASE}/run-now`, { method: "POST" });
      setStatus("Done. Refreshing...");
      await fetchData();
      setStatus("");
    } catch {
      setStatus("Error triggering run.");
    } finally {
      setRunningNow(false);
    }
  }

  // Opens the AlertPanel for the clicked alert and marks it as read via PATCH
  async function openAlert(alert) {
    setSelectedAlerts(alert);
    if (!alert.is_read) {
      await authFetch(`${API_BASE}/alerts/${alert.id}/read`, { method: "PATCH" });
      setAlerts(prev => prev.map(a => a.id === alert.id ? {...a, is_read: true} : a));
    }
  }

  // Gate: show AuthPage if no logged-in user, otherwise show the dashboard
  if (!currentUser) {
    return <AuthPage onLogin={(email) => setCurrentUser(email)} />;
  }

  return (
    <div style={{ height: "100vh", background: "#0a0a12", fontFamily: "'IBM Plex Mono', 'Courier New', monospace", display: "flex", flexDirection: "column" }}>
      {/* Global modals — rendered at the top level so they sit above everything */}
      {showAddModal && <WatchlistFormModal onClose={() => setShowAddModal(false)} onSaved={fetchData} />}
      {showRunConfirm && <ConfirmRunModal onConfirm={runNow} onClose={() => setShowRunConfirm(false)} />}
      {selectedAlert && <AlertPanel alert={selectedAlert} onClose={() => setSelectedAlerts(null)} />}
      {openCategory && <SummaryPanel category={openCategory} digests={digests} dossiers={dossiers} onClose={() => setOpenCategory(null)} />}

      {/* ── Sticky top nav bar ── */}
      <div style={{ padding: "16px 28px", borderBottom: "0.5px solid #1a1a28", display: "flex", alignItems: "center", gap: 16, background: "#0a0a12", position: "sticky", top: 0, zIndex: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="3" fill="#7F77DD" />
            <circle cx="12" cy="12" r="7" stroke="#7F77DD" strokeWidth="1" strokeDasharray="2 2" fill="none" opacity="0.5" />
            <circle cx="12" cy="12" r="11" stroke="#7F77DD" strokeWidth="0.5" fill="none" opacity="0.25" />
          </svg>
          <span style={{ fontSize: 15, fontWeight: 700, color: "#e8e6ff", letterSpacing: "0.05em" }}>
            INDEX<span style={{ color: "#7F77DD" }}>PULSE</span>
          </span>
          <span style={{ position: "fixed", top: "4px", left: "4px", color: "#666", fontSize: "12px" }}>
                 v{version}
         </span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
          {status && <span style={{ fontSize: 11, color: "#7F77DD" }}>{status}</span>}
          {lastRefresh && <span style={{ fontSize: 11, color: "#444" }}>refreshed {timeAgo(lastRefresh)}</span>}
          <span style={{ fontSize: 11, color: "#555" }}>{watchlists.length} watchlists · {alerts.length} alerts</span>
          <span style={{ fontSize: 11, color: "#555" }}>{currentUser}</span>
          <button onClick={handleLogout} style={{ background: "transparent", border: "0.5px solid #2a2a38", borderRadius: 8, padding: "6px 12px", color: "#888", fontSize: 11, cursor: "pointer" }}>Sign out</button>
          <button onClick={fetchData} style={{ background: "transparent", border: "0.5px solid #2a2a38", borderRadius: 8, padding: "6px 12px", color: "#888", fontSize: 11, cursor: "pointer" }}>↻ Refresh</button>
          <button onClick={() => setShowRunConfirm(true)} disabled={runningNow} style={{ background: "transparent", border: "0.5px solid #7F77DD44", borderRadius: 8, padding: "6px 12px", color: "#7F77DD", fontSize: 11, cursor: runningNow ? "not-allowed" : "pointer", opacity: runningNow ? 0.5 : 1 }}> Run now</button>
          <button onClick={() => setShowAddModal(true)} style={{ background: "#7F77DD", border: "none", borderRadius: 8, padding: "6px 14px", color: "#fff", fontSize: 11, fontWeight: 700, cursor: "pointer" }}>+ Add watchlist</button>
        </div>
      </div>

      {/* ── Kanban board: one Column per category ── */}
      <div style={{ flex: 1, display: "flex", gap: 14, padding: "18px 24px", overflowX: "auto", alignItems: "stretch" }}>
        {CATEGORIES.map(cat => (
          <Column
            key={cat}
            category={cat}
            alerts={alerts.filter(a => (a.category || "Custom") === cat)}
            watchlists={watchlists}
            loading={loading}
            onWatchlistSaved={fetchData}
            onOpenAlerts={openAlert}
            onOpenSummaries={setOpenCategory}
          />
        ))}
      </div>
    </div>
  );
}
