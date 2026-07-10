from __future__ import annotations

import re

JUNK_PATTERNS = (
    r"javascript is disabled",
    r"please enable javascript",
    r"couldn.?t load",
    r"required part of this site",
    r"disable any ad blockers",
    r"try using a different browser",
)

JUNK_RE = re.compile("|".join(JUNK_PATTERNS), re.IGNORECASE)


def is_usable_text(text: str, *, min_chars: int = 80) -> bool:
    """Reject SPA shells, JS error pages, and near-empty fetches."""
    stripped = (text or "").strip()
    if len(stripped) < min_chars:
        return False
    if JUNK_RE.search(stripped):
        return False
    alnum = sum(1 for c in stripped if c.isalnum())
    if alnum / max(len(stripped), 1) < 0.15:
        return False
    return True


def filter_chunks(chunks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return [(text, hint) for text, hint in chunks if is_usable_text(text, min_chars=40)]