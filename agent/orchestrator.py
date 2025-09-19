"""The chat agent orchestrator.

This module coordinates the interaction between different components of the
chat-based whistle-blower system. It manages the conversation flow,
evidence collection, and judgment process through a conversational interface.
"""

from __future__ import annotations

import asyncio
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from .tools_registry import TOOLS
from .chat_manager import ChatManager, Message, ConversationState
from retriever.search import RAGRetriever



class Orchestrator:
    """Manages the interaction between different components of the system."""

    def __init__(self, retriever: RAGRetriever):
        self.retriever = retriever
        self.chat_manager = ChatManager(retriever)
        self.conversations: Dict[str, ConversationState] = {}

    async def start_conversation(self, conversation_id: str) -> str:
        """Start a new conversation."""
        return await self.chat_manager.start_conversation(conversation_id)

    async def process_message(
        self,
        conversation_id: str,
        message: str,
        evidence_files: Optional[List[Dict]] = None
    ) -> str:
        """Process a user message and return the system's response."""
        response = await self.chat_manager.process_message(
            conversation_id,
            message,
            evidence_files
        )
        return response

    async def process_judgment(self, conversation_id: str) -> str:
        """Triggers the judgment process in the ChatManager."""
        return await self.chat_manager.make_judgment(conversation_id)