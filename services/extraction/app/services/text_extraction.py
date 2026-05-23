"""Turn an uploaded file (PDF, image, or text) into raw text.

Kept separate from the LLM logic so each concern is testable in isolation.
"""
from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from a PDF. Falls back gracefully if a page has no text layer."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            parts.append(page.extract_text() or "")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to extract text from page %d: %s", i, exc)
    return "\n".join(parts).strip()


def extract_text(filename: str, data: bytes) -> str:
    """Dispatch on file extension and return plain text."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(data)
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="replace").strip()
    # For images you would plug in OCR (e.g. pytesseract) here. Kept out of the
    # core path to avoid a heavy system dependency; documented as a known extension point.
    raise ValueError(
        f"Unsupported file type: {filename}. Supported: .pdf, .txt, .md"
    )
