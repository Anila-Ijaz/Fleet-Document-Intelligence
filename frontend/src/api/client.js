// API client — uses direct Render URLs in production, Vite proxy paths in local dev.

const IS_DEV = import.meta.env.DEV;

const EXTRACT = IS_DEV
  ? "/api/extract"
  : "https://fleet-document-intelligence.onrender.com";

const RAG = IS_DEV
  ? "/api/rag"
  : "https://rag-chatbot-cs9e.onrender.com";

const AGENT = IS_DEV
  ? "/api/agent"
  : "https://agent-service-4jxu.onrender.com";

export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${EXTRACT}/documents`, { method: "POST", body: form });
  if (!res.ok) throw new Error((await res.json()).detail || "Upload failed");
  return res.json();
}

export async function listDocuments() {
  const res = await fetch(`${EXTRACT}/documents`);
  if (!res.ok) throw new Error("Failed to load documents");
  return res.json();
}

export async function reindexAll() {
  const res = await fetch(`${RAG}/index`, { method: "POST" });
  if (!res.ok) throw new Error("Indexing failed");
  return res.json();
}

export async function askQuestion(question) {
  const res = await fetch(`${RAG}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Chat failed");
  return res.json();
}

export async function triageDocument(docId) {
  const res = await fetch(`${AGENT}/triage/${docId}`, { method: "POST" });
  if (!res.ok) throw new Error((await res.json()).detail || "Triage failed");
  return res.json();
}

export async function deleteDocument(id) {
  const res = await fetch(`${EXTRACT}/documents/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error((await res.json()).detail || "Delete failed");
}

export async function listNeedsReview() {
  const res = await fetch(`${EXTRACT}/documents?needs_review=true`);
  if (!res.ok) throw new Error("Failed to load review queue");
  return res.json();
}
