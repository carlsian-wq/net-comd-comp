from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import requests

DEFAULT_BASE_URL = "http://localhost:11434"


def is_ollama_available(base_url: str = DEFAULT_BASE_URL) -> bool:
    try:
        r = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False


def list_models(base_url: str = DEFAULT_BASE_URL) -> list[str]:
    try:
        r = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
        if r.status_code != 200:
            return []
        return [m.get("name", "") for m in r.json().get("models", [])]
    except requests.RequestException:
        return []


def model_installed(name: str, base_url: str = DEFAULT_BASE_URL) -> bool:
    root = name.split(":")[0]
    installed = list_models(base_url)
    return any(n == name or n.startswith(f"{root}:") for n in installed)


def extract_json(text: str) -> Optional[dict]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


class OllamaChat:
    def __init__(
        self,
        model: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        num_thread: Optional[int] = None,
        timeout: int = 120,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.num_thread = num_thread if num_thread and num_thread > 0 else None
        self.timeout = timeout

    def _options(self, **extra: Any) -> Dict[str, Any]:
        opts = dict(extra)
        if self.num_thread is not None:
            opts["num_thread"] = self.num_thread
        return opts

    def chat(
        self,
        messages: list[dict],
        *,
        format_json: bool = False,
        temperature: float = 0.2,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": self._options(temperature=temperature),
        }
        if format_json:
            payload["format"] = "json"
        r = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")