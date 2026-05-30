"""The RAG question-answering chain.

Retrieves relevant chunks from pgvector, builds a context block with source markers,
and asks the LLM to answer in German using ONLY that context, citing sources. Returns
both the answer and the source chunks so the UI can show citations.
"""
from __future__ import annotations

import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.core.llm import get_chat_model
from app.services.vectorstore import similarity_search

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an assistant for a fleet management company. \
Answer questions strictly based on the provided context from internal documents \
(invoices, leasing contracts, damage reports, vehicle registrations).

Rules:
- Answer in English.
- Use ONLY information from the context. If the answer is not in the context, \
clearly state: "This information is not available in the provided documents."
- Reference sources using the marker [Source N].
- Do not invent numbers, names, or facts.
"""

USER_PROMPT = """Question: {question}

Context from documents:
{context}

Answer the question precisely and cite your sources."""


def _format_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        blocks.append(
            f"[Quelle {i}] (Dokument: {c['filename']}, Abschnitt {c['chunk_index']})\n"
            f"{c['content']}"
        )
    return "\n\n".join(blocks)


def answer_question(question: str, top_k: int | None = None) -> dict:
    """Run retrieval + generation. Returns answer text and the source chunks."""
    if not question.strip():
        raise ValueError("Empty question.")

    chunks = similarity_search(question, top_k=top_k)
    if not chunks:
        return {
            "answer": "No documents have been indexed yet. "
            "Please click 'Indexing for chat' first.",
            "sources": [],
        }

    context = _format_context(chunks)
    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", USER_PROMPT)]
    )
    chain = prompt | get_chat_model()
    response = chain.invoke({"question": question, "context": context})

    answer = response.content if hasattr(response, "content") else str(response)

    sources = [
        {
            "marker": f"Quelle {i}",
            "document_id": c["document_id"],
            "filename": c["filename"],
            "chunk_index": c["chunk_index"],
            "similarity": round(float(c["similarity"]), 3),
            "preview": c["content"][:200],
        }
        for i, c in enumerate(chunks, start=1)
    ]

    logger.info("Answered question using %d sources", len(sources))
    return {"answer": answer, "sources": sources}
