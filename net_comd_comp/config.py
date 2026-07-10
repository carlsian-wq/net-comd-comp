from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config.yaml"


def load_config(path: Path | str | None = None) -> Dict[str, Any]:
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with cfg_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_path(cfg: Dict[str, Any], *parts: str) -> Path:
    base = ROOT
    return (base.joinpath(*parts)).resolve()


def vendor_sources(cfg: Dict[str, Any], vendor: str) -> Dict[str, List]:
    sources = cfg.get("sources", {}).get(vendor, {}) or {}
    return {
        "pdfs": list(sources.get("pdfs") or []),
        "urls": list(sources.get("urls") or []),
    }


def platform_context(cfg: Dict[str, Any]) -> str:
    """Human-readable platform scope for the comparison agent."""
    platforms = cfg.get("platforms") or {}
    lines: List[str] = []
    for key in ("cisco", "arista"):
        p = platforms.get(key) or {}
        if not p:
            continue
        product = p.get("product", key)
        os_name = p.get("os", "")
        notes = (p.get("notes") or "").strip()
        lines.append(f"- {product} ({os_name})")
        if notes:
            lines.append(f"  {notes}")
    return "\n".join(lines) if lines else "Cisco IOS XE and Arista EOS campus switches."