"""Chat manager for handling conversations with users.

This module implements the chat management system that handles the conversation flow,
maintains context, and coordinates between different components like the RAG system
and the judge system.
"""

from __future__ import annotations

import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

from openai import AsyncOpenAI
from langchain_core.documents import Document
from app.settings import get_settings

from judge.prompts import (
    SYSTEM_PROMPT,
    INITIAL_GREETING,
    JUDGE_PROMPT_TEMPLATE,
)
from judge.types import JudgeDecision, SEVERITY_LABELS, PolicyLink
from retriever.search import RAGRetriever


@dataclass
class Message:
    """A chat message."""
    role: str
    content: str


@dataclass
class ConversationState:
    """The current state of a conversation."""
    messages: List[Message]
    turn_count: int = 0

class ChatManager:
    """Manages the conversation flow and state."""

    def __init__(self, retriever: RAGRetriever):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.retriever = retriever
        self.conversation_states: Dict[str, ConversationState] = {}

    def _get_or_create_state(self, conversation_id: str) -> ConversationState:
        """Get existing conversation state or create new one."""
        if conversation_id not in self.conversation_states:
            self.conversation_states[conversation_id] = ConversationState(
                messages=[Message(role="system", content=SYSTEM_PROMPT)],
            )
        return self.conversation_states[conversation_id]

    async def start_conversation(self, conversation_id: str) -> str:
        """Start a new conversation."""
        state = self._get_or_create_state(conversation_id)
        state.messages.append(Message(role="assistant", content=INITIAL_GREETING))
        return INITIAL_GREETING

    def _format_chat_history(self, messages: List[Message]) -> str:
        """Format chat history for the model."""
        return "\n".join([
            f"{msg.role}: {msg.content}" for msg in messages
        ])

    def _format_judgment_report(self, decision: JudgeDecision) -> str:
        """Formats the judge's decision into a human-readable report."""
        report_parts = [
            "[최종 판정 결과]",
            f"- 위반유형: {', '.join(decision.violation_type)}",
            f"- 중대성(severity): {decision.severity}",
            f"- 레이블: {decision.severity_label}",
            "- 권고조치:",
            *["  • " + action for action in decision.recommended_actions],
            "- 사유(rationale):",
            f"  {decision.rationale}",
            "- 관련 규정(policy_links):"
        ]
        for link in decision.policy_links:
            report_parts.append(f"  • 문서: {link.doc_id}, 조항: {link.section}")
            report_parts.append(f"    - 근거 문장: '{link.sentence}'")

        report_parts.append(f"- confidence: {decision.confidence:.2f}")
        report_parts.append(f"- needs_more_evidence: {decision.needs_more_evidence}")
        
        return "\n".join(report_parts)

    def _extract_doc_id_from_message(self, message: str) -> Optional[str]:
        """Extracts a document ID from the user's message."""
        # Look for filenames in quotes or ending with .pdf
        match = re.search(r'["“]([^"”]+\.pdf)["”]|["“]([^"”]+)["”]|(\S+\.pdf)', message)
        if match:
            # The first non-None group is the match
            return next((g for g in match.groups() if g is not None), None)
        return None

    def _extract_doc_id_from_context(self, context: str) -> Optional[str]:
        """Extracts the source document ID from the context string."""
        match = re.search(r"출처: (.+)", context)
        if match:
            return match.group(1).strip()
        return None

    async def process_message(
        self,
        conversation_id: str,
        message: str,
        evidence_files: Optional[List[Dict]] = None
    ) -> str:
        """Process a message and return the response."""
        state = self._get_or_create_state(conversation_id)
        state.messages.append(Message(role="user", content=message))
        state.turn_count += 1

        if "판정" in message or "판단" in message:
            return await self.make_judgment(conversation_id)

        requested_doc_id = self._extract_doc_id_from_message(message)
        policy_context = await self.retriever.get_context(message, doc_id=requested_doc_id)
        chat_history = self._format_chat_history(state.messages)
        
        retrieved_doc_id = self._extract_doc_id_from_context(policy_context)

        warning_message = ""
        if requested_doc_id and retrieved_doc_id and requested_doc_id not in retrieved_doc_id:
            warning_message = f"참고: 요청하신 '{requested_doc_id}' 문서를 찾지 못했습니다. 대신 검색된 '{retrieved_doc_id}' 문서를 기반으로 답변합니다.\n\n"

        context_prompt = (
            f"{warning_message}"
            f"이전 대화 내용:\n{chat_history}\n\n"
            f"관련 정책 및 규정:\n{policy_context}\n\n"
            f"마지막 사용자 메시지:\n{message}\n\n"
            "위 맥락을 고려하여 적절한 응답을 제공해주세요."
            "(만약 '참고' 메시지가 있다면, 해당 내용을 반드시 답변에 포함하여 사용자에게 알려주세요.)"
        )
        
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context_prompt}
            ]
        )
        
        assistant_message = response.choices[0].message.content
        
        if state.turn_count >= 3:
            assistant_message += "\n\n충분한 정보가 수집된 경우, 다음 단계로 최종 판정을 요청할 수 있습니다. 판정을 원하시면 '판정 요청'이라고 말씀해주세요."

        state.messages.append(Message(role="assistant", content=assistant_message))
        
        return assistant_message

    async def make_judgment(self, conversation_id: str) -> str:
        """Make a final judgment based on collected information."""
        state = self._get_or_create_state(conversation_id)
        
        chat_history = self._format_chat_history(state.messages)
        evidence = "대화 내용에서 증거 수집" 
        
        # Check for document mismatch across the whole conversation
        requested_doc_id = None
        for msg in state.messages:
            if msg.role == 'user':
                doc_id = self._extract_doc_id_from_message(msg.content)
                if doc_id:
                    requested_doc_id = doc_id # Keep the last requested doc

        full_conversation_text = "\n".join([m.content for m in state.messages])
        policy_context = await self.retriever.get_context(full_conversation_text, doc_id=requested_doc_id)
        
        retrieved_doc_id = self._extract_doc_id_from_context(policy_context)

        warning_message = ""
        if requested_doc_id and retrieved_doc_id and requested_doc_id not in retrieved_doc_id:
            warning_message = f"참고: 사용자가 대화 중 '{requested_doc_id}' 문서를 요청했지만, 판정은 검색된 '{retrieved_doc_id}' 문서를 기반으로 이루어졌습니다.\n\n"

        schema_json = json.dumps(JudgeDecision.model_json_schema(), indent=2)
        prompt = JUDGE_PROMPT_TEMPLATE.format(
            chat_history=chat_history,
            evidence=evidence,
            policy_context=f"{warning_message}{policy_context}",
            schema=schema_json
        )
        
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"},
        )
        
        try:
            judgment_json = json.loads(response.choices[0].message.content)
            decision = JudgeDecision.model_validate(judgment_json)
            
            report = self._format_judgment_report(decision)
            
            # Prepend warning to the final report if it exists
            final_report = f"{warning_message}{report}" if warning_message else report

            state.messages.append(Message(role="assistant", content=final_report))
            return final_report
            
        except (json.JSONDecodeError, ValueError) as e:
            error_message = f"판정 결과를 처리하는 중 오류가 발생했습니다: {e}"
            state.messages.append(Message(role="assistant", content=error_message))
            return error_message
