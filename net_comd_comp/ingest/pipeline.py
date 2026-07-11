from __future__ import annotations

import re
from pathlib import Path
from typing import BinaryIO, Callable, Dict, List, Optional, Union

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

UPLOAD_ROOT = ROOT / "data" / "sources" / "uploads"
UPLOAD_EXTENSIONS = {".pdf", ".txt", ".md"}


def _log(fn: ProgressFn, msg: str) -> None:
    if fn:
        fn(msg)


def _resolve_pdf(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (ROOT / p).resolve()


def uploads_dir(vendor: str) -> Path:
    """Per-vendor folder for user-uploaded training docs."""
    path = UPLOAD_ROOT / vendor.lower().strip()
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_upload_name(filename: str) -> str:
    """Basename only; strip path traversal and unsafe characters."""
    name = Path(filename or "upload.bin").name
    name = re.sub(r"[^\w.\- ()[\]]+", "_", name).strip("._ ")
    return name or "upload.bin"


def save_uploaded_file(
    vendor: str,
    filename: str,
    data: Union[bytes, BinaryIO],
) -> Path:
    """Persist an uploaded file under data/sources/uploads/{vendor}/."""
    dest_dir = uploads_dir(vendor)
    safe = safe_upload_name(filename)
    dest = dest_dir / safe
    if hasattr(data, "read"):
        payload = data.read()
    else:
        payload = data
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    dest.write_bytes(payload)
    return dest


def list_uploaded_files(vendor: Optional[str] = None) -> List[Path]:
    """List saved upload files for one vendor or all vendors."""
    if vendor:
        folder = uploads_dir(vendor)
        if not folder.is_dir():
            return []
        return sorted(
            p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in UPLOAD_EXTENSIONS
        )
    results: List[Path] = []
    if not UPLOAD_ROOT.is_dir():
        return results
    for child in sorted(UPLOAD_ROOT.iterdir()):
        if child.is_dir():
            results.extend(list_uploaded_files(child.name))
    return results


def _read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_file_text(path: Path) -> tuple[str, str]:
    """Return (text, source_type) for a local pdf/txt/md file."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path), "pdf"
    if suffix in (".txt", ".md"):
        return _read_text_file(path), "txt"
    raise ValueError(f"Unsupported file type: {path.suffix}")


def ingest_file(
    index: CommandIndex,
    path: Path | str,
    vendor: str,
    on_progress: ProgressFn = None,
) -> int:
    """Chunk a local PDF/TXT and upsert into the command index."""
    file_path = Path(path)
    if not file_path.is_file():
        _log(on_progress, f"Skip missing file: {file_path}")
        return 0
    if file_path.suffix.lower() not in UPLOAD_EXTENSIONS:
        _log(on_progress, f"Skip unsupported type: {file_path.name}")
        return 0

    _log(on_progress, f"Ingesting {vendor} file: {file_path.name}")
    try:
        text, source_type = extract_file_text(file_path)
    except Exception as exc:
        _log(on_progress, f"Failed to read {file_path.name}: {exc}")
        return 0

    trusted = source_type == "pdf"
    if not is_usable_text(text, trusted_pdf=trusted):
        _log(on_progress, f"Skipped unusable content: {file_path.name}")
        return 0

    chunks = filter_chunks(dedupe_chunks(chunk_text(text)))
    if not chunks:
        _log(on_progress, f"No usable chunks: {file_path.name}")
        return 0

    return index.upsert_chunks(
        vendor=vendor,
        source_name=file_path.stem,
        source_type=source_type,
        source_ref=str(file_path.resolve()),
        chunks=chunks,
    )


def ingest_uploads(
    index: CommandIndex,
    vendor: str,
    on_progress: ProgressFn = None,
) -> int:
    """Ingest all files under data/sources/uploads/{vendor}/."""
    added = 0
    for path in list_uploaded_files(vendor):
        added += ingest_file(index, path, vendor, on_progress=on_progress)
    return added


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
        added += ingest_file(index, path, vendor, on_progress=on_progress)

    # User uploads (PDF/TXT) — always re-ingested with config sources
    added += ingest_uploads(index, vendor, on_progress=on_progress)

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
        if not is_usable_text(text, trusted_pdf=(source_type == "pdf")):
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
    **_ignored: object,
) -> Dict[str, int]:
    """Ingest all configured sources. Pass replace=True to clear each vendor first."""
    cfg = cfg or load_config()
    return {
        "cisco": ingest_vendor(index, "cisco", cfg, on_progress, replace=replace),
        "arista": ingest_vendor(index, "arista", cfg, on_progress, replace=replace),
    }