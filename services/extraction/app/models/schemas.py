"""Domain schemas for fleet/leasing documents.

These Pydantic models are the contract for what the LLM must return. By binding the
LLM to these schemas (structured output), we turn free text into validated, typed data
that can be written straight into the database. This is the core of the extraction service.
"""
from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """The fleet document categories the system understands."""

    INVOICE = "invoice"
    LEASING_CONTRACT = "leasing_contract"
    DAMAGE_REPORT = "damage_report"
    VEHICLE_REGISTRATION = "vehicle_registration"
    UNKNOWN = "unknown"


class LineItem(BaseModel):
    description: str = Field(description="Description of the line item / service")
    quantity: float | None = Field(default=None, description="Quantity, if present")
    unit_price: float | None = Field(default=None, description="Price per unit in EUR")
    total: float | None = Field(default=None, description="Line total in EUR")


class ExtractedFields(BaseModel):
    """The structured fields extracted from a document.

    All fields optional because real-world documents are messy and not every field
    appears in every document. Extraction should never fail just because a field is missing.
    """

    document_type: DocumentType = Field(
        description="The classified type of this document"
    )

    # Common identifiers
    document_number: str | None = Field(
        default=None, description="Invoice number, contract ID, or reference number"
    )
    document_date: date | None = Field(
        default=None, description="The primary date on the document (ISO format)"
    )

    # Parties
    supplier_name: str | None = Field(default=None, description="Issuing company / supplier")
    customer_name: str | None = Field(default=None, description="Recipient / lessee")

    # Vehicle (key for a fleet company)
    vehicle_make: str | None = Field(default=None, description="e.g. BMW, MINI, Audi")
    vehicle_model: str | None = Field(default=None, description="e.g. 320d, Cooper SE")
    vin: str | None = Field(default=None, description="Vehicle Identification Number")
    license_plate: str | None = Field(default=None, description="Registration / plate number")

    # Money
    currency: str = Field(default="EUR", description="ISO currency code")
    net_amount: float | None = Field(default=None, description="Net total")
    vat_amount: float | None = Field(default=None, description="VAT / tax amount")
    gross_amount: float | None = Field(default=None, description="Gross total")
    line_items: list[LineItem] | None = Field(
        default=None, description="Itemised lines, if any"
    )

    # Leasing-specific
    monthly_rate: float | None = Field(default=None, description="Monthly leasing rate in EUR")
    contract_start: date | None = Field(default=None, description="Lease start date")
    contract_end: date | None = Field(default=None, description="Lease end date")

    # Free-text catch-all
    summary: str | None = Field(
        default=None, description="One-sentence German summary of the document"
    )


class ExtractionResult(BaseModel):
    """Full result returned by the API, including metadata."""

    fields: ExtractedFields
    confidence: float = Field(
        ge=0.0, le=1.0, description="Model's self-reported confidence 0-1"
    )
    raw_text_chars: int = Field(description="Number of characters of source text processed")
    needs_review: bool = Field(
        description="True if confidence is low or critical fields are missing"
    )
