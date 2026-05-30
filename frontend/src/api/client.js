// Thin API client. Uses the Vite proxy paths in dev; configurable base for prod.

const EXTRACT = "/api/extract";
const RAG = "/api/rag";
const AGENT = "/api/agent";

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

export async function listNeedsReview() {
  const res = await fetch(`${EXTRACT}/documents?needs_review=true`);
  if (!res.ok) throw new Error("Failed to load review queue");
  return res.json();
}
