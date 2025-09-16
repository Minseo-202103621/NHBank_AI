"""Email header parser.

This helper converts a raw email header string into a dictionary of fields.
It relies on Python's built‑in `email` library.  More advanced parsing
could include decoding encoded words, unfolding line continuations and
validating header names.
"""

from __future__ import annotations

from email import message_from_string
from typing import Dict


def parse_email_header(raw_header: str) -> Dict[str, str]:
    """Parse an email header into a dictionary of header fields.

    Args:
        raw_header: A string containing the raw header text of an email.

    Returns:
        A dictionary mapping header names to their values.  If the
        header contains multiple instances of the same field the last
        occurrence overwrites previous ones.
    """

    msg = message_from_string(raw_header)
    headers: Dict[str, str] = {}
    for key, value in msg.items():
        headers[key] = value
    return headers