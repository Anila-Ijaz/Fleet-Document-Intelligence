import { useEffect, useState } from "react";
import { listDocuments, reindexAll, deleteDocument } from "../api/client";

export default function DocumentList({ refreshKey }) {
  const [docs, setDocs] = useState([]);
  const [indexing, setIndexing] = useState(false);
  const [status, setStatus] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  async function load() {
    try {
      setDocs(await listDocuments());
    } catch {
      /* service may still be starting */
    }
  }

  useEffect(() => {
    load();
  }, [refreshKey]);

  async function handleReindex() {
    setIndexing(true);
    setStatus("Indexiere Dokumente für die Suche…");
    try {
      const r = await reindexAll();
      setStatus(`${r.indexed_documents} Dokumente, ${r.indexed_chunks} Abschnitte indexiert.`);
    } catch (e) {
      setStatus(`Fehler: ${e.message}`);
    } finally {
      setIndexing(false);
    }
  }

  async function handleDelete(doc) {
    if (!window.confirm(`"${doc.filename}" löschen?`)) return;
    setDeletingId(doc.id);
    try {
      await deleteDocument(doc.id);
      setDocs((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (e) {
      setStatus(`Fehler beim Löschen: ${e.message}`);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="panel">
      <h2>Dokumente</h2>
      {docs.length === 0 && <p className="status">Noch keine Dokumente.</p>}
      {docs.map((d) => (
        <div className="doc-row" key={d.id}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="fn">{d.filename}</div>
            <div className="sub">
              {d.supplier_name || "—"}
              {d.gross_amount ? ` · ${d.gross_amount.toFixed(2)} EUR` : ""}
              {d.vehicle_make ? ` · ${d.vehicle_make}` : ""}
            </div>
          </div>
          <span className="badge">{d.document_type}</span>
          <span className={`badge ${d.needs_review ? "review" : "ok"}`}>
            {d.needs_review ? "Prüfen" : "OK"}
          </span>
          <button
            onClick={() => handleDelete(d)}
            disabled={deletingId === d.id}
            title="Dokument löschen"
            style={{
              background: "transparent",
              border: "1px solid #444",
              color: "#e05",
              borderRadius: 3,
              cursor: "pointer",
              padding: "2px 6px",
              fontSize: 13,
              lineHeight: 1,
              minWidth: "unset",
              width: 24,
              height: 22,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              opacity: deletingId === d.id ? 0.4 : 1,
            }}
          >
            ×
          </button>
        </div>
      ))}
      <div style={{ marginTop: 18 }}>
        <button className="ghost" onClick={handleReindex} disabled={indexing}>
          {indexing ? "Indexiere…" : "Für Chat indexieren"}
        </button>
        {status && <div className="status">{status}</div>}
      </div>
    </div>
  );
}
