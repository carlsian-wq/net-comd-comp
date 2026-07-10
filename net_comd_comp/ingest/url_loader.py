from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "net-comd-comp/0.1 (+documentation-ingest)",
    "Accept": "text/html,application/xhtml+xml",
}


def fetch_url_text(url: str, timeout: int = 45) -> str:
    r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body
    if not main:
        return ""
    text = main.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text