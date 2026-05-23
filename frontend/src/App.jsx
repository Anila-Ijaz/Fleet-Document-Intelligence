import { useState } from "react";
import UploadPanel from "./components/UploadPanel.jsx";
import DocumentList from "./components/DocumentList.jsx";
import ChatPanel from "./components/ChatPanel.jsx";

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="app">
      <header className="masthead">
        <div>
          <span className="tag">Flottenmanagement · Prozessautomatisierung</span>
          <h1>Fleet Document Intelligence</h1>
        </div>
        <div className="meta">v0.2 · RAG + Extraction</div>
      </header>

      <div className="grid">
        <UploadPanel onUploaded={() => setRefreshKey((k) => k + 1)} />
        <DocumentList refreshKey={refreshKey} />
        <ChatPanel />
      </div>
    </div>
  );
}
