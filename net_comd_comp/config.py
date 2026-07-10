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