"""Ensure Ollama API server is reachable on Windows."""

from __future__ import annotations

import platform
import subprocess
import time

import requests

DEFAULT_BASE_URL = "http://localhost:11434"


def ollama_api_up(base_url: str = DEFAULT_BASE_URL, timeout: float = 3) -> bool:
    try:
        r = requests.get(f"{base_url.rstrip('/')}/api/version", timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False


def ensure_ollama_server(base_url: str = DEFAULT_BASE_URL, wait_seconds: int = 45) -> bool:
    if ollama_api_up(base_url):
        return True
    if platform.system() != "Windows":
        return False
    import os

    ollama_cli = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
    if not os.path.isfile(ollama_cli):
        return False
    subprocess.Popen(
        [ollama_cli, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if ollama_api_up(base_url):
            return True
        time.sleep(2)
    return False