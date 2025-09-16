"""Thin wrapper around the retrieval engine for use by the agent.

This module lazily instantiates a `SimpleRetriever` using the path to the
regulation index specified in the application settings.  The asynchronous
`search` function can then be imported and called from the orchestrator.
"""

from __future__ import annotations

from typing import List, Dict

from app.settings import get_settings
from retriever.search import RAGRetriever


_retriever: RAGRetriever | None = None


def _get_retriever() -> RAGRetriever:
    global _retriever
    if _retriever is None:
        settings = get_settings()
        _retriever = RAGRetriever(settings.regulation_index_path)
    return _retriever


async def search(query: str, top_k: int = 3) -> List[Dict]:
    """Search the regulation index for relevant chunks.

    Args:
        query: A free text query, typically the summary and description of a report.
        top_k: Number of top results to return.

    Returns:
        A list of index records augmented with a `score` field.
    """

    retriever = _get_retriever()
    return await retriever.search(query, top_k)