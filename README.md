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
![AWS](https://img.shields.io/badge/AWS-EKS-FF9900?logo=amazonwebservices&logoColor=white)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)

An end-to-end **AI-supported process automation** system for **fleet leasing** — the
business of companies like Alphabet (BMW Group), LeasePlan, and Arval. It ingests the
documents a fleet leasing company handles every day (invoices, leasing contracts, damage
reports, vehicle registrations), uses a Large Language Model to **extract structured,
validated data**, stores it, and lets staff query the whole corpus through a German RAG
chatbot — replacing slow, manual document handling with an automated pipeline.

Built specifically to demonstrate the skills in BMW Group / Alphabet's "Developer for
AI-supported process automation" role: LLMs and RAG, structured extraction, data
pipelines, and (on the roadmap) AI agents, n8n workflows, and cloud deployment.

> **Status:** Feature-complete across all 7 build phases — document extraction, RAG
> chatbot, LangGraph triage agent, n8n orchestration, React frontend, Kubernetes
> manifests (local `kind` + AWS EKS), and CI. Runs locally with one command.

## Why this design

This table maps the project directly onto the BMW Group / Alphabet job requirements:

| Job requirement | Where it lives in this repo |
|---|---|
| LLMs, structured output, text generation | `services/extraction` — LangChain + Pydantic structured output |
| RAG systems, chatbots | `services/rag` — pgvector retrieval + cited German Q&A |
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
            │     │ LangChain    │  │ cited German │
            │     └──────┬───────┘  │ Q&A          │
            │            │          └──────┬───────┘
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

  Deployment: Docker Compose (local) · Kubernetes on kind (local) · AWS EKS (cloud)
```

The **n8n workflow** orchestrates the pipeline: a document hits a webhook, gets its
fields extracted, is triaged by the **LangGraph agent**, then routed (auto-approve /
review / escalate). The **RAG service** answers German questions over the whole corpus
with citations. All four app services are containerised and deployable to Kubernetes.

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
- Agent service: http://localhost:8002/docs
- n8n workflow editor: http://localhost:5678 (import `n8n/workflows/`)

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

- **Local Kubernetes (kind):** `./scripts/deploy-kind.sh` — free, proves the manifests work
- **AWS EKS:** see `k8s/README.md` for the full guide (includes cost warnings + teardown)

## Roadmap

- [x] **Phase 1** — Extraction service + Postgres, structured output, tests, Docker
- [x] **Phase 2** — RAG chatbot over the corpus (pgvector, citations, German Q&A)
- [x] **Phase 3** — LangGraph triage agent + n8n ingest/orchestration workflow
- [x] **Phase 4** — React frontend (upload + chat + review queue)
- [x] **Phase 5** — Kubernetes manifests, runs on local `kind` (`scripts/deploy-kind.sh`)
- [x] **Phase 6** — AWS EKS deployment (ECR images, `scripts/deploy-eks.sh`, see `k8s/README.md`)
- [x] **Phase 7** — CI (GitHub Actions), tests across services, architecture docs

### Possible future work
- Replace in-cluster Postgres with Amazon RDS (pgvector) for a managed database
- OCR for scanned PDFs (pytesseract) in the extraction service
- A demo GIF in this README (record once running locally)

## Tech stack

**Backend & AI:** Python 3.12 · FastAPI · LangChain · Pydantic v2 · OpenAI
(gpt-4o-mini + text-embedding-3-small) — provider-agnostic, also supports Anthropic,
AWS Bedrock, and local Ollama

**Data:** PostgreSQL 16 · pgvector (vector similarity search) · SQLAlchemy 2.0

**Frontend:** React 18 · Vite · nginx (production serving + API proxy)

**Infrastructure:** Docker · Docker Compose · Kubernetes + AWS EKS (planned)

**Quality:** pytest (LLM mocked for fast, deterministic tests) · type hints · multi-stage
Docker builds running as non-root
