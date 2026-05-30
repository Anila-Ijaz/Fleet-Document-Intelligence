"""Vector store backed by Postgres + pgvector.

Stores document chunks and their embeddings, and does cosine-similarity retrieval.
Written with explicit SQL so the retrieval mechanics are visible, not hidden behind a
high-level wrapper - this demonstrates understanding of how RAG retrieval actually works.
"""
from __future__ import annotations

import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine
from app.core.llm import get_embeddings

logger = logging.getLogger(__name__)


def ensure_schema() -> None:
    """Create the chunks table + vector index if they don't exist."""
    s = get_settings()
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS doc_chunks (
                    id          BIGSERIAL PRIMARY KEY,
                    document_id BIGINT NOT NULL,
                    filename    TEXT,
                    chunk_index INT NOT NULL,
                    content     TEXT NOT NULL,
                    embedding   vector({s.embedding_dim})
                )
                """
            )
        )
        # Drop the old IVFFlat index if it exists — IVFFlat requires at least
        # as many rows as `lists` (100) to work; with small datasets it returns
        # zero results. HNSW works correctly for any dataset size.
        conn.execute(text("DROP INDEX IF EXISTS doc_chunks_embedding_idx"))
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS doc_chunks_embedding_hnsw_idx
                ON doc_chunks USING hnsw (embedding vector_cosine_ops)
                """
            )
        )
    logger.info("Vector schema ensured (dim=%s)", s.embedding_dim)


def _splitter() -> RecursiveCharacterTextSplitter:
    s = get_settings()
    return RecursiveCharacterTextSplitter(
        chunk_size=s.chunk_size,
        chunk_overlap=s.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def index_document(document_id: int, filename: str, content: str) -> int:
    """Chunk a document, embed each chunk, and store. Returns number of chunks stored."""
    chunks = _splitter().split_text(content)
    if not chunks:
        return 0

    embeddings = get_embeddings().embed_documents(chunks)
    engine = get_engine()

    with engine.begin() as conn:
        # Idempotent: clear any prior chunks for this document before re-indexing.
        conn.execute(
            text("DELETE FROM doc_chunks WHERE document_id = :doc_id"),
            {"doc_id": document_id},
        )
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            conn.execute(
                text(
                    """
                    INSERT INTO doc_chunks (document_id, filename, chunk_index, content, embedding)
                    VALUES (:doc_id, :filename, :idx, :content, :embedding)
                    """
                ),
                {
                    "doc_id": document_id,
                    "filename": filename,
                    "idx": i,
                    "content": chunk,
                    # pgvector accepts the Python list rendered as a string literal.
                    "embedding": str(emb),
                },
            )
    logger.info("Indexed document %s into %d chunks", document_id, len(chunks))
    return len(chunks)


def similarity_search(query: str, top_k: int | None = None) -> list[dict]:
    """Return the top_k most similar chunks to the query."""
    s = get_settings()
    k = top_k or s.top_k
    query_emb = get_embeddings().embed_query(query)
    engine = get_engine()

    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT document_id, filename, chunk_index, content,
                       1 - (embedding <=> :q) AS similarity
                FROM doc_chunks
                ORDER BY embedding <=> :q
                LIMIT :k
                """
            ),
            {"q": str(query_emb), "k": k},
        ).mappings().all()
    return [dict(r) for r in rows]
