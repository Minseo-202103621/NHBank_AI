"""Utility to build a regulation index from PDF files.

This script extracts text from each PDF file in a given directory and
splits it into rough paragraphs.  Each paragraph becomes a record in
the JSONL index with a document identifier, a section label and an
anchor.  The resulting index can be consumed by the retrieval engine.

Note: the extraction is intentionally simple and may not handle scanned
PDFs or complex layouts.  Use a more robust parser or OCR in a
production implementation.
"""

from __future__ import annotations

import json
import os
from typing import Iterable

from PyPDF2 import PdfReader


def _extract_text(pdf_path: str) -> str:
    """Extract raw text from a PDF file using PyPDF2.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        A single string containing the concatenated text of all pages.
    """

    reader = PdfReader(pdf_path)
    text_parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text_parts.append(page_text)
    return "\n".join(text_parts)


def _chunk_text(text: str, chunk_size: int = 1024) -> Iterable[str]:
    """Split text into approximate paragraphs based on blank lines.

    If blank lines are absent or too few, long paragraphs are further
    divided into fixed‐sized chunks to maintain retrieval granularity.

    Args:
        text: The full document text.
        chunk_size: Target length of each chunk (in characters).

    Yields:
        Chunks of text.
    """

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for para in paragraphs:
        if len(para) <= chunk_size:
            yield para
        else:
            # further subdivide long paragraphs
            for start in range(0, len(para), chunk_size):
                yield para[start : start + chunk_size]


def build_index(pdf_dir: str, output_path: str) -> None:
    """Build a JSONL regulation index from PDF documents.

    Each record in the JSONL file contains fields: `doc_id`, `section`,
    `anchor`, `text` and `meta`.  The `doc_id` is the filename of the PDF,
    `section` is a numbered chunk label (e.g. `chunk_0`), the `anchor` is a
    combination of filename and chunk label, and `text` is the extracted
    content.  Metadata contains at least the original filename.

    Args:
        pdf_dir: Directory containing PDF files to index.
        output_path: Path to write the JSONL index.
    """

    with open(output_path, "w", encoding="utf-8") as out_f:
        for filename in sorted(os.listdir(pdf_dir)):
            if not filename.lower().endswith(".pdf"):
                continue
            pdf_path = os.path.join(pdf_dir, filename)
            try:
                text = _extract_text(pdf_path)
            except Exception:
                # Skip files that cannot be parsed
                continue
            for i, chunk in enumerate(_chunk_text(text)):
                record = {
                    "doc_id": filename,
                    "section": f"chunk_{i}",
                    "anchor": f"{filename}#chunk_{i}",
                    "text": chunk,
                    "meta": {"filename": filename},
                }
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")