"""Registry of agent tools.

This module centralises the export of tool functions for use by the
orchestrator.  It simplifies dependency management and provides a single
point of reference for what capabilities the agent has access to.
"""

from __future__ import annotations

from .tools.rag_search import search as rag_search
from .tools.file_ingest import handle_upload as file_ingest
from .tools.pii_mask import mask_pii
from .tools.header_parser import parse_email_header
from .tools.policy_filter import is_allowed


TOOLS = {
    "rag_search": rag_search,
    "file_ingest": file_ingest,
    "mask_pii": mask_pii,
    "parse_email_header": parse_email_header,
    "policy_filter": is_allowed,
}