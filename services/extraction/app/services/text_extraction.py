"""Turn an uploaded file (PDF, image, or text) into raw text.

Kept separate from the LLM logic so each concern is testable in isolation.
Scanned PDFs and images are handled via OCR (pytesseract + pdf2image).
"""
from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


def _ocr_pdf_page(data: bytes, page_num: int) -> str:
    """Convert one PDF page to an image and run OCR on it.

    Returns empty string if OCR dependencies are not installed or OCR fails,
    so the caller can degrade gracefully.
    """
    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        images = convert_from_bytes(
            data, first_page=page_num + 1, last_page=page_num + 1, dpi=300
        )
        if not images:
            return ""
        return pytesseract.image_to_string(images[0], lang="eng+deu").strip()
    except ImportError:
        logger.warning("OCR dependencies not available (pytesseract/pdf2image). Skipping OCR.")
        return ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR failed for page %d: %s", page_num, exc)
        return ""


def _ocr_image(data: bytes) -> str:
    """Run OCR directly on an image file (PNG, JPG, etc.)."""
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(image, lang="eng+deu").strip()
    except ImportError:
        logger.warning("OCR dependencies not available (pytesseract/Pillow). Skipping OCR.")
        return ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR failed on image: %s", exc)
        return ""


def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from a PDF. Falls back to OCR for scanned (image-only) pages."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text)
            else:
                logger.info("Page %d has no text layer — attempting OCR", i)
                ocr_text = _ocr_pdf_page(data, i)
                if ocr_text:
                    parts.append(ocr_text)
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
    if name.endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        return _ocr_image(data)
    raise ValueError(
        f"Unsupported file type: {filename}. Supported: .pdf, .txt, .md, .png, .jpg, .jpeg"
    )
