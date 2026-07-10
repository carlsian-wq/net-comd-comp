from __future__ import annotations

from typing import Any, Dict, List

from net_comd_comp.agent.cli_skeleton import (
    best_line_skeleton,
    cli_skeleton,
    structural_tokens,
)
from net_comd_comp.agent.keywords import keyword_overlap_score, query_tokens
from net_comd_comp.agent.mappings import (
    find_curated_mapping,
    normalize_cli,
    target_rejected_by_curated,
)
from net_comd_comp.agent.search import SemanticSearcher
from net_comd_comp.index.store import CommandIndex
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
- Use ONLY commands and syntax supported by the retrieved excerpts for the target vendor.
- If target-vendor excerpts are missing or unrelated, set target_command to "" and explain that no equivalent was found in indexed docs.
- NEVER answer with a command from a different feature area than the user query.
- NEVER reuse an example from these instructions unless it matches the user query.
- Prefer exact CLI syntax from the excerpts when available.
- Documentation placeholders (<user>, <removed>, WORD, interface names) differ between vendors.
  Match on command structure (keywords, order, options), not placeholder labels.
- SNMPv3 examples: Cisco may show "user ... v3 auth sha ... priv aes256";
  Arista uses "snmp-server user ... v3 auth sha ... priv aes" — treat aes/aes256 as equivalent options.
