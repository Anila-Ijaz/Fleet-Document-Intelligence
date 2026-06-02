import { useState } from "react";
import { askQuestion } from "../api/client";

export default function ChatPanel() {
  const [log, setLog] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function send() {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setLog((l) => [...l, { role: "user", text: q }]);
    setLoading(true);
    try {
      const res = await askQuestion(q);
      setLog((l) => [...l, { role: "bot", text: res.answer, sources: res.sources }]);
    } catch (e) {
      setLog((l) => [...l, { role: "bot", text: `Fehler: ${e.message}`, sources: [] }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel" style={{ gridColumn: "1 / -1" }}>
      <h2>Document Chat (RAG)</h2>
      <div className="chat-log">
        {log.length === 0 && (
          <p className="status">
            Ask something about the uploaded documents, e.g.{" "}
            "What is the total amount of the invoice?"
          </p>
        )}
        {log.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <span className="who">{m.role === "user" ? "You" : "Assistant"}</span>
            {m.text}
            {m.sources?.length > 0 && (
              <div className="sources">
                {m.sources.map((s) => (
                  <div className="source" key={s.marker}>
                    [{s.marker}] {s.filename} ·{" "}
                    <span className="sim">{(s.similarity * 100).toFixed(0)}%</span> · {s.preview}…
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="msg bot">
            <span className="who">Assistant</span>
            <span className="spinner">Thinking…</span>
          </div>
        )}
      </div>
      <div className="chat-input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask a question about your documents…"
        />
        <button onClick={send} disabled={loading}>
          Send
        </button>
      </div>
    </div>
  );
}
