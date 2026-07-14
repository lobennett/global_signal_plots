"""Parse BIDS entities from BOLD filenames (generic — any subject label)."""
from __future__ import annotations

import re


def parse_bold_meta(filename: str) -> dict:
    """Extract bare-ID entities from a BOLD filename. Missing entities -> None."""
    def grab(key: str):
        m = re.search(rf"{key}-([A-Za-z0-9]+)", filename)
        return m.group(1) if m else None
    return {
        "subject": grab("sub"),
        "session": grab("ses"),
        "task": grab("task"),
        "run": grab("run"),
        "echo": grab("echo"),
    }
