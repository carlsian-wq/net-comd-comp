from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def normalize_cli(command: str) -> str:
    text = (command or "").replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", text.strip().lower())


def query_matches_command(query: str, command: str) -> bool:
    """True when the query is exactly the command or clearly contains it."""
    q = normalize_cli(query)
    c = normalize_cli(command)
    if not q or not c:
        return False
    if q == c:
        return True
    return f" {c} " in f" {q} "


def command_mappings(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(cfg.get("command_mappings") or [])


def find_curated_mapping(
    query: str,
    *,
    direction: str = "auto",
    cfg: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Return a curated Cisco↔Arista mapping when the query matches config."""
    if not normalize_cli(query):
        return None

    d = (direction or "auto").lower()
    for entry in command_mappings(cfg):
        cisco = entry.get("cisco", "")
        arista = entry.get("arista", "")
        notes = (entry.get("notes") or "").strip()
        bidirectional = bool(entry.get("bidirectional", True))

        if cisco and query_matches_command(query, cisco) and d in ("auto", "cisco_to_arista"):
            return {
                "source_vendor": "cisco",
                "target_vendor": "arista",
                "source_command": entry.get("cisco", query),
                "target_command": entry.get("arista", ""),
                "explanation": notes or f"Curated mapping for {entry.get('cisco', query)}.",
                "differences": list(entry.get("differences") or []),
                "caveats": list(entry.get("caveats") or []),
                "reject_targets": list(entry.get("reject_targets") or []),
                "mapping_id": entry.get("id", ""),
            }

        if (
            bidirectional
            and arista
            and query_matches_command(query, arista)
            and d in ("auto", "arista_to_cisco")
        ):
            return {
                "source_vendor": "arista",
                "target_vendor": "cisco",
                "source_command": entry.get("arista", query),
                "target_command": entry.get("cisco", ""),
                "explanation": notes or f"Curated mapping for {entry.get('arista', query)}.",
                "differences": list(entry.get("differences") or []),
                "caveats": list(entry.get("caveats") or []),
                "reject_targets": list(entry.get("reject_targets") or []),
                "mapping_id": entry.get("id", ""),
            }

    return None


def target_rejected_by_curated(curated: Dict[str, Any], target_command: str) -> bool:
    """True when a curated mapping explicitly blocks this LLM suggestion."""
    for reject in curated.get("reject_targets") or []:
        if query_matches_command(target_command, reject):
            return True
    return False


def curated_search_phrases(cfg: Dict[str, Any], query: str) -> List[str]:
    """Extra phrases to retrieve when a curated mapping exists for this query."""
    match = find_curated_mapping(query, cfg=cfg)
    if not match:
        return []
    phrases = [match["target_command"], match["source_command"], query]
    return list(dict.fromkeys(p for p in phrases if p))