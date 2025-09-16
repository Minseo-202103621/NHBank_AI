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
from judge.chain import judge_report


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
    ) -> Tuple[str, bool]:
        """Process a user message and return the system's response."""
        # Get conversation state or create new one
        state = self.chat_manager._get_or_create_state(conversation_id)
        
        # Process the message
        response, ready_for_judgment = await self.chat_manager.process_message(
            conversation_id,
            message,
            evidence_files
        )
        
        return response, ready_for_judgment

    async def process_judgment(self, conversation_id: str) -> Dict:
        """Generate a final judgment for the conversation.

        The function performs the following steps:
        1. Collects all relevant information from the conversation
        2. Retrieves relevant regulations using RAG
        3. Generates a structured judgment with citations
        4. Returns the formatted response
        """
        # Get conversation state
        state = self.chat_manager._get_or_create_state(conversation_id)
        
        if not state.is_ready_for_judgment:
            raise ValueError("Not enough information to make a judgment")

        # Collect all information
        complaint = "\n".join([
            msg.content for msg in state.messages 
            if msg.role == "user"
        ])
        
        # Get evidence texts
        evidence_texts = [
            doc.get("extracted_text", "")
            for doc in state.evidence_documents
        ]
        
        # Search relevant regulations
        search_results = await TOOLS["rag_search"](complaint, top_k=3)
        
        # Construct evidence citations
        citations: List[Dict] = []
        for idx, doc in enumerate(state.evidence_documents):
            text = doc.get("extracted_text", "")
            snippet = text.strip()[:200] if text else ""
            citations.append({
                "source": doc.get("filename", f"evidence_{idx + 1}"),
                "quote": snippet
            })
            
        # Generate judgment
        judgment = await judge_report(complaint, evidence_texts, search_results)
        
        # Augment with citations and links
        judgment["evidence_citations"] = citations
        judgment["policy_links"] = [
            {
                "source": result.source,
                "relevance": result.score,
                "text": result.content[:200]
            } for result in search_results
        ]
        
        return judgment