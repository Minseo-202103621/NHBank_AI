"""Handle evidence file uploads and text extraction.

This module provides a function for processing uploaded files.  Files are
persisted via the storage layer and any textual content is extracted for
later use in the RAG pipeline.  Currently only PDF files are parsed; in
practice you would support text extraction from Word documents, images
(via OCR) and email formats (.eml/.msg) as well.
"""

from __future__ import annotations

import io
from fastapi import UploadFile
from typing import Optional

from PyPDF2 import PdfReader

from storage.s3 import save_evidence_file
from storage import models


def handle_upload(uploaded: UploadFile, report_id: int) -> models.Evidence:
    """Persist an uploaded file and extract text if possible.

    Args:
        uploaded: The file provided via a multipart form in FastAPI.
        report_id: Identifier of the report the evidence belongs to.

    Returns:
        A new `Evidence` ORM object. The object has not yet been added
        to a database session.
    """

    file_bytes = uploaded.file.read() or b''
    uploaded.file.seek(0) # Reset file pointer for subsequent reads (e.g., by PdfReader)
    storage_uri, file_hash = save_evidence_file(file_bytes, uploaded.filename)
    extracted_text: Optional[str] = None
    # Attempt simple text extraction for PDFs
    if uploaded.filename.lower().endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            pieces: list[str] = []
            for page in reader.pages:
                text = page.extract_text() or ""
                pieces.append(text)
            extracted_text = "\n".join(pieces)
        except Exception:
            extracted_text = None
    evidence = models.Evidence(
        report_id=report_id,
        filename=uploaded.filename,
        storage_uri=storage_uri,
        hash=file_hash,
        extracted_text=extracted_text,
    )
    return evidence