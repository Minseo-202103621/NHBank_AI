"""Simple content filter.

The policy filter inspects text for the presence of banned terms and
disallows further processing if any are found.  In production you would
use a more sophisticated classifier or integrate policy documents.
"""

BANNED_TERMS = [
    "폭력",  # violence
    "위협",  # threat
    "사기",  # fraud
    "허위제보",  # false report
]


def is_allowed(text: str) -> bool:
    """Return True if the text passes the content filter.

    Args:
        text: Arbitrary user input.

    Returns:
        True if no banned terms appear in the text, False otherwise.
    """

    for term in BANNED_TERMS:
        if term in text:
            return False
    return True