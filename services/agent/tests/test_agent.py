"""Tests for the triage agent.

The deterministic nodes (risk, anomalies, action) are tested directly with no LLM.
The full graph is tested for auto-approve (which skips the LLM entirely), so the whole
suite runs without an API key.
"""
from app.services import triage_agent as ta


def test_classify_risk_high_on_large_amount():
    out = ta.classify_risk({"gross_amount": 9000.0, "confidence": 0.9})
    assert out["risk_level"] == "high"


def test_classify_risk_high_on_low_confidence():
    out = ta.classify_risk({"gross_amount": 100.0, "confidence": 0.3})
    assert out["risk_level"] == "high"


def test_classify_risk_low():
    out = ta.classify_risk({"gross_amount": 200.0, "confidence": 0.95})
    assert out["risk_level"] == "low"


def test_detect_anomalies_flags_missing_supplier_and_unknown_type():
    out = ta.detect_anomalies(
        {"document_type": "unknown", "confidence": 0.9, "supplier_name": None}
    )
    assert any("Dokumenttyp" in a for a in out["anomalies"])
    assert any("Lieferant" in a for a in out["anomalies"])


def test_detect_anomalies_clean_document():
    out = ta.detect_anomalies(
        {
            "document_type": "invoice",
            "confidence": 0.9,
            "supplier_name": "Autohaus GmbH",
            "gross_amount": 800.0,
        }
    )
    assert out["anomalies"] == []


def test_decide_action_escalate_on_high_risk():
    assert ta.decide_action({"risk_level": "high", "anomalies": []})["action"] == "escalate"


def test_decide_action_auto_approve_when_clean():
    assert (
        ta.decide_action({"risk_level": "low", "anomalies": []})["action"]
        == "auto_approve"
    )


def test_full_graph_auto_approve_skips_llm():
    # A clean, low-value, high-confidence invoice should auto-approve with no LLM call.
    doc = {
        "id": 1,
        "document_type": "invoice",
        "confidence": 0.95,
        "gross_amount": 300.0,
        "supplier_name": "Autohaus GmbH",
    }
    result = ta.triage_document(doc)
    assert result["action"] == "auto_approve"
    assert result["draft_reply"] is None
    assert result["risk_level"] == "low"
