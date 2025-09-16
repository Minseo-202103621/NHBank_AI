"""Chat manager for handling conversations with users.

This module implements the chat management system that handles the conversation flow,
maintains context, and coordinates between different components like the RAG system
and the judge system.
"""

from __future__ import annotations

import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

from openai import AsyncOpenAI
from langchain_core.documents import Document
from app.settings import get_settings

from judge.prompts import (
    SYSTEM_PROMPT,
    INITIAL_GREETING,
    EVIDENCE_REQUEST,
    JUDGE_PROMPT,
    FINAL_JUDGMENT,
    CONVERSATION_MEMORY_PROMPT,
)
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
    collected_info: Dict[str, str]
    evidence_documents: List[Dict]
    needs_evidence: bool
    is_ready_for_judgment: bool
    judgment_made: bool


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
                collected_info={},
                evidence_documents=[],
                needs_evidence=False,
                is_ready_for_judgment=False,
                judgment_made=False
            )
        return self.conversation_states[conversation_id]

    async def start_conversation(self, conversation_id: str) -> str:
        """Start a new conversation."""
        state = self._get_or_create_state(conversation_id)
        state.messages.append(Message(role="assistant", content=INITIAL_GREETING))
        return INITIAL_GREETING

    def _prepare_conversation_context(self, state: ConversationState, query: str) -> str:
        """Prepare conversation context for the model."""
        # Get relevant documents from RAG
        context = self.retriever.get_context(query)
        
        # Format conversation history
        chat_history = "\n".join([
            f"{msg.role}: {msg.content}" for msg in state.messages[-5:]  # Last 5 messages
        ])
        
        # Format collected information
        collected_info = "\n".join([
            f"{key}: {value}" for key, value in state.collected_info.items()
        ])
        
        return CONVERSATION_MEMORY_PROMPT.format(
            chat_history=chat_history,
            collected_info=collected_info,
            policy_context=context,
            user_message=query
        )

    async def process_message(
        self,
        conversation_id: str,
        message: str,
        evidence_files: Optional[List[Dict]] = None
    ) -> Tuple[str, bool]:
        """Process a message and return the response."""
        state = self._get_or_create_state(conversation_id)
        
        # Add user message to history
        state.messages.append(Message(role="user", content=message))
        
        # Handle evidence if provided
        if evidence_files:
            state.evidence_documents.extend(evidence_files)
            state.needs_evidence = False
            
        # Prepare conversation context
        context = self._prepare_conversation_context(state, message)
        
        # Get model response
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "system", "content": context},
                {"role": "user", "content": message}
            ]
        )
        
        assistant_message = response.choices[0].message.content
        state.messages.append(Message(role="assistant", content=assistant_message))
        
        # Check if ready for judgment
        if (not state.needs_evidence and not state.judgment_made and 
            len(state.evidence_documents) > 0):
            state.is_ready_for_judgment = True
            
        return assistant_message, state.is_ready_for_judgment

    async def make_judgment(self, conversation_id: str) -> str:
        """Make a final judgment based on collected information."""
        state = self._get_or_create_state(conversation_id)
        
        if not state.is_ready_for_judgment:
            return "아직 판단을 내리기 위한 충분한 정보가 수집되지 않았습니다."
            
        # Prepare judgment context
        complaint = json.dumps(state.collected_info, ensure_ascii=False)
        evidence = json.dumps(state.evidence_documents, ensure_ascii=False)
        
        # Get judgment from model
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": JUDGE_PROMPT.format(
                    complaint=complaint,
                    evidence=evidence
                )}
            ]
        )
        
        try:
            judgment_data = json.loads(response.choices[0].message.content)
            
            # Format the judgment
            judgment = FINAL_JUDGMENT.format(
                severity_label=judgment_data.get("severity_label", "알 수 없음"),
                violation_types=", ".join(judgment_data.get("violation_type", [])),
                recommended_actions=", ".join(judgment_data.get("recommended_actions", [])),
                rationale=judgment_data.get("rationale", ""),
                additional_evidence_request=(
                    "\n추가 증거가 필요합니다." if judgment_data.get("needs_more_evidence")
                    else ""
                )
            )
            
            state.judgment_made = True
            state.messages.append(Message(role="assistant", content=judgment))
            return judgment
            
        except json.JSONDecodeError:
            return "판단 결과를 처리하는 중 오류가 발생했습니다."