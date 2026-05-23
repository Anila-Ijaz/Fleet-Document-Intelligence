"""FastAPI application - the extraction service HTTP API.

Endpoints:
  GET  /health              -> liveness/readiness probe (used by k8s)
  POST /documents           -> upload a file, extract fields, persist, return result
  GET  /documents           -> list stored documents (with simple filters)
  GET  /documents/{id}      -> fetch one document
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.models import db
from app.models.schemas import ExtractionResult
from app.services.extractor import extract_fields
from app.services.text_extraction import extract_text

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=get_settings().app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    # Create tables on boot. For a bigger project you'd use Alembic migrations;
    # documented as a deliberate simplification for the portfolio scope.
    db.create_tables()
    logger.info("Extraction service started (provider=%s)", get_settings().llm_provider)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "extraction", "provider": get_settings().llm_provider}


@app.post("/documents", response_model=ExtractionResult)
async def create_document(file: UploadFile = File(...)) -> ExtractionResult:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")

    try:
        text = extract_text(file.filename or "upload", data)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No extractable text found (scanned PDF without OCR?).",
        )

    try:
        result = extract_fields(text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Extraction failed")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}") from exc

    # Persist
    with db.get_session() as session:
        doc = db.Document(
            filename=file.filename or "upload",
            document_type=result.fields.document_type.value,
            raw_text=text,
            extracted=result.fields.model_dump(mode="json"),
            confidence=result.confidence,
            needs_review=result.needs_review,
            supplier_name=result.fields.supplier_name,
            gross_amount=result.fields.gross_amount,
            vehicle_make=result.fields.vehicle_make,
        )
        session.add(doc)
        session.commit()
        logger.info("Stored document id=%s type=%s", doc.id, doc.document_type)

    return result


@app.get("/documents")
def list_documents(
    needs_review: bool | None = Query(default=None),
    document_type: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
) -> list[dict]:
    with db.get_session() as session:
        query = session.query(db.Document)
        if needs_review is not None:
            query = query.filter(db.Document.needs_review == needs_review)
        if document_type:
            query = query.filter(db.Document.document_type == document_type)
        rows = query.order_by(db.Document.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "filename": r.filename,
                "document_type": r.document_type,
                "supplier_name": r.supplier_name,
                "gross_amount": r.gross_amount,
                "vehicle_make": r.vehicle_make,
                "confidence": r.confidence,
                "needs_review": r.needs_review,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


@app.get("/documents/{doc_id}")
def get_document(doc_id: int) -> dict:
    with db.get_session() as session:
        r = session.get(db.Document, doc_id)
        if not r:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {
            "id": r.id,
            "filename": r.filename,
            "document_type": r.document_type,
            "extracted": r.extracted,
            "confidence": r.confidence,
            "needs_review": r.needs_review,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
