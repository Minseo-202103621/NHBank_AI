"""API schemas for the chat-based whistle-blower system.

These Pydantic models define the structure of requests and responses for
the chat-based whistle-blower system API endpoints.
"""

from __future__ import annotations

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A chat message."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Request model for chat messages."""
    conversation_id: str = Field(..., description="Unique identifier for the conversation")
    message: str = Field(..., description="The message content")


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    conversation_id: str
    message: str
    ready_for_judgment: bool = False


class EvidenceUpload(BaseModel):
    """Evidence upload information."""
    conversation_id: str
    file_info: Dict[str, str]
    extracted_text: Optional[str]


class JudgeResponse(BaseModel):
    """Response model for the judgment endpoint."""
    violation_type: List[str] = Field(..., description="위반 유형 목록")
    severity: int = Field(..., description="심각도 (0-3)")
    severity_label: str = Field(..., description="심각도 설명")
    recommended_actions: List[str] = Field(..., description="권장 조치 목록")
    rationale: str = Field(..., description="판단 근거")
    evidence_citations: List[Dict[str, str]] = Field(..., description="증거 인용")
    policy_links: List[Dict[str, str]] = Field(..., description="관련 규정 링크")
    confidence: float = Field(..., description="판단 신뢰도 (0-1)")
    needs_more_evidence: bool = Field(..., description="추가 증거 필요 여부")