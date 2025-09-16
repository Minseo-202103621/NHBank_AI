"""PII masking helpers.

This module defines a simple function for masking personally identifiable
information (PII) found in text.  It masks email addresses, phone numbers
and Korean resident registration numbers.  You should expand this
function with more robust rules or integrate an existing de‑identification
library for production use.
"""

import re


def mask_pii(text: str) -> str:
    """Mask common PII patterns in the given text.

    The function attempts to find and mask email addresses (by replacing
    the portion before the domain with asterisks), Korean phone numbers
    (masking the middle digits) and resident registration numbers (13
    digits).  This function does not guarantee complete de‑identification
    but demonstrates the idea.

    Args:
        text: Arbitrary text potentially containing PII.

    Returns:
        A copy of the text with PII masked.
    """

    if not text:
        return text
    # Mask email addresses
    def _mask_email(match: re.Match) -> str:
        user, domain = match.group(1), match.group(2)
        return user[0] + "***@" + domain

    text = re.sub(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", _mask_email, text)
    # Mask Korean phone numbers (e.g. 010-1234-5678)
    text = re.sub(r"(\d{3})[- ]?\d{3,4}[- ]?(\d{4})", r"\1-****-\2", text)
    # Mask resident registration numbers (6 digits + 7 digits)
    text = re.sub(r"(\d{6})[- ]?(\d{7})", r"\1-*******", text)
    return text