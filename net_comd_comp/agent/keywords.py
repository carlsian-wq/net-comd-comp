from __future__ import annotations

import re

from net_comd_comp.agent.cli_skeleton import (
    cli_skeleton,
    skeleton_search_phrases,
    structural_tokens,
)

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
    tokens = structural_tokens(query)
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

    # ICMP hardening — redirects and unreachables are separate mappings on Arista.
    if "icmp redirect" not in q and re.search(r"\bredirects?\b", q):
        related.extend(["no ip icmp redirect", "ip icmp redirect"])

    if "rate-limit-unreachable" in q or (
        "unreachable" in q and "redirect" not in q
    ):
        related.extend(
            [
                "ip icmp rate-limit-unreachable",
                "rate-limit-unreachable",
                "no ip unreachables",
            ]
        )

    if "portfast" in q or "bpduguard" in q:
        related.extend(
            [
                "spanning-tree portfast",
                "spanning-tree edge-port bpduguard default",
                "spanning-tree edge-port bpduguard",
                "spanning-tree bpduguard",
            ]
        )

    return list(dict.fromkeys(p for p in related if p and p != q))


def search_phrases(query: str, *, target_vendor: str | None = None) -> list[str]:
    phrases: list[str] = []
    for base in phrase_variants(query):
        phrases.append(base)
        phrases.extend(related_phrases(base, target_vendor=target_vendor))
    phrases.extend(skeleton_search_phrases(query))
    skeleton = cli_skeleton(query)
    if skeleton:
        phrases.append(skeleton)
    return list(dict.fromkeys(phrases))