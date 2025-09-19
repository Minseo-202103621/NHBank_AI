"""Data models for the judge chain."""
from typing import List, Dict
from pydantic import BaseModel, Field

# Mapping from severity score to human readable Korean label.
SEVERITY_LABELS: dict[int, str] = {
    0: "규정 위반 없음",
    1: "경미한 위반 (주의 또는 교육 필요)",
    2: "중대한 위반 (조사 또는 감사 필요)",
    3: "심각한 위반 (즉시 처분 또는 법적 조치 필요)",
}

class PolicyLink(BaseModel):
    """A link to a specific policy document section."""
    doc_id: str = Field(..., description="참조한 문서의 ID 또는 이름")
    section: str = Field(..., description="참조한 조항 또는 섹션")
    sentence: str = Field(..., description="판단 근거가 된 핵심 문장")

class JudgeDecision(BaseModel):
    """Represents the final judgment of the AI judge."""
    violation_type: List[str] = Field(..., description="위반 유형 목록 (예: '배임/횡령', '불법 대출 실행')")
    severity: int = Field(..., description="사안의 중대성 점수 (0-3 사이의 정수)")
    severity_label: str = Field(..., description="중대성 점수에 해당하는 레이블")
    recommended_actions: List[str] = Field(..., description="권고 조치 사항 목록")
    rationale: str = Field(..., description="판정의 근거가 되는 핵심 사유 요약")
    policy_links: List[PolicyLink] = Field(..., description="판정의 근거가 된 관련 규정 목록")
    confidence: float = Field(..., description="판정에 대한 신뢰도 점수 (0.0 ~ 1.0)")
    needs_more_evidence: bool = Field(..., description="추가 증거가 필요한지 여부")
