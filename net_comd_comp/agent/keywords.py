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


def related_phrases(query: str, *, target_vendor: str | None = None) -> list[str]:
    """Cross-vendor and synonym phrases to improve target-side retrieval."""
    q = re.sub(r"\s+", " ", query.strip().lower())
    related: list[str] = []

    if "redirect" in q:
        related.extend(
            [
                "no ip icmp redirect",
                "ip icmp redirect",
                "icmp redirect",
                "icmp redirects",
            ]
        )
        if q.startswith("no "):
            related.append("no ip redirects")

    if "portfast" in q or "bpduguard" in q:
        related.extend(
            [
                "spanning-tree portfast",
                "spanning-tree edge-port bpduguard default",
                "spanning-tree edge-port bpduguard",
                "spanning-tree bpduguard",
            ]
        )

    if target_vendor == "arista" and q.startswith("no ip "):
        # Cisco "no ip X" often maps to Arista "no ip icmp X" or "no ip X"
        tail = q[6:].strip()
        if tail and "icmp" not in tail:
            related.append(f"no ip icmp {tail}")

    return list(dict.fromkeys(p for p in related if p and p != q))


def search_phrases(query: str, *, target_vendor: str | None = None) -> list[str]:
    phrases: list[str] = []
    for base in phrase_variants(query):
        phrases.append(base)
        phrases.extend(related_phrases(base, target_vendor=target_vendor))
    return list(dict.fromkeys(phrases))