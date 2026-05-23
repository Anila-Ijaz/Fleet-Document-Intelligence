"""LLM-powered structured extraction.

Binds the chat model to the ExtractedFields schema so the model is forced to return
valid, typed JSON. Includes a German-aware system prompt because the target documents
(and the target employer) are German.
"""
from __future__ import annotations

import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.llm import get_chat_model
from app.models.schemas import ExtractedFields, ExtractionResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Du bist ein Experte für die Analyse von Flotten- und Leasingdokumenten \
(Rechnungen, Leasingverträge, Schadensmeldungen, Fahrzeugscheine).

Extrahiere die angeforderten Felder so genau wie möglich aus dem Dokumenttext.
Regeln:
- Wenn ein Feld nicht im Dokument vorkommt, lasse es null. Erfinde KEINE Werte.
- Beträge als Zahlen ohne Währungssymbol oder Tausendertrennzeichen (z. B. 1234.56).
- Datumsangaben im ISO-Format YYYY-MM-DD.
- Klassifiziere den Dokumenttyp anhand des Inhalts.
- Die Zusammenfassung ("summary") muss ein deutscher Satz sein.
"""

USER_PROMPT = """Analysiere das folgende Dokument und extrahiere die strukturierten Felder.

--- DOKUMENTTEXT START ---
{document_text}
--- DOKUMENTTEXT ENDE ---
"""

# Critical fields whose absence should flag a document for human review.
_CRITICAL = ("document_type", "document_number", "gross_amount")


def _compute_needs_review(fields: ExtractedFields, confidence: float) -> bool:
    if confidence < 0.6:
        return True
    if fields.document_type.value == "unknown":
        return True
    return False


def extract_fields(document_text: str) -> ExtractionResult:
    """Run the LLM extraction over document text and return a validated result."""
    if not document_text.strip():
        raise ValueError("Empty document text - nothing to extract.")

    model = get_chat_model()
    structured_model = model.with_structured_output(ExtractedFields)

    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("human", USER_PROMPT)]
    )
    chain = prompt | structured_model

    # Truncate very long docs to keep within context; documented tradeoff.
    text = document_text[:12000]

    logger.info("Running extraction over %d chars", len(text))
    fields: ExtractedFields = chain.invoke({"document_text": text})

    # Simple heuristic confidence. In production you might use logprobs or a
    # second verification pass; kept transparent and explainable here.
    populated = sum(
        1 for f in (fields.document_number, fields.gross_amount, fields.supplier_name) if f
    )
    confidence = round(0.5 + 0.15 * populated, 2)
    confidence = min(confidence, 0.95)

    return ExtractionResult(
        fields=fields,
        confidence=confidence,
        raw_text_chars=len(document_text),
        needs_review=_compute_needs_review(fields, confidence),
    )
