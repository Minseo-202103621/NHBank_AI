"""Utility functions for calibrating judge output."""

from .types import SEVERITY_LABELS


def map_severity_label(severity: int) -> str:
    """Translate a numeric severity score to a label.

    If the provided severity is not in the known range it defaults to
    "배임 횡령 위험 아님".
    """

    return SEVERITY_LABELS.get(severity, SEVERITY_LABELS[0])