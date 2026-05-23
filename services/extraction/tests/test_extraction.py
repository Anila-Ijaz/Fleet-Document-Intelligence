"""Tests for the extraction service.

We mock the LLM so tests are fast, deterministic, and require no model. This shows you
test the logic around the model, not the model itself - a sign of practical engineering.
"""
from datetime import date
from unittest.mock import patch

import pytest

from app.models.schemas import DocumentType, ExtractedFields
from app.services import extractor
from app.services.text_extraction import extract_text


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
