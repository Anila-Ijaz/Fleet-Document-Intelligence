"""Tests for the extraction service.

We mock the LLM so tests are fast, deterministic, and require no model. This shows you
test the logic around the model, not the model itself - a sign of practical engineering.
"""
from datetime import date
from unittest.mock import patch

import pytest

from app.models.schemas import DocumentType, ExtractedFields
from app.services import extractor
from app.services.text_extraction import extract_text, _ocr_pdf_page


def test_extract_text_from_plain_text():
    data = "Rechnung Nr. 123\nBMW 320d\nBrutto: 1234.56".encode("utf-8")
    text = extract_text("invoice.txt", data)
    assert "Rechnung" in text
    assert "BMW 320d" in text


def test_unsupported_file_type_raises():
    with pytest.raises(ValueError):
        extract_text("photo.heic", b"x")


def test_extract_fields_uses_structured_output():
    fake_fields = ExtractedFields(
        document_type=DocumentType.INVOICE,
        document_number="RE-2026-001",
        document_date=date(2026, 1, 15),
        supplier_name="Werkstatt München GmbH",
        vehicle_make="BMW",
        gross_amount=1234.56,
        summary="Rechnung für die Wartung eines BMW 320d.",
    )

    class FakeChain:
        def invoke(self, _inputs):
            return fake_fields

    # Patch the chain construction so no real model is called.
    with patch.object(extractor, "get_chat_model") as mock_model:
        mock_model.return_value.with_structured_output.return_value = object()
        with patch("app.services.extractor.ChatPromptTemplate") as mock_prompt:
            mock_prompt.from_messages.return_value.__or__ = lambda self, other: FakeChain()
            result = extractor.extract_fields("Rechnung Nr. RE-2026-001 ... Brutto 1234.56")

    assert result.fields.document_type == DocumentType.INVOICE
    assert result.fields.gross_amount == 1234.56
    assert result.confidence > 0.5
    assert result.needs_review is False


def test_empty_text_raises():
    with pytest.raises(ValueError):
        extractor.extract_fields("   ")


def test_image_file_type_accepted():
    """PNG/JPG files are accepted and routed to OCR (mocked here)."""
    with patch("app.services.text_extraction._ocr_image", return_value="Invoice total 500 EUR"):
        text = extract_text("scan.png", b"fake-image-bytes")
    assert "Invoice total 500 EUR" in text


def test_ocr_fallback_for_scanned_pdf():
    """When pypdf returns no text (scanned PDF), OCR is attempted per page."""
    from unittest.mock import MagicMock

    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""

    with patch("pypdf.PdfReader") as mock_reader_cls:
        mock_reader_cls.return_value.pages = [mock_page]
        with patch("app.services.text_extraction._ocr_pdf_page", return_value="Scanned invoice 862 EUR") as mock_ocr:
            text = extract_text("scanned.pdf", b"fake-pdf")

    mock_ocr.assert_called_once_with(b"fake-pdf", 0)
    assert "Scanned invoice 862 EUR" in text


def test_ocr_graceful_fallback_when_not_installed():
    """If pytesseract is not installed, OCR returns empty string without crashing."""
    import sys
    with patch.dict(sys.modules, {"pytesseract": None, "pdf2image": None}):
        result = _ocr_pdf_page(b"fake-pdf", 0)
    assert result == ""
