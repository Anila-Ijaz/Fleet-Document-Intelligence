#!/usr/bin/env bash
# End-to-end smoke test: extraction (port 8000) + RAG (port 8001).
# Assumes `docker compose up` is running and OPENAI_API_KEY is set.
set -euo pipefail

EXTRACT="${1:-http://localhost:8000}"
RAG="${2:-http://localhost:8001}"

echo "== Extraction service =="
echo "1) Health..."
curl -fsS "$EXTRACT/health" && echo

echo "2) Upload sample invoice..."
curl -fsS -X POST "$EXTRACT/documents" -F "file=@sample_docs/rechnung_beispiel.txt" | python3 -m json.tool

echo "3) Upload sample leasing contract..."
curl -fsS -X POST "$EXTRACT/documents" -F "file=@sample_docs/leasingvertrag_beispiel.txt" | python3 -m json.tool

echo "4) List documents..."
curl -fsS "$EXTRACT/documents" | python3 -m json.tool

echo "== RAG service =="
echo "5) Index all documents into the vector store..."
curl -fsS -X POST "$RAG/index" | python3 -m json.tool

echo "6) Ask a German question (chatbot with citations)..."
curl -fsS -X POST "$RAG/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "Wie hoch ist die monatliche Leasingrate und fuer welches Fahrzeug?"}' \
  | python3 -m json.tool

echo "Smoke test complete."
