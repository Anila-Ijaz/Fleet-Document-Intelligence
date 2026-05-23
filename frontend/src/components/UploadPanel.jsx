import { useRef, useState } from "react";
import { uploadDocument } from "../api/client";

export default function UploadPanel({ onUploaded }) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  async function handleFile(file) {
    if (!file) return;
    setError(null);
    setStatus(`Verarbeite ${file.name}…`);
    try {
      const result = await uploadDocument(file);
      const t = result.fields.document_type;
      setStatus(
        `Extrahiert: ${t}` +
          (result.needs_review ? " — markiert zur Prüfung" : " ✓")
      );
      onUploaded?.(result);
    } catch (e) {
      setError(e.message);
      setStatus(null);
    }
  }

  return (
    <div className="panel">
      <h2>Dokument hochladen</h2>
      <div
        className={`dropzone ${drag ? "drag" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          handleFile(e.dataTransfer.files?.[0]);
        }}
      >
        <p>Datei hierher ziehen oder klicken</p>
        <p className="hint">PDF · TXT · MD</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.md"
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>
      {status && <div className="status">{status}</div>}
      {error && <div className="status error">Fehler: {error}</div>}
    </div>
  );
}
