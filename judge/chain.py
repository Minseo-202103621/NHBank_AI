"""The core logic for the judge chain.

This module composes the prompt, calls the OpenAI API and parses the
response.  If the API call fails or returns invalid JSON the chain falls
back to a heuristic rule based on whether the complaint mentions terms
associated with embezzlement or breach of duty.  The judgement includes
both a numeric severity and the corresponding label.
"""

from __future__ import annotations

import json
import os
from typing import List, Dict, Any

import openai

from .prompts import JUDGE_PROMPT
from .calibrate import map_severity_label
from app.settings import get_settings


async def judge_report(
    complaint: str, evidence_list: List[str], search_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Invoke the LLM to produce a judgement for a report.

    Args:
        complaint: Text summarising the complaint (summary + details).
        evidence_list: A list of extracted evidence texts.
        search_results: Results from the RAG search (unused in this PoC but
            could be included in the prompt to ground the model).

    Returns:
        A dictionary with keys defined in the prompt template.  If the call
        to the OpenAI API fails, a heuristic fallback is used.
    """

    # Prepare prompt with complaint and concatenated evidence
    evidence_text = "\n\n".join(evidence_list or [])
    prompt = JUDGE_PROMPT.format(
        complaint=complaint.strip(),
        evidence=evidence_text.strip(),
    )
    
    settings = get_settings()
    result: Dict[str, Any] = {}
    
    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=512
        )
        content = completion.choices[0].message.content.strip()
        result = json.loads(content)
    except Exception as e:
        print(f"OpenAI API 호출 중 오류 발생: {e}")
        result = {}
    # Heuristic fallback if no result from API
    if not result:
        violation_types: List[str] = []
        sev = 0
        lower = complaint.lower()
        # Simple rule: mention of 횡령 or 배임 implies moderate severity
        if "횡령" in lower or "배임" in lower:
            violation_types.append("배임/횡령")
            sev = 2
        result = {
            "violation_type": violation_types,
            "severity": sev,
            "recommended_actions": ["조사 필요"] if sev > 0 else ["해당 없음"],
            "rationale": "단순 규칙에 따른 기본 판단입니다.",
            "confidence": 0.5,
            "needs_more_evidence": False,
        }
    # Ensure severity label exists
    severity = int(result.get("severity", 0))
    result["severity_label"] = result.get(
        "severity_label", map_severity_label(severity)
    )
    return result