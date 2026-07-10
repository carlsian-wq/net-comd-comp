from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional

from net_comd_comp.config import ROOT, load_config, vendor_sources
from net_comd_comp.ingest.chunker import chunk_text, dedupe_chunks
from net_comd_comp.ingest.quality import filter_chunks, is_usable_text
from net_comd_comp.ingest.pdf_loader import extract_pdf_text
from net_comd_comp.ingest.url_loader import (
    fetch_pdf_text_cached,
    fetch_url_text,
    is_pdf_url,
)
from net_comd_comp.index.store import CommandIndex

ProgressFn = Optional[Callable[[str], None]]


def _log(fn: ProgressFn, msg: str) -> None:
    if fn:
        fn(msg)


def _resolve_pdf(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (ROOT / p).resolve()


def ingest_vendor(
    index: CommandIndex,
    vendor: str,
    cfg: Dict,
    on_progress: ProgressFn = None,
    *,
    replace: bool = False,
) -> int:
    sources = vendor_sources(cfg, vendor)
    added = 0

    if replace:
        removed = index.clear_vendor(vendor)
        _log(on_progress, f"Cleared {removed} existing {vendor} chunks")

    for pdf_path in sources["pdfs"]:
        path = _resolve_pdf(pdf_path)
        if not path.is_file():
            _log(on_progress, f"Skip missing PDF: {path}")
            continue
        _log(on_progress, f"Ingesting {vendor} PDF: {path.name}")
        text = extract_pdf_text(path)
        chunks = filter_chunks(dedupe_chunks(chunk_text(text)))
        n = index.upsert_chunks(
            vendor=vendor,
            source_name=path.stem,
            source_type="pdf",
            source_ref=str(path),
            chunks=chunks,
        )
        added += n

    pdf_cache = ROOT / "data" / "sources" / "cache"

    for entry in sources["urls"]:
        if isinstance(entry, str):
            name, url, entry_type = entry, entry, None
        else:
            name = entry.get("name") or entry.get("url", "web")
            url = entry.get("url", "")
            entry_type = entry.get("type")
        if not url:
            continue
        source_type = "pdf" if is_pdf_url(url, entry_type) else "url"
        _log(on_progress, f"Ingesting {vendor} {source_type.upper()}: {name}")
        try:
            if source_type == "pdf":
                text = fetch_pdf_text_cached(url, pdf_cache)
            else:
                text = fetch_url_text(url)
        except Exception as exc:
            _log(on_progress, f"Source failed ({name}): {exc}")
            continue
        if not is_usable_text(text):
            _log(
                on_progress,
                f"Skipped unusable page ({name}) — use PDF or print-friendly source",
            )
            continue
        chunks = filter_chunks(dedupe_chunks(chunk_text(text)))
        if not chunks:
            _log(on_progress, f"No usable chunks ({name})")
            continue
        n = index.upsert_chunks(
            vendor=vendor,
            source_name=name,
            source_type=source_type,
            source_ref=url,
            chunks=chunks,
        )
        added += n

    return added


def ingest_all_sources(
    index: CommandIndex,
    cfg: Optional[Dict] = None,
    on_progress: ProgressFn = None,
    *,
    replace: bool = False,
) -> Dict[str, int]:
    cfg = cfg or load_config()
    return {
        "cisco": ingest_vendor(index, "cisco", cfg, on_progress, replace=replace),
        "arista": ingest_vendor(index, "arista", cfg, on_progress, replace=replace),
    }