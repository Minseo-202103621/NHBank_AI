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
        
        print(f"[DEBUG] Initializing vector store from: {persist_directory}")

        if os.path.exists(persist_directory):
            print("[DEBUG] Loading existing ChromaDB from disk.")
            self.vectorstore = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
            print("[DEBUG] ChromaDB loaded successfully.")
        else:
            print("[DEBUG] No existing ChromaDB found. Creating a new one.")
            documents = self._load_documents()
            print(f"[DEBUG] Loaded {len(documents)} document chunks from jsonl.")
            if not documents:
                print("[ERROR] No documents to index. The database will be empty.")
                self.vectorstore = None
                return

            print("[DEBUG] Creating new ChromaDB instance...")
            try:
                self.vectorstore = Chroma(
                    collection_name="bank_whistle",
                    persist_directory=persist_directory,
                    embedding_function=self.embeddings
                )
                print("[DEBUG] Adding documents and creating embeddings. This may take a moment...")
                self.vectorstore.add_documents(documents)
                print("[DEBUG] New ChromaDB created and documents added.")
            except Exception as e:
                print(f"[ERROR] An exception occurred during ChromaDB creation/embedding: {e}")
                import traceback
                traceback.print_exc()
                self.vectorstore = None

        if self.vectorstore:
            try:
                count = self.vectorstore._collection.count()
                print(f"[DEBUG] Vector store initialized. Number of documents in collection: {count}")
                if count == 0:
                    print("[WARNING] The vector store is empty. Searches will not find any results.")
            except Exception as e:
                print(f"[ERROR] Could not get document count from vector store: {e}")
        else:
            print("[ERROR] Vector store initialization failed.")

    def _load_documents(self) -> List[Document]:
        """Load documents from the JSONL index file."""
        documents = []
        
        if not os.path.exists(self.index_path):
            return documents
            
        with open(self.index_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                    # Pass the original filename from doc_id to the metadata source
                    doc = Document(
                        page_content=record["text"],
                        metadata={
                            "source": record.get("doc_id", ""), # Use doc_id as the source
                            "section": record.get("section", ""),
                        }
                    )
                    documents.append(doc)
                except json.JSONDecodeError:
                    continue
                    
        return documents

    async def search(self, query: str, k: int = 5, doc_id: Optional[str] = None) -> List[SearchResult]:
        """Search for relevant documents using semantic similarity."""
        if not self.vectorstore:
            return []

        search_kwargs = {
            'k': k,
            'score_threshold': 0.0
        }
        if doc_id:
            search_kwargs['filter'] = {'source': doc_id}
        
        results = self.vectorstore.similarity_search_with_relevance_scores(
            query=query,
            **search_kwargs
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

    async def get_context(self, query: str, doc_id: Optional[str] = None, max_tokens: int = 2000) -> str:
        """Get formatted context string from search results."""
        results = await self.search(query=query, doc_id=doc_id)
        
        num_results = len(results)
        
        context_parts = []
        total_tokens = 0
        
        for result in results:
            result_tokens = len(result.content.split())
            if total_tokens + result_tokens > max_tokens:
                break
            context = f"\n출처: {result.source}\n"
            context += f"관련도: {result.score:.2f}\n"
            context += f"내용: {result.content}\n"
            context_parts.append(context)
            total_tokens += result_tokens
            
        real_context = "\n".join(context_parts)
        
        debug_wrapper = (
            f"--- DEBUG START ---\n"
            f"Search found {num_results} results.\n"
            f"The generated context is:\n"
            f"vvvvvvvvvvvvvvvvvvvv\n"
            f"{real_context}\n"
            f"^^^^^^^^^^^^^^^^^^^^\n"
            f"--- DEBUG END ---\n"
        )
        
        return debug_wrapper