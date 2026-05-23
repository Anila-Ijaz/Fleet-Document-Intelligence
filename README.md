# Fleet Document Intelligence Platform

An end-to-end system that ingests fleet & leasing documents (invoices, leasing
contracts, damage reports, vehicle registrations), extracts **structured, validated
data** with an LLM, stores it, and (in later phases) lets you query the whole corpus
via a German RAG chatbot and act on documents with an autonomous agent.

Built to mirror the kind of AI-supported process automation a fleet leasing company
actually needs: turning unstructured documents into structured, actionable data.

> **Status:** Phase 1 complete — extraction service + database, runnable with one command.
> Phases 2–6 (RAG chatbot, agent, n8n orchestration, Kubernetes, AWS EKS) are on the roadmap below.

## Why this design

| Requirement | Where it lives |
|---|---|
| LLMs, structured output, text generation | `services/extraction` (LangChain + Pydantic structured output) |
| Provider-agnostic AI (Ollama / OpenAI / Anthropic / Bedrock) | `app/core/llm.py` — switch with one env var |
| Databases & data modelling | Postgres + SQLAlchemy, pgvector enabled |
| German-language domain handling | German system prompt + German sample docs |
| Containerisation | Multi-stage `Dockerfile`, `docker-compose.yml` |
| Cloud / orchestration | Kubernetes manifests + AWS EKS (Phase 5–6) |

## Architecture (Phases 1–2)

```
                         ┌─────────────────┐
                         │ React frontend  │  upload · list · chat
                         └───┬─────────┬───┘
                  /api/extract        /api/rag
                         │             │
              ┌──────────▼───┐   ┌─────▼──────────┐
              │  Extraction  │   │  RAG service   │
              │ FastAPI +    │   │ retrieval +    │
              │ LangChain +  │   │ cited German   │
              │ Pydantic     │   │ Q&A            │
              └──────┬───────┘   └───┬────────┬───┘
                     │               │        │
                     ▼               ▼        ▼
              ┌─────────────────────────┐  ┌──────────────┐
              │  Postgres + pgvector     │  │  OpenAI API  │
              │  documents · embeddings  │  │ LLM + embeds │
              └─────────────────────────┘  └──────────────┘
```

The frontend (`frontend/`, React + Vite) provides document upload, a live document
list with review flags, and a German RAG chatbot with inline citations. In production
it is served by nginx, which proxies `/api/extract` and `/api/rag` to the two services.

## Quick start

Prerequisites: Docker + Docker Compose, and an OpenAI API key.
On Windows, see `scripts/setup-wsl2.md` first.

```bash
# 1. Set your OpenAI key
cp .env.example .env        # then edit OPENAI_API_KEY

# 2. Start the stack (Postgres + extraction API + RAG API)
docker compose up --build

# 3. In another terminal, run the end-to-end smoke test
./scripts/smoke-test.sh
```

Interactive API docs:
- Extraction service: http://localhost:8000/docs
- RAG chatbot service: http://localhost:8001/docs

The web UI (built with the rest of the stack) is at http://localhost:3000.

For frontend development with hot reload, run it outside Docker:

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies to the running services
```

Upload a German sample invoice and watch it come back as structured JSON:

```bash
curl -X POST http://localhost:8000/documents \
  -F "file=@sample_docs/rechnung_beispiel.txt"
```

Then index and ask a question in German:

```bash
curl -X POST http://localhost:8001/index
curl -X POST http://localhost:8001/chat -H "Content-Type: application/json" \
  -d '{"question": "Wie hoch ist die monatliche Leasingrate?"}'
```

## Switching LLM provider

No code change — just an env var. To use OpenAI instead of local Ollama:

```yaml
# docker-compose.yml -> extraction.environment
LLM_PROVIDER: openai
LLM_MODEL: gpt-4o-mini
OPENAI_API_KEY: sk-...
```

Supported: `ollama`, `openai`, `anthropic`, `bedrock`.

## Tests

```bash
cd services/extraction
pip install -r requirements.txt
pytest
```

Tests mock the LLM, so they run fast and need no model — they verify the logic
*around* the model (parsing, validation, review-flagging).

## Roadmap

- [x] **Phase 1** — Extraction service + Postgres, structured output, tests, Docker
- [x] **Phase 2** — RAG chatbot over the corpus (pgvector, citations, German Q&A)
- [ ] **Phase 3** — LangGraph agent (anomaly flagging, draft replies) + n8n ingest workflow
- [x] **Phase 4** — React frontend (upload + chat + review queue)
- [ ] **Phase 5** — Kubernetes manifests, runs on local `kind`/`minikube`
- [ ] **Phase 6** — AWS EKS deployment (ECR images, managed Postgres via RDS)
- [ ] **Phase 7** — CI (GitHub Actions), architecture diagram, demo GIF

## Tech stack

Python 3.12 · FastAPI · LangChain · Pydantic v2 · SQLAlchemy 2.0 · PostgreSQL +
pgvector · Ollama · Docker · (Kubernetes + AWS EKS to come)
