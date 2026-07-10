from __future__ import annotations

import re
from typing import Iterable, List

CLI_PREFIXES = (
    "configure",
    "interface",
    "show",
    "no ",
    "ip ",
    "vlan",
    "router",
    "hostname",
    "enable",
    "exit",
    "switchport",
    "spanning-tree",
    "ntp",
    "logging",
    "snmp",
    "aaa ",
    "line ",
    "banner",
    "access-list",
    "route-map",
    "policy-map",
    "class-map",
)

MAX_CHUNK_CHARS = 1800
MIN_CHUNK_CHARS = 40


def _looks_like_cli(line: str) -> bool:
    s = line.strip().lower()
    if not s or s.startswith("#"):
        return False
    return s.startswith(CLI_PREFIXES) or bool(re.match(r"^[a-z][a-z0-9-]+(\s|$)", s))


def _command_hint(text: str) -> str:
    for line in text.splitlines():
        if _looks_like_cli(line):
            return line.strip()[:240]
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    return first[:240]


def chunk_text(text: str) -> List[tuple[str, str]]:
    """Return (text, command_hint) chunks from raw documentation text."""
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    blocks = re.split(r"\n\s*\n", text)
    chunks: List[tuple[str, str]] = []
    buf: List[str] = []

    def flush() -> None:
        if not buf:
            return
        joined = "\n".join(buf).strip()
        if len(joined) >= MIN_CHUNK_CHARS:
            chunks.append((joined, _command_hint(joined)))
        buf.clear()

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if len(block) > MAX_CHUNK_CHARS:
            flush()
            for i in range(0, len(block), MAX_CHUNK_CHARS):
                piece = block[i : i + MAX_CHUNK_CHARS].strip()
                if len(piece) >= MIN_CHUNK_CHARS:
                    chunks.append((piece, _command_hint(piece)))
            continue
        candidate = "\n".join(buf + [block]) if buf else block
        if len(candidate) > MAX_CHUNK_CHARS:
            flush()
            buf.append(block)
        else:
            buf.append(block)
    flush()
    return chunks


def dedupe_chunks(chunks: Iterable[tuple[str, str]]) -> List[tuple[str, str]]:
    seen: set[str] = set()
    out: List[tuple[str, str]] = []
    for text, hint in chunks:
        key = re.sub(r"\s+", " ", text.strip().lower())[:500]
        if key in seen:
            continue
        seen.add(key)
        out.append((text, hint))
    return out