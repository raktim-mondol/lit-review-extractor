import { useEffect, useState } from "react";

const POLL_MS = 2000;

function MetricCard({ label, value }) {
  return (
    <div className="card metric">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </div>
  );
}

function App() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [lastRefresh, setLastRefresh] = useState("");

  useEffect(() => {
    let active = true;

    const fetchStatus = async () => {
      try {
        const res = await fetch("/api/status");
        if (!res.ok) {
          throw new Error(`Status API failed (${res.status})`);
        }
        const data = await res.json();
        if (!active) return;
        setStatus(data);
        setError("");
        setLastRefresh(new Date().toLocaleTimeString());
      } catch (err) {
        if (!active) return;
        setError(err?.message || "Unknown error");
      }
    };

    fetchStatus();
    const timer = setInterval(fetchStatus, POLL_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const totals = status?.totals || {};
  const runtime = status?.runtime || {};
  const percent = Number(totals.progress_percent || 0);

  return (
    <main className="container">
      <header className="header card">
        <h1>Mission Control</h1>
        <p>Literature extractor live progress dashboard</p>
        <div className="muted">
          Refresh: every {POLL_MS / 1000}s{lastRefresh ? ` | Last: ${lastRefresh}` : ""}
        </div>
      </header>

      {error ? <div className="card error">API error: {error}</div> : null}

      <section className="metrics-grid">
        <MetricCard label="Total Papers" value={totals.total ?? "-"} />
        <MetricCard label="Completed" value={totals.completed ?? "-"} />
        <MetricCard label="Failed" value={totals.failed ?? "-"} />
        <MetricCard label="Pending" value={totals.pending ?? "-"} />
      </section>

      <section className="card">
        <div className="row-between">
          <h2>Progress</h2>
          <strong>{percent.toFixed(2)}%</strong>
        </div>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${Math.min(percent, 100)}%` }} />
        </div>
      </section>

      <section className="card">
        <h2>Current Activity</h2>
        <div className="stack">
          <div>
            <span className="label">State:</span> <span>{runtime.state || "idle"}</span>
          </div>
          <div>
            <span className="label">File:</span> <span>{runtime.current_file || "-"}</span>
          </div>
          <div>
            <span className="label">Serial:</span> <span>{runtime.current_serial || "-"}</span>
          </div>
          <div>
            <span className="label">Attempt:</span> <span>{runtime.attempt || "-"}</span>
          </div>
          <div>
            <span className="label">Message:</span> <span>{runtime.message || "-"}</span>
          </div>
          <div>
            <span className="label">Updated:</span> <span>{runtime.updated_at || "-"}</span>
          </div>
        </div>
      </section>

      <section className="two-col">
        <div className="card">
          <h2>Pending Files (preview)</h2>
          <ul className="list">
            {(status?.pending_files_preview || []).map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h2>Recent JSON Outputs</h2>
          <ul className="list">
            {(status?.recent_outputs || []).map((item) => (
              <li key={item.file}>
                <div>{item.file}</div>
                <div className="muted small">{item.modified_at}</div>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </main>
  );
}

export default App;
