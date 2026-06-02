"""Tests for the RAG service. Mocks retrieval + LLM so no DB or API key is needed."""
from unittest.mock import MagicMock, patch

import pytest

from app.services import rag_chain


def test_format_context_numbers_sources():
    chunks = [
        {"filename": "a.txt", "chunk_index": 0, "content": "Inhalt A"},
        {"filename": "b.txt", "chunk_index": 1, "content": "Inhalt B"},
    ]
    ctx = rag_chain._format_context(chunks)
    assert "[Source 1]" in ctx
    assert "[Source 2]" in ctx
    assert "Inhalt A" in ctx and "Inhalt B" in ctx


def test_answer_question_empty_raises():
    with pytest.raises(ValueError):
        rag_chain.answer_question("   ")


def test_answer_question_no_documents_returns_message():
    with patch.object(rag_chain, "similarity_search", return_value=[]):
        result = rag_chain.answer_question("What is the leasing rate?")
    assert result["sources"] == []
    assert "No documents" in result["answer"]


def test_answer_question_with_sources():
    fake_chunks = [
        {
            "document_id": 1,
            "filename": "leasingvertrag.txt",
            "chunk_index": 0,
            "content": "Monatliche Leasingrate: 389,00 EUR",
            "similarity": 0.91,
        }
    ]
    fake_response = MagicMock()
    fake_response.content = "The monthly leasing rate is 389,00 EUR [Source 1]."

    with patch.object(rag_chain, "similarity_search", return_value=fake_chunks):
        with patch.object(rag_chain, "get_chat_model") as mock_model:
            fake_chain = MagicMock()
            fake_chain.invoke.return_value = fake_response
            # prompt | model  ->  fake_chain
            with patch("app.services.rag_chain.ChatPromptTemplate") as mock_prompt:
                mock_prompt.from_messages.return_value.__or__ = lambda s, o: fake_chain
                result = rag_chain.answer_question("What is the leasing rate?")

    assert "389,00 EUR" in result["answer"]
    assert len(result["sources"]) == 1
    assert result["sources"][0]["marker"] == "Source 1"
    assert result["sources"][0]["similarity"] == 0.91
