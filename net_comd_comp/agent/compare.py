from __future__ import annotations

from typing import Dict, List

from net_comd_comp.agent.search import SemanticSearcher
from net_comd_comp.models import CompareResult, SearchHit
from net_comd_comp.ollama_client import OllamaChat, extract_json

SYSTEM_PROMPT_TEMPLATE = """You are a senior network engineer specializing in campus switching CLIs.
Target platforms (use ONLY syntax appropriate for these releases):
{platform_context}

Given a user query and retrieved documentation excerpts, produce the closest equivalent command on the target platform.

Return ONLY valid JSON:
{{
  "source_vendor": "cisco|arista|unknown",
  "target_vendor": "cisco|arista",
  "source_command": "best matching source CLI or paraphrase",
  "target_command": "equivalent target CLI",
  "explanation": "short plain-language summary",
  "differences": ["syntax or behavior difference"],
  "caveats": ["version, feature, or platform caveats"],
  "citations": ["source_name or URL references used"]
}}

Rules:
- Cisco side: Catalyst 9300, IOS XE 26.x — interface names like GigabitEthernet/TwoGigabitEthernet/TenGigabitEthernet.
- Arista side: CCS-720XP, EOS 4.36.1F — interface names like Ethernet1, Ethernet1/1.
- Prefer exact CLI syntax from the excerpts when available.
- Map IOS-XE idioms (e.g. switchport trunk allowed vlan) to EOS idioms (switchport trunk allowed vlan on Arista is similar but verify mode defaults).
- If no exact equivalent exists, give the closest alternative and explain the gap.
- Note when a feature requires a license or is not available on CCS-720XP or Catalyst 9300.
- differences and caveats may be empty arrays.
- Do not invent unsupported commands.
"""


def build_system_prompt(platform_context: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(platform_context=platform_context.strip())


def _format_hits(hits: List[SearchHit], label: str) -> str:
    if not hits:
        return f"{label}: (no excerpts retrieved)\n"
    parts = [f"{label} excerpts:"]
    for i, hit in enumerate(hits[:6], 1):
        c = hit.chunk
        parts.append(
            f"[{i}] score={hit.score:.3f} source={c.source_name} ({c.source_type})\n"
            f"hint: {c.command_hint}\n{c.text[:900]}"
        )
    return "\n\n".join(parts)


def _resolve_direction(
    direction: str,
    query: str,
    cisco_hits: List[SearchHit],
    arista_hits: List[SearchHit],
) -> tuple[str, str]:
    d = (direction or "auto").lower()
    if d == "cisco_to_arista":
        return "cisco", "arista"
    if d == "arista_to_cisco":
        return "arista", "cisco"
    q = query.lower()
    cisco_score = cisco_hits[0].score if cisco_hits else 0.0
    arista_score = arista_hits[0].score if arista_hits else 0.0
    arista_markers = ("eos", "arista", "ethernet1", "mlag", "vxlan", "ccs-720")
    cisco_markers = ("ios", "cisco", "catalyst", "9300", "gigabitethernet", "switchport")
    if any(m in q for m in arista_markers) and not any(m in q for m in cisco_markers):
        return "arista", "cisco"
    if any(m in q for m in cisco_markers) and not any(m in q for m in arista_markers):
        return "cisco", "arista"
    if arista_score > cisco_score + 0.05:
        return "arista", "cisco"
    return "cisco", "arista"


class CommandComparator:
    def __init__(
        self,
        searcher: SemanticSearcher,
        chat: OllamaChat,
        *,
        platform_context: str = "",
    ):
        self.searcher = searcher
        self.chat = chat
        self.platform_context = platform_context

    def compare(
        self,
        query: str,
        *,
        direction: str = "auto",
    ) -> CompareResult:
        both = self.searcher.search_both(query)
        cisco_hits = both["cisco"]
        arista_hits = both["arista"]
        source_vendor, target_vendor = _resolve_direction(
            direction, query, cisco_hits, arista_hits
        )

        user_prompt = (
            f"User query: {query}\n"
            f"Requested direction: {direction}\n"
            f"Resolved translation: {source_vendor} -> {target_vendor}\n\n"
            f"{_format_hits(cisco_hits, 'Cisco')}\n\n"
            f"{_format_hits(arista_hits, 'Arista')}\n"
        )

        raw = self.chat.chat(
            [
                {
                    "role": "system",
                    "content": build_system_prompt(self.platform_context),
                },
                {"role": "user", "content": user_prompt},
            ],
            format_json=True,
            temperature=0.1,
        )
        data = extract_json(raw) or {}

        return CompareResult(
            query=query,
            direction=direction,
            source_vendor=data.get("source_vendor") or source_vendor,
            target_vendor=data.get("target_vendor") or target_vendor,
            source_command=data.get("source_command", ""),
            target_command=data.get("target_command", ""),
            explanation=data.get("explanation", ""),
            differences=list(data.get("differences") or []),
            caveats=list(data.get("caveats") or []),
            citations=list(data.get("citations") or []),
            raw_response=raw,
        )