- Honor curated command_mappings from configuration when provided in the user prompt.
- Cisco "spanning-tree portfast bpduguard default" maps to Arista "spanning-tree edge-port bpduguard default".
- When excerpts show a target command, you MUST return it in target_command even if naming differs slightly.
- If no exact equivalent exists, give the closest alternative from excerpts and explain the gap.
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
        cli_line = best_line_skeleton(f"{c.command_hint}\n{c.text}")
        cli_note = f"cli skeleton: {cli_line}\n" if cli_line else ""
        parts.append(
            f"[{i}] score={hit.score:.3f} source={c.source_name} ({c.source_type})\n"
            f"hint: {c.command_hint}\n{cli_note}{c.text[:900]}"
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


def _target_overlap_ok(
    query: str,
    target_command: str,
    target_hits: List[SearchHit],
    *,
    curated: Dict[str, Any] | None = None,
) -> bool:
    if not target_command.strip():
        return True

    if curated:
        if normalize_cli(target_command) == normalize_cli(curated["target_command"]):
            return True
        if target_rejected_by_curated(curated, target_command):
            return False

    tokens = query_tokens(query)
    if keyword_overlap_score(target_command, tokens) >= 0.2:
        return True
    target_tokens = set(structural_tokens(target_command))
    if tokens and len(set(tokens) & target_tokens) / len(tokens) >= 0.45:
        return True
    if target_hits:
        excerpt = f"{target_hits[0].chunk.command_hint}\n{target_hits[0].chunk.text}"
        if keyword_overlap_score(excerpt, tokens) >= 0.2:
            return True
        hay_tokens = set(structural_tokens(excerpt))
        if tokens and len(set(tokens) & hay_tokens) / len(tokens) >= 0.45:
            return True
        if cli_skeleton(query) and cli_skeleton(query) in cli_skeleton(excerpt):
            return True
    return False


class CommandComparator:
    def __init__(
        self,
        searcher: SemanticSearcher,
        chat: OllamaChat,
        command_index: CommandIndex,
        *,
        platform_context: str = "",
        cfg: Dict[str, Any] | None = None,
    ):
        self.searcher = searcher
        self.chat = chat
        self.command_index = command_index
        self.platform_context = platform_context
        self.cfg = cfg or {}

    def compare(
        self,
        query: str,
        *,
        direction: str = "auto",
    ) -> CompareResult:
        curated = find_curated_mapping(query, direction=direction, cfg=self.cfg)
        if curated:
            return CompareResult(
                query=query,
                direction=direction,
                source_vendor=curated["source_vendor"],
                target_vendor=curated["target_vendor"],
                source_command=curated["source_command"],
                target_command=curated["target_command"],
                explanation=curated["explanation"],
                differences=list(curated.get("differences") or []),
                caveats=list(curated.get("caveats") or []),
                citations=["config.yaml command_mappings"],
                confidence="curated",
                retrieval_note=f"Curated mapping ({curated.get('mapping_id', '')})",
            )

        both = self.searcher.search_both(query)
        cisco_hits = both["cisco"]
        arista_hits = both["arista"]
        source_vendor, target_vendor = _resolve_direction(
            direction, query, cisco_hits, arista_hits
        )
        target_hits = arista_hits if target_vendor == "arista" else cisco_hits
        source_hits = cisco_hits if source_vendor == "cisco" else arista_hits

        target_indexed = self.command_index.count(target_vendor) > 0
        source_conf = self.searcher.retrieval_confidence(query, source_hits)
        target_conf = self.searcher.retrieval_confidence(query, target_hits)

        if not target_indexed:
            return CompareResult(
                query=query,
                direction=direction,
                source_vendor=source_vendor,
                target_vendor=target_vendor,
                source_command=query,
                target_command="",
                explanation=(
                    f"No {target_vendor.title()} documentation is indexed yet. "
                    "Run **Ingest sources from config** (include the EOS PDF) and "
                    "**Build semantic index** before comparing commands."
                ),
                differences=[],
                caveats=[],
                citations=[],
                confidence="none",
                retrieval_note=f"{target_vendor} chunk count is 0 in the index.",
            )

        if target_conf == "none" and not target_hits:
            return CompareResult(
                query=query,
                direction=direction,
                source_vendor=source_vendor,
                target_vendor=target_vendor,
                source_command=query,
                target_command="",
                explanation=(
                    "No relevant documentation excerpt was found for this query on the "
                    f"{target_vendor.title()} side. The indexed sources may be incomplete — "
                    "ensure vendor PDFs are ingested, not just HTML index pages."
                ),
                differences=[],
                caveats=[
                    "Try **Replace existing documentation** + re-ingest to load full PDF command references."
                ],
                citations=[h.chunk.source_name for h in target_hits[:3]],
                confidence="none",
                retrieval_note="Target-vendor retrieval confidence too low; skipped LLM synthesis.",
            )

        curated_hint = ""
        if curated:
            curated_hint = (
                f"\nCurated mapping (use this target_command): "
                f"{curated['source_command']} -> {curated['target_command']}\n"
                f"Notes: {curated['explanation']}\n"
            )

        user_prompt = (
            f"User query: {query}\n"
            f"Requested direction: {direction}\n"
            f"Resolved translation: {source_vendor} -> {target_vendor}\n"
            f"Source retrieval confidence: {source_conf}\n"
            f"Target retrieval confidence: {target_conf}\n"
            f"{curated_hint}\n"
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
            temperature=0.05,
        )
        data = extract_json(raw) or {}

        overlap_curated = find_curated_mapping(query, direction=direction, cfg=self.cfg)
        target_command = data.get("target_command", "")
        if target_command and not _target_overlap_ok(
            query, target_command, target_hits, curated=overlap_curated
        ):
            target_command = ""
            data["explanation"] = (
                (data.get("explanation") or "")
                + " The model suggestion was rejected because it did not match the query "
                "or retrieved documentation."
            ).strip()

        late_curated = find_curated_mapping(query, direction=direction, cfg=self.cfg)
        if late_curated:
            target_command = late_curated["target_command"]
            data["explanation"] = late_curated["explanation"]
            data["differences"] = list(late_curated.get("differences") or [])
            data["caveats"] = list(late_curated.get("caveats") or [])
            return CompareResult(
                query=query,
                direction=direction,
                source_vendor=late_curated["source_vendor"],
                target_vendor=late_curated["target_vendor"],
                source_command=late_curated["source_command"],
                target_command=target_command,
                explanation=late_curated["explanation"],
                differences=list(late_curated.get("differences") or []),
                caveats=list(late_curated.get("caveats") or []),
                citations=["config.yaml command_mappings"],
                raw_response=raw,
                confidence="curated",
                retrieval_note=f"Curated mapping ({late_curated.get('mapping_id', '')})",
            )

        confidence = target_conf
        if not target_command:
            confidence = "none"

        return CompareResult(
            query=query,
            direction=direction,
            source_vendor=data.get("source_vendor") or source_vendor,
            target_vendor=data.get("target_vendor") or target_vendor,
            source_command=data.get("source_command", "") or query,
            target_command=target_command,
            explanation=data.get("explanation", ""),
            differences=list(data.get("differences") or []),
            caveats=list(data.get("caveats") or []),
            citations=list(data.get("citations") or []),
            raw_response=raw,
            confidence=confidence,
            retrieval_note=f"source={source_conf}, target={target_conf}",
        )