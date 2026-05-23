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

SYSTEM_PROMPT = """Du bist ein Assistent für ein Flottenmanagement-Unternehmen. \
Beantworte Fragen ausschließlich auf Basis des bereitgestellten Kontexts aus internen \
Dokumenten (Rechnungen, Leasingverträge, Schadensmeldungen, Fahrzeugscheine).

Regeln:
- Antworte auf Deutsch.
- Nutze NUR Informationen aus dem Kontext. Wenn die Antwort nicht im Kontext steht, \
sage klar: "Diese Information ist in den vorliegenden Dokumenten nicht enthalten."
- Verweise bei Aussagen auf die Quelle mit der Markierung [Quelle N].
- Erfinde keine Zahlen, Namen oder Fakten.
"""

USER_PROMPT = """Frage: {question}

Kontext aus den Dokumenten:
{context}

Beantworte die Frage präzise und gib die Quellen an."""


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
            "answer": "Es sind noch keine Dokumente indexiert, "
            "daher kann die Frage nicht beantwortet werden.",
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
