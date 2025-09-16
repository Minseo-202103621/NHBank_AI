"""Enumerations and constants for the judge chain."""

# Mapping from severity score to human readable Korean label.
SEVERITY_LABELS: dict[int, str] = {
    0: "배임 횡령 위험 아님",
    1: "배임 횡령 의심(주의 요망)",
    2: "배임 횡령(조사 필요)",
    3: "배임 횡령 즉시 처분 필요",
}