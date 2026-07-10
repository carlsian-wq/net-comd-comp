from __future__ import annotations

import re

STOP_WORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "on",
        "for",
        "to",
        "and",
        "or",
        "is",
        "in",
        "at",
        "of",
        "with",
        "configure",
        "configuration",
        "command",
        "mode",
    }
)


def query_tokens(query: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9-]+", query.lower())
    return [t for t in tokens if len(t) >= 2 and t not in STOP_WORDS]


def keyword_overlap_score(text: str, tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    hay = text.lower()
    hits = sum(1 for token in tokens if token in hay)
    return hits / len(tokens)


def phrase_variants(query: str) -> list[str]:
    """CLI phrase variants for exact-ish database lookup."""
    q = re.sub(r"\s+", " ", query.strip().lower())
    variants = [q]
    if q.startswith("no "):
        variants.append(q[3:].strip())
    else:
        variants.append(f"no {q}")
    return list(dict.fromkeys(v for v in variants if v))