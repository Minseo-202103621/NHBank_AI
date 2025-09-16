"""Enhanced retrieval engine for the regulation corpus using RAG.

This module implements a more sophisticated retrieval system that uses
dense embeddings and semantic search to find relevant passages from the
regulation corpus. It supports both exact matching and semantic similarity
for better context retrieval during conversations.
"""

from __future__ import annotations

import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.settings import get_settings

from app.settings import get_settings


@dataclass
class SearchResult:
    """Represents a search result with metadata."""
    content: str
    source: str
    score: float
    metadata: Dict


class RAGRetriever:
    """Enhanced retrieval engine using RAG."""

    def __init__(self, index_path: str):
        self.index_path = index_path
        settings = get_settings()
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
        self.vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", "!", "?", ";"]
        )
        self._initialize_vectorstore()

    def _initialize_vectorstore(self):
        """Initialize or load the vector store."""
        settings = get_settings()
        persist_directory = settings.chroma_persist_directory
        
        if os.path.exists(persist_directory):
            self.vectorstore = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
        else:
            documents = self._load_documents()
            self.vectorstore = Chroma(
                collection_name="bank_whistle",
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
            self.vectorstore.add_documents(documents)
            self.vectorstore.persist()

    def _load_documents(self) -> List[Document]:
        """Load documents from the JSONL index file."""
        documents = []
        
        if not os.path.exists(self.index_path):
            return documents
            
        with open(self.index_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    doc = Document(
                        page_content=record["text"],
                        metadata={
                            "source": record.get("source", ""),
                            "title": record.get("title", ""),
                            "section": record.get("section", ""),
                            "page": record.get("page", 0)
                        }
                    )
                    documents.append(doc)
                except json.JSONDecodeError:
                    continue
                    
        return documents

    async def search(self, query: str, k: int = 5) -> List[SearchResult]:
        """Search for relevant documents using semantic similarity."""
        if not self.vectorstore:
            return []
            
        results = self.vectorstore.similarity_search_with_relevance_scores(
            query=query,
            k=k
        )
        
        search_results = []
        for doc, score in results:
            search_results.append(SearchResult(
                content=doc.page_content,
                source=doc.metadata.get("source", ""),
                score=score,
                metadata=doc.metadata
            ))
            
        return search_results

    async def add_documents(self, documents: List[Document]):
        """Add new documents to the vector store."""
        if not self.vectorstore:
            return
            
        chunks = self.text_splitter.split_documents(documents)
        self.vectorstore.add_documents(chunks)
        self.vectorstore.persist()

    def get_context(self, query: str, max_tokens: int = 2000) -> str:
        """Get formatted context string from search results."""
        results = self.vectorstore.similarity_search_with_relevance_scores(query, k=3)
        
        context_parts = []
        current_tokens = 0
        
        for doc, score in results:
            if current_tokens >= max_tokens:
                break
                
            context = f"\n출처: {doc.metadata.get('source', '')}\n"
            context += f"관련도: {score:.2f}\n"
            context += f"내용: {doc.page_content}\n"
            
            # Rough token estimate
            current_tokens += len(context) / 3
            context_parts.append(context)
            
        return "\n".join(context_parts)