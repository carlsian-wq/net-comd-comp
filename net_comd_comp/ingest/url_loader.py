from __future__ import annotations

import hashlib
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from net_comd_comp.ingest.pdf_loader import extract_pdf_text

DEFAULT_HEADERS = {
    "User-Agent": "net-comd-comp/0.1 (+documentation-ingest)",
    "Accept": "text/html,application/xhtml+xml,application/pdf",
}


def is_pdf_url(url: str, entry_type: str | None = None) -> bool:
    if entry_type == "pdf":
        return True
    path = url.split("?", 1)[0].lower()
    return path.endswith(".pdf")


def fetch_url_text(url: str, timeout: int = 60) -> str:
    r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    r.raise_for_status()
    content_type = (r.headers.get("Content-Type") or "").lower()
    if "pdf" in content_type or is_pdf_url(url):
        return extract_pdf_text_from_bytes(r.content)
    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    main = (
        soup.find(id="fw-content")
        or soup.find("main")
        or soup.find("article")
        or soup.find(class_="book")
        or soup.body
    )
    if not main:
        return ""
    text = main.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def extract_pdf_text_from_bytes(data: bytes) -> str:
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        return extract_pdf_text(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def fetch_pdf_text_cached(url: str, cache_dir: Path, timeout: int = 180) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    cached = cache_dir / f"{digest}.pdf"
    if not cached.is_file():
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        r.raise_for_status()
        cached.write_bytes(r.content)
    return extract_pdf_text(cached)