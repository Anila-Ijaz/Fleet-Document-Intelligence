"""Agent service HTTP API.

  GET  /health             -> probe
  POST /triage/{doc_id}    -> run the triage agent over a stored document
  POST /triage             -> run the agent over an inline document payload (used by n8n)
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.services.triage_agent import triage_document

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=get_settings().app_name, version="0.3.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

_engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)


class DocPayload(BaseModel):
    id: int = 0
    document_type: str = "unknown"
    confidence: float = 1.0
    gross_amount: float | None = None
    supplier_name: str | None = None
    summary: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "agent"}


@app.post("/triage/{doc_id}")
def triage_by_id(doc_id: int) -> dict:
    with _engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT id, document_type, confidence, gross_amount, supplier_name "
                "FROM documents WHERE id = :id"
            ),
            {"id": doc_id},
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found.")

    result = triage_document(dict(row))
    return _clean(result)


@app.post("/triage")
def triage_inline(payload: DocPayload) -> dict:
    result = triage_document(payload.model_dump())
    return _clean(result)


def _clean(result: dict) -> dict:
    """Return only the decision-relevant fields."""
    return {
        "document_id": result.get("document_id"),
        "risk_level": result.get("risk_level"),
        "anomalies": result.get("anomalies", []),
        "action": result.get("action"),
        "draft_reply": result.get("draft_reply"),
    }
