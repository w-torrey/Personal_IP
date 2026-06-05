import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://100.65.81.57:8000";

const CATEGORIES = ["Exec Watch", "Fraud", "Threat Intelligence", "Uncategorized"];

const CATEGORY_COLORS = {
  "Exec Watch": "#7F77DD",
  "Fraud": "#D85A30",
  "Threat Intelligence": "#1D9E75",
  "Uncategorized": "#888780",
};

const CATEGORY_BG = {
  "Exec Watch": "rgba(127,119,221,0.12)",
  "Fraud": "rgba(216,90,48,0.12)",
  "Threat Intelligence": "rgba(29,158,117,0.12)",
  "Uncategorized": "rgba(136,135,128,0.12)",
};

function timeAgo(dateStr) {
  if (!dateStr) return "Unknown";
  const date = new Date(dateStr);
  if (isNaN(date)) return dateStr;
  const diff = Math.floor((Date.now() - date) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function AlertCard({ alert }) {
  const cat = alert.category || "Uncategorized";
  const accent = CATEGORY_COLORS[cat] || CATEGORY_COLORS["Uncategorized"];
  return (
    <div style={{
      background: "#18181f",
      border: "0.5px solid #2a2a38",
      borderLeft: `3px solid ${accent}`,
      borderRadius: "10px",
      padding: "14px 16px",
      marginBottom: "10px",
      transition: "border-color 0.15s",
      cursor: "default",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
        <p style={{
          margin: 0,
          fontSize: "13px",
          fontWeight: 500,
          color: "#e8e6ff",
          lineHeight: 1.4,
          flex: 1,
        }}>
          {alert.link ? (
            <a href={alert.link} target="_blank" rel="noopener noreferrer" style={{ color: "#e8e6ff", textDecoration: "none" }}
              onMouseEnter={e => e.target.style.color = accent}
              onMouseLeave={e => e.target.style.color = "#e8e6ff"}>
              {alert.title || "Untitled"}
            </a>
          ) : (alert.title || "Untitled")}
        </p>
        {alert.link && (
          <a href={alert.link} target="_blank" rel="noopener noreferrer" style={{ color: "#555", flexShrink: 0, marginTop: 2 }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </a>
        )}
      </div>
      {alert.snippet && (
        <p style={{ margin: "8px 0 0", fontSize: "12px", color: "#888", lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {alert.snippet}
        </p>
      )}
      <div style={{ display: "flex", gap: 10, marginTop: 10, alignItems: "center" }}>
        {alert.source && (
          <span style={{ fontSize: "11px", color: "#666", fontWeight: 500 }}>{alert.source}</span>
        )}
        <span style={{ fontSize: "11px", color: "#444" }}>·</span>
        <span style={{ fontSize: "11px", color: "#555" }}>
          {alert.person && `${alert.person}`}{alert.organization && ` · ${alert.organization}`}
        </span>
        <span style={{ fontSize: "11px", color: "#444", marginLeft: "auto" }}>
          {timeAgo(alert.fetched_at)}
        </span>
      </div>
    </div>
  );
}

function Column({ category, alerts, loading }) {
  const accent = CATEGORY_COLORS[category];
  const bg = CATEGORY_BG[category];
  return (
    <div style={{
      flex: "1 1 0",
      minWidth: 0,
      display: "flex",
      flexDirection: "column",
      background: "#0f0f16",
      border: "0.5px solid #1e1e2e",
      borderRadius: "14px",
      overflow: "hidden",
    }}>
      <div style={{
        padding: "14px 18px",
        borderBottom: "0.5px solid #1e1e2e",
        background: bg,
        display: "flex",
        alignItems: "center",
        gap: 10,
        position: "sticky",
        top: 0,
        zIndex: 1,
      }}>
        <span style={{
          width: 8, height: 8, borderRadius: "50%",
          background: accent, flexShrink: 0,
          boxShadow: `0 0 6px ${accent}88`,
        }} />
        <span style={{ fontSize: "13px", fontWeight: 600, color: "#e8e6ff", letterSpacing: "0.03em" }}>
          {category}
        </span>
        <span style={{
          marginLeft: "auto", fontSize: "11px", fontWeight: 600,
          color: accent, background: `${accent}22`,
          padding: "2px 8px", borderRadius: 20,
        }}>
          {alerts.length}
        </span>
      </div>
      <div style={{ padding: "12px", overflowY: "auto", flex: 1 }}>
        {loading ? (
          <div style={{ color: "#444", fontSize: "12px", textAlign: "center", paddingTop: 24 }}>Loading...</div>
        ) : alerts.length === 0 ? (
          <div style={{ color: "#333", fontSize: "12px", textAlign: "center", paddingTop: 24 }}>No alerts</div>
        ) : (
          alerts.map(a => <AlertCard key={a.id} alert={a} />)
        )}
      </div>
    </div>
  );
}

function AddWatchlistModal({ onClose, onAdded }) {
  const [person, setPerson] = useState("");
  const [org, setOrg] = useState("");
  const [category, setCategory] = useState("Exec Watch");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit() {
    if (!person.trim() && !org.trim()) {
      setError("At least a person or organization is required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/watchlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ person: person.trim(), organization: org.trim(), category }),
      });
      if (!res.ok) throw new Error("Failed to create watchlist");
      const data = await res.json();
      onAdded(data);
      onClose();
    } catch (e) {
      setError("Failed to create watchlist. Check your connection.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100,
    }} onClick={onClose}>
      <div style={{
        background: "#13131c", border: "0.5px solid #2a2a38",
        borderRadius: 16, padding: "28px 28px 24px", width: 400, maxWidth: "90vw",
      }} onClick={e => e.stopPropagation()}>
        <h2 style={{ margin: "0 0 20px", fontSize: 17, fontWeight: 600, color: "#e8e6ff" }}>
          Add watchlist
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, color: "#666", display: "block", marginBottom: 6 }}>Person</label>
            <input
              value={person} onChange={e => setPerson(e.target.value)}
              placeholder="e.g. Ronald O'Hanley"
              style={{
                width: "100%", background: "#0f0f16", border: "0.5px solid #2a2a38",
                borderRadius: 8, padding: "9px 12px", color: "#e8e6ff",
                fontSize: 13, outline: "none", boxSizing: "border-box",
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "#666", display: "block", marginBottom: 6 }}>Organization</label>
            <input
              value={org} onChange={e => setOrg(e.target.value)}
              placeholder="e.g. State Street"
              style={{
                width: "100%", background: "#0f0f16", border: "0.5px solid #2a2a38",
                borderRadius: 8, padding: "9px 12px", color: "#e8e6ff",
                fontSize: 13, outline: "none", boxSizing: "border-box",
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "#666", display: "block", marginBottom: 6 }}>Category</label>
            <select
              value={category} onChange={e => setCategory(e.target.value)}
              style={{
                width: "100%", background: "#0f0f16", border: "0.5px solid #2a2a38",
                borderRadius: 8, padding: "9px 12px", color: "#e8e6ff",
                fontSize: 13, outline: "none", boxSizing: "border-box",
              }}
            >
              {CATEGORIES.filter(c => c !== "Uncategorized").map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          {error && <p style={{ margin: 0, fontSize: 12, color: "#D85A30" }}>{error}</p>}
          <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
            <button onClick={onClose} style={{
              flex: 1, padding: "9px", borderRadius: 8, border: "0.5px solid #2a2a38",
              background: "transparent", color: "#666", fontSize: 13, cursor: "pointer",
            }}>Cancel</button>
            <button onClick={handleSubmit} disabled={loading} style={{
              flex: 1, padding: "9px", borderRadius: 8, border: "none",
              background: "#7F77DD", color: "#fff", fontSize: 13, fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.6 : 1,
            }}>{loading ? "Adding..." : "Add watchlist"}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [alerts, setAlerts] = useState([]);
  const [watchlists, setWatchlists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [runningNow, setRunningNow] = useState(false);
  const [status, setStatus] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [alertsRes, watchlistsRes] = await Promise.all([
        fetch(`${API_BASE}/alerts`),
        fetch(`${API_BASE}/watchlists`),
      ]);
      const alertsData = await alertsRes.json();
      const watchlistsData = await watchlistsRes.json();
      setAlerts(alertsData);
      setWatchlists(watchlistsData);
      setLastRefresh(new Date());
    } catch (e) {
      console.error("Failed to fetch data", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  async function runNow() {
    setRunningNow(true);
    setStatus("Running all watchlists...");
    try {
      await fetch(`${API_BASE}/run-now`, { method: "POST" });
      setStatus("Done. Refreshing alerts...");
      await fetchData();
      setStatus("");
    } catch {
      setStatus("Error triggering run.");
    } finally {
      setRunningNow(false);
    }
  }

  function getAlertsForCategory(cat) {
    return alerts.filter(a => (a.category || "Uncategorized") === cat);
  }

  const totalAlerts = alerts.length;

  return (
    <div style={{
      minHeight: "100vh", background: "#0a0a12",
      fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
      display: "flex", flexDirection: "column",
    }}>
      {showModal && (
        <AddWatchlistModal
          onClose={() => setShowModal(false)}
          onAdded={() => fetchData()}
        />
      )}

      {/* Header */}
      <div style={{
        padding: "16px 28px",
        borderBottom: "0.5px solid #1a1a28",
        display: "flex", alignItems: "center", gap: 16,
        background: "#0a0a12",
        position: "sticky", top: 0, zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="3" fill="#7F77DD" />
            <circle cx="12" cy="12" r="7" stroke="#7F77DD" strokeWidth="1" strokeDasharray="2 2" fill="none" opacity="0.5" />
            <circle cx="12" cy="12" r="11" stroke="#7F77DD" strokeWidth="0.5" fill="none" opacity="0.25" />
          </svg>
          <span style={{ fontSize: 15, fontWeight: 700, color: "#e8e6ff", letterSpacing: "0.05em" }}>
            INDEX<span style={{ color: "#7F77DD" }}>PULSE</span>
          </span>
        </div>

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
          {status && (
            <span style={{ fontSize: 11, color: "#7F77DD" }}>{status}</span>
          )}
          {lastRefresh && (
            <span style={{ fontSize: 11, color: "#444" }}>
              refreshed {timeAgo(lastRefresh)}
            </span>
          )}
          <span style={{ fontSize: 11, color: "#555" }}>
            {watchlists.length} watchlists · {totalAlerts} alerts
          </span>
          <button onClick={fetchData} style={{
            background: "transparent", border: "0.5px solid #2a2a38",
            borderRadius: 8, padding: "6px 12px", color: "#888",
            fontSize: 11, cursor: "pointer", letterSpacing: "0.04em",
          }}>↻ Refresh</button>
          <button onClick={runNow} disabled={runningNow} style={{
            background: "transparent", border: "0.5px solid #7F77DD44",
            borderRadius: 8, padding: "6px 12px", color: "#7F77DD",
            fontSize: 11, cursor: runningNow ? "not-allowed" : "pointer",
            letterSpacing: "0.04em", opacity: runningNow ? 0.5 : 1,
          }}>⚡ Run now</button>
          <button onClick={() => setShowModal(true)} style={{
            background: "#7F77DD", border: "none",
            borderRadius: 8, padding: "6px 14px", color: "#fff",
            fontSize: 11, fontWeight: 700, cursor: "pointer", letterSpacing: "0.04em",
          }}>+ Add watchlist</button>
        </div>
      </div>

      {/* Columns */}
      <div style={{
        flex: 1, display: "flex", gap: 14, padding: "18px 24px",
        overflowX: "auto", alignItems: "stretch",
      }}>
        {CATEGORIES.map(cat => (
          <Column
            key={cat}
            category={cat}
            alerts={getAlertsForCategory(cat)}
            loading={loading}
          />
        ))}
      </div>
    </div>
  );
}
