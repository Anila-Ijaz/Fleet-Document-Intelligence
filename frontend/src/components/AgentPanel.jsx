import { useEffect, useState } from "react";
import { listNeedsReview, triageDocument } from "../api/client";

const ACTION_LABEL = {
  auto_approve: "Automatisch genehmigt",
  flag_for_review: "Zur Prüfung markiert",
  escalate: "Eskaliert",
};

const ACTION_CLASS = {
  auto_approve: "ok",
  flag_for_review: "review",
  escalate: "escalate",
};

export default function AgentPanel({ refreshKey }) {
  const [docs, setDocs] = useState([]);
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState({});

  useEffect(() => {
    listNeedsReview()
      .then(setDocs)
      .catch(() => {});
  }, [refreshKey]);

  async function handleTriage(docId) {
    setLoading((l) => ({ ...l, [docId]: true }));
    try {
      const result = await triageDocument(docId);
      setResults((r) => ({ ...r, [docId]: result }));
    } catch (e) {
      setResults((r) => ({ ...r, [docId]: { error: e.message } }));
    } finally {
      setLoading((l) => ({ ...l, [docId]: false }));
    }
  }

  return (
    <div className="panel">
      <h2>Prüfwarteschlange · Agent</h2>
      {docs.length === 0 && (
        <p className="status">Keine Dokumente zur Prüfung.</p>
      )}
      {docs.map((d) => {
        const result = results[d.id];
        const busy = loading[d.id];
        return (
          <div className="doc-row" key={d.id} style={{ flexDirection: "column", alignItems: "flex-start", gap: 8 }}>
            <div style={{ display: "flex", width: "100%", alignItems: "center", gap: 8 }}>
              <div style={{ flex: 1 }}>
                <div className="fn">{d.filename}</div>
                <div className="sub">
                  {d.supplier_name || "—"}
                  {d.gross_amount ? ` · ${d.gross_amount.toFixed(2)} EUR` : ""}
                </div>
              </div>
              <span className="badge">{d.document_type}</span>
              <button
                className="ghost"
                onClick={() => handleTriage(d.id)}
                disabled={busy}
                style={{ minWidth: 90 }}
              >
                {busy ? "Analysiere…" : "Triage"}
              </button>
            </div>

            {result && !result.error && (
              <div style={{ width: "100%", background: "var(--bg-panel, #f5f5f5)", borderRadius: 6, padding: "10px 12px", fontSize: 13 }}>
                <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                  <span className={`badge ${ACTION_CLASS[result.action] || ""}`}>
                    {ACTION_LABEL[result.action] || result.action}
                  </span>
                  <span className="badge">Risiko: {result.risk_level}</span>
                </div>
                {result.anomalies?.length > 0 && (
                  <div style={{ marginBottom: 6 }}>
                    <strong>Auffälligkeiten:</strong>
                    <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                      {result.anomalies.map((a, i) => <li key={i}>{a}</li>)}
                    </ul>
                  </div>
                )}
                {result.draft_reply && (
                  <div>
                    <strong>Interne Notiz:</strong>
                    <p style={{ margin: "4px 0 0", fontStyle: "italic" }}>{result.draft_reply}</p>
                  </div>
                )}
              </div>
            )}
            {result?.error && (
              <div className="status error">Fehler: {result.error}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}
