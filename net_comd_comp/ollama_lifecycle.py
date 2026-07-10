"""Ensure Ollama API server is reachable."""

from __future__ import annotations

import os
import platform
import shutil
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


def _find_ollama_binary() -> str | None:
    found = shutil.which("ollama")
    if found:
        return found
    for path in ("/usr/local/bin/ollama", "/usr/bin/ollama"):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _start_ollama_serve(binary: str) -> None:
    subprocess.Popen(
        [binary, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _ensure_ollama_linux(wait_seconds: int) -> bool:
    if shutil.which("systemctl"):
        for cmd in (
            ["systemctl", "start", "ollama"],
            ["sudo", "systemctl", "start", "ollama"],
        ):
            try:
                subprocess.run(cmd, capture_output=True, timeout=15, check=False)
            except (subprocess.TimeoutExpired, OSError):
                pass
            deadline = time.time() + min(wait_seconds, 20)
            while time.time() < deadline:
                if ollama_api_up():
                    return True
                time.sleep(2)

    binary = _find_ollama_binary()
    if not binary:
        return False
    _start_ollama_serve(binary)
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if ollama_api_up():
            return True
        time.sleep(2)
    return False


def _ensure_ollama_windows(wait_seconds: int) -> bool:
    ollama_cli = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Programs",
        "Ollama",
        "ollama.exe",
    )
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
        if ollama_api_up():
            return True
        time.sleep(2)
    return False


def ensure_ollama_server(base_url: str = DEFAULT_BASE_URL, wait_seconds: int = 45) -> bool:
    if ollama_api_up(base_url):
        return True
    system = platform.system()
    if system == "Windows":
        return _ensure_ollama_windows(wait_seconds)
    if system == "Linux":
        return _ensure_ollama_linux(wait_seconds)
    binary = _find_ollama_binary()
    if not binary:
        return False
    _start_ollama_serve(binary)
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if ollama_api_up(base_url):
            return True
        time.sleep(2)
    return False