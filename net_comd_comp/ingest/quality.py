from __future__ import annotations

BROWSER_SHELL_MARKERS = (
    "javascript is disabled in your browser",
    "please enable javascript to proceed",
    "a required part of this site couldn't load",
    "a required part of this site could not load",
    "disable any ad blockers",
    "try using a different browser",
)


def looks_like_browser_shell(text: str) -> bool:
    """Detect Arista/Cisco SPA error stubs — not random 'couldn't load' in PDFs."""
    lower = text.lower()
    hits = sum(1 for marker in BROWSER_SHELL_MARKERS if marker in lower)
    if len(text) < 500:
        return hits >= 1
    if len(text) < 2000:
        return hits >= 2
    return False


def is_usable_text(
    text: str,
    *,
    min_chars: int = 80,
    trusted_pdf: bool = False,
) -> bool:
    """Reject SPA shells, JS error pages, and near-empty fetches."""
    stripped = (text or "").strip()
    if len(stripped) < min_chars:
        return False
    if trusted_pdf:
        return True
    if looks_like_browser_shell(stripped):
        return False
    alnum = sum(1 for c in stripped if c.isalnum())
    if alnum / max(len(stripped), 1) < 0.15:
        return False
    return True


def filter_chunks(chunks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return [
        (text, hint)
        for text, hint in chunks
        if is_usable_text(text, min_chars=40) and not looks_like_browser_shell(text)
    ]