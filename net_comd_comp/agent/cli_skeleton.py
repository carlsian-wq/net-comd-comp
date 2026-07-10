from __future__ import annotations

import re
from typing import Iterable

# Doc placeholders: <user>, {word}, WORD, x.x.x.x, interface tokens, etc.
ANGLE_PLACEHOLDER = re.compile(r"<[^>]+>")
BRACE_PLACEHOLDER = re.compile(r"\{[^}]+\}")
DOC_ELLIPSIS = re.compile(r"\.\.\.")
INTERFACE_REF = re.compile(
    r"\b(?:gigabitethernet|two-gigabitethernet|tengigabitethernet|fastethernet|"
    r"ethernet|port-channel|vlan|loopback|mgmt|management)\S*",
    re.I,
)
IP_PLACEHOLDER = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){0,3}(?:\.\d{1,3})?\b")
REMOVED_MARKERS = re.compile(r"\b(?:removed|optional|required)\b", re.I)

# Cross-vendor token aliases (syntax skeleton, not literal values).
TOKEN_ALIASES: dict[str, str] = {
    "aes256": "aes",
    "aes-256": "aes",
    "aes192": "aes",
    "aes-192": "aes",
    "aes128": "aes",
    "aes-128": "aes",
    "sha1": "sha",
    "sha-1": "sha",
    "sha224": "sha",
    "sha-224": "sha",
    "sha256": "sha",
    "sha-256": "sha",
    "sha384": "sha",
    "sha-512": "sha",
    "des56": "des",
    "snmpv3": "v3",
    "snmpv2c": "snmp",
}

# Too generic to anchor SQL prefilter.
WEAK_ANCHOR_TOKENS = frozenset(
    {
        "user",
        "group",
        "auth",
        "priv",
        "the",
        "and",
        "for",
        "with",
        "mode",
        "command",
        "configure",
        "configuration",
        "server",
        "no",
        "ip",
    }
)


def strip_cli_placeholders(text: str) -> str:
    """Remove documentation placeholders so CLI keywords remain."""
    s = (text or "").replace("\n", " ").replace("\r", " ")
    s = ANGLE_PLACEHOLDER.sub(" ", s)
    s = BRACE_PLACEHOLDER.sub(" ", s)
    s = DOC_ELLIPSIS.sub(" ", s)
    s = REMOVED_MARKERS.sub(" ", s)
    s = INTERFACE_REF.sub(" ", s)
    s = IP_PLACEHOLDER.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_token(token: str) -> str:
    t = token.lower().strip(".,;:|")
    return TOKEN_ALIASES.get(t, t)


def structural_tokens(text: str) -> list[str]:
    """Meaningful CLI tokens after placeholder stripping and alias folding."""
    cleaned = strip_cli_placeholders(text).lower()
    raw = re.findall(r"[a-z0-9][a-z0-9-]*", cleaned)
    out: list[str] = []
    seen: set[str] = set()
    for token in raw:
        norm = normalize_token(token)
        if len(norm) < 2 or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return out


def cli_skeleton(text: str) -> str:
    return " ".join(structural_tokens(text))


TOKEN_MATCH_WEIGHT: dict[str, float] = {
    "user": 0.45,
    "group": 0.45,
    "server": 0.35,
    "auth": 1.0,
    "priv": 1.0,
}


def weighted_token_match(query_tokens: list[str], hay_tokens: list[str]) -> float:
    hay_set = set(hay_tokens)
    total = 0.0
    hit = 0.0
    for token in query_tokens:
        weight = TOKEN_MATCH_WEIGHT.get(token, 1.0)
        total += weight
        if token in hay_set:
            hit += weight
    return hit / total if total else 0.0


def retrieval_anchors(tokens: list[str], *, max_anchors: int = 3) -> list[str]:
    """Context-aware anchors for SQL prefilter (keep loose to survive placeholders)."""
    if "v3" in tokens and "user" in tokens:
        picks = ["v3", "snmp"]
        for token in ("auth", "sha", "priv", "aes"):
            if token in tokens:
                picks.append(token)
        return list(dict.fromkeys(picks))[:max_anchors]
    return anchor_tokens(tokens, max_anchors=max_anchors)


def anchor_tokens(tokens: Iterable[str], *, max_anchors: int = 4) -> list[str]:
    """Pick distinctive tokens for SQL prefiltering."""
    ranked: list[tuple[int, str]] = []
    for token in tokens:
        if token in WEAK_ANCHOR_TOKENS:
            continue
        score = len(token)
        if token.isdigit():
            score -= 2
        if "-" in token:
            score += 1
        ranked.append((score, token))
    ranked.sort(reverse=True)
    anchors = [t for _, t in ranked[:max_anchors]]
    if not anchors:
        anchors = list(tokens)[:max_anchors]
    return anchors


def extract_cli_lines(text: str) -> list[str]:
    """Pull likely CLI syntax lines out of prose documentation chunks."""
    lines: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if len(line) < 8:
            continue
        lower = line.lower()
        if lower.startswith(("switch(config)", "switch#", "device#", "router(config)", "r1(config)")):
            lines.append(line)
            continue
        if re.match(
            r"^(snmp-server|no snmp-server|user\b|username\b|ip snmp|show snmp)\b",
            lower,
        ):
            lines.append(line)
            continue
        if re.match(r"^[•\-]\s*(md5|sha|aes|des)\b", lower):
            lines.append(line)
    return lines


def token_subsequence_score(query_tokens: list[str], hay_tokens: list[str]) -> float:
    if not query_tokens:
        return 0.0
    qi = 0
    for token in hay_tokens:
        if qi < len(query_tokens) and token == query_tokens[qi]:
            qi += 1
    return qi / len(query_tokens)


def best_line_skeleton(text: str) -> str:
    """Best CLI skeleton from a chunk — prefers syntax lines over section titles."""
    candidates = extract_cli_lines(text)
    if not candidates:
        return cli_skeleton(text)
    return max(candidates, key=lambda line: len(structural_tokens(line)))


def snmp_prefix_variants(query: str) -> list[str]:
    """Cisco/Arista SNMP user syntax often differs only by snmp-server prefix."""
    tokens = structural_tokens(query)
    if "user" not in tokens or "v3" not in tokens:
        return []
    skeleton = " ".join(tokens)
    variants: list[str] = []
    if not skeleton.startswith("snmp-server"):
        variants.append(f"snmp-server {skeleton}")
    if skeleton.startswith("snmp-server "):
        variants.append(skeleton[len("snmp-server ") :])
    return variants


def skeleton_search_phrases(query: str) -> list[str]:
    """Phrases for retrieval when docs use different placeholder text."""
    phrases: list[str] = []
    skeleton = cli_skeleton(query)
    if skeleton and len(skeleton) >= 6:
        phrases.append(skeleton)

    tokens = structural_tokens(query)
    if len(tokens) >= 3:
        # Sliding windows of structural keywords (ignore placeholder gaps).
        for width in (6, 5, 4, 3):
            if len(tokens) < width:
                continue
            for i in range(0, len(tokens) - width + 1):
                phrases.append(" ".join(tokens[i : i + width]))

    phrases.extend(snmp_prefix_variants(query))
    return list(dict.fromkeys(p for p in phrases if p and len(p) >= 5))