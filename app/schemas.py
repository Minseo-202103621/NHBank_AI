"""API request and response models.

These Pydantic models describe the shape of data exchanged with the FastAPI
endpoints. Having explicit schemas improves validation and generates rich
OpenAPI documentation. In this PoC the models are intentionally simple but
can be extended to include more metadata as needed.
"""

from __future__ import annotations

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    """Model for creating a new whistle‑blower report."""

    summary: str = Field(..., description="A brief summary of the suspected misconduct.")
    details: Optional[str] = Field(
        None,
        description="Additional details about the incident, including dates, people involved and any relevant context.",
    )
    category: Optional[str] = Field(None, description="Optional category of the report.")
    department: Optional[str] = Field(None, description="Department or business unit relevant to the report.")


class EvidenceInfo(BaseModel):
    """Representation of evidence attached to a report."""

    id: int
    filename: str
    extracted_text: Optional[str] = None


class Report(BaseModel):
    """Full representation of a report returned by the API."""

    id: int
    summary: str
    details: Optional[str]
    category: Optional[str]
    department: Optional[str]
    status: str
    created_at: str
    evidence: List[EvidenceInfo] = []


class JudgeRequest(BaseModel):
    """Empty request body for judge endpoint.

    In the future this model can include fields such as override instructions
    or user context to influence the judgement.
    """

    pass


class JudgeResponse(BaseModel):
    """Response model for the judgement endpoint."""

    violation_type: List[str]
    severity: int
    severity_label: str
    recommended_actions: List[str]
    rationale: str
    evidence_citations: List[Dict]
    policy_links: List[Dict]
    confidence: float
    needs_more_evidence: bool