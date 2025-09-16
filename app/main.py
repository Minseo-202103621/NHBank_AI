"""FastAPI application entrypoint.

This module defines the REST API endpoints for the chat-based whistle-blower service.
It exposes routes for chat messages, evidence uploads, and judgments.
"""

from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, File, Form, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

from app.chat_schemas import ChatRequest, ChatResponse, EvidenceUpload, JudgeResponse
from app.settings import get_settings
from storage.db import get_db, init_db
from storage import models  # Import the models
from agent.orchestrator import Orchestrator
from agent.tools.file_ingest import handle_upload
from retriever.search import RAGRetriever

app = FastAPI(title="Bank Whistle AI")

# Global orchestrator instance
orchestrator = None

@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database and orchestrator on startup."""
    init_db()
    settings = get_settings()
    retriever = RAGRetriever(settings.regulation_index_path)
    global orchestrator
    orchestrator = Orchestrator(retriever)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat/start")
async def start_chat(db: Session = Depends(get_db)) -> ChatResponse:
    """Start a new chat conversation and create a corresponding report."""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    # Create a new report record for this conversation
    new_report = models.Report(
        summary="New chat conversation started.",
        status="chatting",
        created_at=datetime.utcnow()
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    conversation_id = str(new_report.id)
    message = await orchestrator.start_conversation(conversation_id)

    return ChatResponse(
        conversation_id=conversation_id,
        message=message,
        ready_for_judgment=False
    )

@app.post("/chat/message")
async def chat_message(request: ChatRequest) -> ChatResponse:
    """Process a chat message."""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    message, ready_for_judgment = await orchestrator.process_message(
        request.conversation_id,
        request.message
    )

    return ChatResponse(
        conversation_id=request.conversation_id,
        message=message,
        ready_for_judgment=ready_for_judgment
    )

@app.post("/chat/upload")
async def upload_evidence(
    conversation_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> EvidenceUpload:
    """Upload evidence file for a conversation."""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    try:
        report_id = int(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    # Handle file upload (synchronous call, no await)
    evidence_obj = handle_upload(file, report_id)
    db.add(evidence_obj)
    db.commit()
    db.refresh(evidence_obj)

    # Prepare evidence info for the orchestrator
    evidence_info_dict = {
        "id": str(evidence_obj.id),
        "filename": evidence_obj.filename,
        "extracted_text": evidence_obj.extracted_text or ""
    }

    # Process the evidence in chat
    await orchestrator.process_message(
        conversation_id,
        f"증거 자료가 업로드되었습니다: {file.filename}",
        [evidence_info_dict]
    )

    return EvidenceUpload(
        conversation_id=conversation_id,
        file_info=evidence_info_dict,
        extracted_text=evidence_obj.extracted_text
    )

@app.post("/chat/judge")
async def make_judgment(request: ChatRequest) -> JudgeResponse:
    """Make a final judgment for a conversation."""
    if not orchestrator:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    judgment = await orchestrator.process_judgment(request.conversation_id)
    
    # Optionally, update the report status
    try:
        report_id = int(request.conversation_id)
        report = db.get(models.Report, report_id)
        if report:
            report.status = "judged"
            db.commit()
    except (ValueError, Exception):
        pass # Fail silently if report update fails

    return JudgeResponse(**judgment)
