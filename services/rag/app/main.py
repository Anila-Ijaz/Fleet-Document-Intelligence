"""RAG service HTTP API.

  GET  /health          -> probe
  POST /index           -> (re)index all stored documents into the vector store
  POST /index/{doc_id}  -> index a single document by id
  POST /chat            -> ask a question, get a cited German answer
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine
from app.services.rag_chain import answer_question
from app.services.vectorstore import ensure_schema, index_document

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=get_settings().app_name, version="0.2.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


class ChatRequest(BaseModel):
    question: str
    top_k: int | None = None


@app.on_event("startup")
def _startup() -> None:
    ensure_schema()
    logger.info("RAG service started (provider=%s)", get_settings().llm_provider)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "rag"}


@app.post("/index")
def index_all() -> dict:
    """Read every document from the shared DB and (re)index it into pgvector."""
    engine = get_engine()
    total_docs = 0
    total_chunks = 0
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, filename, raw_text FROM documents")
        ).mappings().all()
    for r in rows:
        n = index_document(r["id"], r["filename"], r["raw_text"])
        total_docs += 1
        total_chunks += n
    return {"indexed_documents": total_docs, "indexed_chunks": total_chunks}


@app.post("/index/{doc_id}")
def index_one(doc_id: int) -> dict:
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, filename, raw_text FROM documents WHERE id = :id"),
            {"id": doc_id},
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found.")
    n = index_document(row["id"], row["filename"], row["raw_text"])
    return {"document_id": doc_id, "indexed_chunks": n}


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    try:
        return answer_question(req.question, top_k=req.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat failed")
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc
