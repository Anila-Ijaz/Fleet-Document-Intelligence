"""A stateful triage agent built with LangGraph.

Given a processed document, the agent walks a small decision graph:

    classify_risk -> detect_anomalies -> decide_action -> [draft_reply | finalize]

Design choice: business-critical decisions (is this high value? low confidence?) are
made by DETERMINISTIC rules, not the LLM. The LLM is used only where it adds value -
drafting a human-readable German reply. This keeps the system auditable: you can always
explain *why* a document was flagged. An LLM left in charge of financial decisions would
be a red flag in a real fleet/leasing context.
"""
from __future__ import annotations

import logging
from typing import Literal, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from app.core.config import get_settings
from app.core.llm import get_chat_model

logger = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    # Inputs
    document_id: int
    document_type: str
    confidence: float
    gross_amount: float | None
    supplier_name: str | None
    summary: str | None

    # Working state
    risk_level: Literal["low", "medium", "high"]
    anomalies: list[str]
    action: Literal["auto_approve", "flag_for_review", "escalate"]
    draft_reply: str | None


# --- Nodes ---------------------------------------------------------------


def classify_risk(state: AgentState) -> AgentState:
    """Deterministic risk classification from amount + confidence."""
    s = get_settings()
    amount = state.get("gross_amount") or 0.0
    confidence = state.get("confidence", 1.0)

    if amount >= s.high_value_threshold_eur or confidence < s.confidence_review_threshold:
        risk = "high"
    elif amount >= s.high_value_threshold_eur / 2:
        risk = "medium"
    else:
        risk = "low"

    logger.info("Risk for doc %s: %s (amount=%.2f, conf=%.2f)",
                state.get("document_id"), risk, amount, confidence)
    return {"risk_level": risk}


def detect_anomalies(state: AgentState) -> AgentState:
    """Rule-based anomaly checks. Transparent and explainable."""
    s = get_settings()
    anomalies: list[str] = []

    if state.get("confidence", 1.0) < s.confidence_review_threshold:
        anomalies.append("Niedrige Extraktionssicherheit")
    if state.get("document_type") == "unknown":
        anomalies.append("Dokumenttyp konnte nicht bestimmt werden")
    if not state.get("supplier_name"):
        anomalies.append("Kein Lieferant/Absender erkannt")
    amount = state.get("gross_amount")
    if amount is not None and amount >= s.high_value_threshold_eur:
        anomalies.append(f"Hoher Betrag (>= {s.high_value_threshold_eur:.0f} EUR)")
    if amount is None and state.get("document_type") in ("invoice", "leasing_contract"):
        anomalies.append("Betrag fehlt bei Rechnung/Vertrag")

    return {"anomalies": anomalies}


def decide_action(state: AgentState) -> AgentState:
    """Map risk + anomalies to a concrete action."""
    risk = state.get("risk_level", "low")
    anomalies = state.get("anomalies", [])

    if risk == "high":
        action = "escalate"
    elif risk == "medium" or anomalies:
        action = "flag_for_review"
    else:
        action = "auto_approve"

    return {"action": action}


def draft_reply(state: AgentState) -> AgentState:
    """Use the LLM to draft a short German internal note explaining the decision."""
    model = get_chat_model()
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Du bist ein Assistent im Flottenmanagement. Formuliere eine kurze, "
                "sachliche interne Notiz auf Deutsch (max. 3 Sätze), die erklärt, warum "
                "ein Dokument geprüft oder eskaliert werden muss.",
            ),
            (
                "human",
                "Dokumenttyp: {document_type}\nBetrag: {gross_amount} EUR\n"
                "Lieferant: {supplier_name}\nAuffälligkeiten: {anomalies}\n"
                "Empfohlene Aktion: {action}\n\nSchreibe die Notiz.",
            ),
        ]
    )
    chain = prompt | model
    response = chain.invoke(
        {
            "document_type": state.get("document_type"),
            "gross_amount": state.get("gross_amount"),
            "supplier_name": state.get("supplier_name") or "unbekannt",
            "anomalies": ", ".join(state.get("anomalies", [])) or "keine",
            "action": state.get("action"),
        }
    )
    text = response.content if hasattr(response, "content") else str(response)
    return {"draft_reply": text}


def finalize(state: AgentState) -> AgentState:
    """Terminal node for auto-approved documents - no reply needed."""
    return {"draft_reply": None}


# --- Routing -------------------------------------------------------------


def route_after_action(state: AgentState) -> str:
    """Auto-approved docs skip the LLM entirely; others get a drafted note."""
    return "finalize" if state.get("action") == "auto_approve" else "draft_reply"


# --- Graph construction --------------------------------------------------


def build_agent():
    graph = StateGraph(AgentState)
    graph.add_node("classify_risk", classify_risk)
    graph.add_node("detect_anomalies", detect_anomalies)
    graph.add_node("decide_action", decide_action)
    graph.add_node("draft_reply", draft_reply)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("classify_risk")
    graph.add_edge("classify_risk", "detect_anomalies")
    graph.add_edge("detect_anomalies", "decide_action")
    graph.add_conditional_edges(
        "decide_action",
        route_after_action,
        {"draft_reply": "draft_reply", "finalize": "finalize"},
    )
    graph.add_edge("draft_reply", END)
    graph.add_edge("finalize", END)

    return graph.compile()


# Compile once at import.
_AGENT = None


def get_agent():
    global _AGENT
    if _AGENT is None:
        _AGENT = build_agent()
    return _AGENT


def triage_document(doc: dict) -> AgentState:
    """Run the agent over one document's extracted fields. Pure function over state."""
    initial: AgentState = {
        "document_id": doc.get("id", 0),
        "document_type": doc.get("document_type", "unknown"),
        "confidence": doc.get("confidence", 1.0),
        "gross_amount": doc.get("gross_amount"),
        "supplier_name": doc.get("supplier_name"),
        "summary": doc.get("summary"),
    }
    result = get_agent().invoke(initial)
    return result
