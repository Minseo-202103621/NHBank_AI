"""Placeholder for OCR extraction.

In a full implementation this function would perform optical character
recognition on images (e.g. scans of documents) to recover text for
inclusion in the retrieval pipeline.  This PoC leaves OCR unimplemented.
"""

from __future__ import annotations

from typing import Optional


def ocr_extract(image_bytes: bytes) -> Optional[str]:
    """Perform OCR on image bytes.

    Args:
        image_bytes: Raw bytes of an image file.

    Returns:
        Extracted text if OCR is available, otherwise `None`.
    """

    # OCR is not implemented in this proof of concept.
    return None