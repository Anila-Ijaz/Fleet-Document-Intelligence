# Fleet Document Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?logo=langchain&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agent-1C3C3C)
![OpenAI](https://img.shields.io/badge/OpenAI-API-412991?logo=openai&logoColor=white)
![Postgres](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![n8n](https://img.shields.io/badge/n8n-workflow-EA4B71?logo=n8n&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-kind%20%2B%20EKS-326CE5?logo=kubernetes&logoColor=white)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)

An end-to-end **AI-supported process automation** system for **fleet leasing** — the
business of companies like Alphabet (BMW Group), LeasePlan, and Arval. It ingests the
documents a fleet leasing company handles every day (invoices, leasing contracts, damage
reports, vehicle registrations), uses a Large Language Model to **extract structured,
validated data**, stores it, and lets staff query the whole corpus through a RAG
chatbot — replacing slow, manual document handling with an automated pipeline.

Built specifically to demonstrate the skills in BMW Group / Alphabet's "Developer for
AI-supported process automation" role: LLMs and RAG, structured extraction, data
pipelines, AI agents, n8n workflows, and cloud deployment.

> **Status:** Feature-complete across all 7 build phases — document extraction, RAG
> chatbot, LangGraph triage agent, n8n orchestration, React frontend, Kubernetes
> manifests (local `kind`), and CI. Deployed and live.

## Live Demo

**Try the application here:** [https://frontend-1plp.onrender.com/](https://frontend-1plp.onrender.com/)

> **Note:** The app is hosted on Render's free tier. If the page takes 30–60 seconds
> to load on first visit, the service is spinning up from idle — just wait and refresh.

### What you can do in the live demo

1. **Upload a document** — use any of the sample files in `sample_docs/` (German invoices,
   leasing contracts, damage reports). The AI extracts structured fields and classifies
   the document type automatically.
2. **Review queue** — documents flagged as low-confidence or high-value appear here for
   human review, with the agent's German explanation note.
3. **RAG chatbot** — click "Index for chat", then ask questions in English or German
   about any uploaded documents. Answers include citations showing which document each
   fact came from.

## Why this design

This table maps the project directly onto the BMW Group / Alphabet job requirements:

| Job requirement | Where it lives in this repo |
|---|---|
| LLMs, structured output, text generation | `services/extraction` — LangChain + Pydantic structured output |
| RAG systems, chatbots | `services/rag` — pgvector retrieval + cited Q&A |
| AI agents | `services/agent` — LangGraph stateful triage agent |
| Workflow automation with n8n | `n8n/workflows/fleet_document_intake.json` |
| Data pipelines / ETL / databases | Postgres + pgvector + SQLAlchemy, document→fields→embeddings flow |
| Provider-agnostic AI (OpenAI / Anthropic / Bedrock / Ollama) | each service's `core/llm.py` — switch with one env var |
| Cloud environments (Azure, AWS) | `k8s/` manifests + `scripts/deploy-eks.sh` (AWS EKS + ECR) |
| German language | German prompts, German sample documents, German UI |
| Structured, production-minded engineering | tests, CI (`.github/workflows/ci.yml`), multi-stage non-root Docker |

## Architecture

```
                          ┌─────────────────┐
                          │ React frontend  │  upload · list · chat
                          └───┬─────────┬───┘
                   /api/extract        /api/rag
                          │             │
   n8n workflow           │             │
   (orchestration)        ▼             ▼
   webhook ─┐     ┌──────────────┐  ┌──────────────┐
            ├────▶│  Extraction  │  │  RAG service │
            │     │ FastAPI +    │  │ retrieval +  │
            │     │ LangChain    │  │ cited Q&A    │
            │     └──────┬───────┘  └──────┬───────┘
            │            │                 │
            │     ┌──────▼───────┐         │
            └────▶│ Agent        │         │
                  │ LangGraph    │         │
                  │ triage       │         │
                  └──────┬───────┘         │
                         ▼                 ▼
                  ┌─────────────────────────┐   ┌──────────────┐
                  │  Postgres + pgvector     │   │  OpenAI API  │
                  │  documents · embeddings  │   │ LLM + embeds │
                  └─────────────────────────┘   └──────────────┘

  Deployment: Render (live) · Docker Compose (local) · Kubernetes on kind (local) · AWS EKS (cloud)
```

The **n8n workflow** orchestrates the pipeline: a document hits a webhook, gets its
fields extracted, is triaged by the **LangGraph agent**, then routed (auto-approve /
review / escalate). The **RAG service** answers questions over the whole corpus
with citations. All four app services are containerised and deployable to Kubernetes.

## Switching LLM provider

No code change — just an env var:

```yaml
# docker-compose.yml -> extraction.environment
LLM_PROVIDER: openai
LLM_MODEL: gpt-4o-mini
OPENAI_API_KEY: sk-...
```

Supported: `ollama`, `openai`, `anthropic`, `bedrock`.

## Tests

Each service has its own suite. Tests mock the LLM, so they run fast and need no API key:

```bash
cd services/extraction && pip install -r requirements.txt && pytest
cd services/rag        && pip install -r requirements.txt && pytest
cd services/agent      && pip install -r requirements.txt && pytest
```

16 tests cover extraction parsing/validation, RAG retrieval + citation formatting, and
the agent's deterministic decision logic (including a full LangGraph graph run). CI runs
all of these on every push — see `.github/workflows/ci.yml`.

## Deployment

- **Live (Render):** [https://frontend-1plp.onrender.com/](https://frontend-1plp.onrender.com/)
- **Local Kubernetes (kind):** `./scripts/deploy-kind.sh` — free, proves the manifests work
- **AWS EKS:** see `k8s/README.md` for the full guide (includes cost warnings + teardown)

## Local development

Prerequisites: Docker + Docker Compose, and an OpenAI API key.
On Windows, see `scripts/setup-wsl2.md` first.

```bash
# 1. Set your OpenAI key
cp .env.example .env        # then edit OPENAI_API_KEY

# 2. Start the stack
docker compose up --build

# 3. Run the end-to-end smoke test
./scripts/smoke-test.sh
```

Local service ports (only accessible when running the stack locally):
- Extraction API + docs: `http://localhost:8000/docs`
- RAG API + docs: `http://localhost:8001/docs`
- Agent API + docs: `http://localhost:8002/docs`
- n8n workflow editor: `http://localhost:5678` (import `n8n/workflows/`)
- Web UI: `http://localhost:3000`

For frontend development with hot reload:

```bash
cd frontend
npm install
npm run dev          # proxies to the running backend services
```

## Roadmap

- [x] **Phase 1** — Extraction service + Postgres, structured output, tests, Docker
- [x] **Phase 2** — RAG chatbot over the corpus (pgvector, citations, Q&A)
- [x] **Phase 3** — LangGraph triage agent + n8n ingest/orchestration workflow
- [x] **Phase 4** — React frontend (upload + chat + review queue)
- [x] **Phase 5** — Kubernetes manifests, runs on local `kind` (`scripts/deploy-kind.sh`)
- [x] **Phase 6** — AWS EKS deployment (ECR images, `scripts/deploy-eks.sh`, see `k8s/README.md`)
- [x] **Phase 7** — CI (GitHub Actions), tests across services, architecture docs
- [x] **Phase 8** — Live deployment on Render

### Possible future work
- Replace in-cluster Postgres with Amazon RDS (pgvector) for a managed database
- OCR for scanned PDFs (pytesseract) in the extraction service
- A demo GIF in this README

## Tech stack

**Backend & AI:** Python 3.12 · FastAPI · LangChain · Pydantic v2 · OpenAI
(gpt-4o-mini + text-embedding-3-small) — provider-agnostic, also supports Anthropic,
AWS Bedrock, and local Ollama

**Data:** PostgreSQL 16 · pgvector (vector similarity search) · SQLAlchemy 2.0

**Frontend:** React 18 · Vite · nginx (production serving + API proxy)

**Infrastructure:** Docker · Docker Compose · Kubernetes + AWS EKS · Render (live hosting)

**Quality:** pytest (LLM mocked for fast, deterministic tests) · type hints · multi-stage
Docker builds running as non-root
