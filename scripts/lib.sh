#!/usr/bin/env bash
# Shared helpers for net-comd-comp bash scripts.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${PROJECT_ROOT}/config.yaml"
VENV_DIR="${PROJECT_ROOT}/venv"
STREAMLIT="${VENV_DIR}/bin/streamlit"
PIP="${VENV_DIR}/bin/pip"
PYTHON="${VENV_DIR}/bin/python"

config_get() {
    local key="$1"
    local default="$2"
    if [[ -f "${CONFIG_PATH}" ]]; then
        local val
        val="$(grep -E "^[[:space:]]*${key}:[[:space:]]*" "${CONFIG_PATH}" | head -1 \
            | sed -E 's/^[[:space:]]*[^:]+:[[:space:]]*//' \
            | sed -E 's/[[:space:]]+#.*$//' \
            | tr -d "\"'")"
        if [[ -n "${val}" ]]; then
            echo "${val}"
            return 0
        fi
    fi
    echo "${default}"
}

ollama_api_up() {
    curl -sf --max-time 3 "http://127.0.0.1:11434/api/version" >/dev/null 2>&1
}

find_ollama() {
    if command -v ollama >/dev/null 2>&1; then
        command -v ollama
        return 0
    fi
    for candidate in /usr/local/bin/ollama /usr/bin/ollama; do
        if [[ -x "${candidate}" ]]; then
            echo "${candidate}"
            return 0
        fi
    done
    return 1
}

ensure_ollama() {
    if ollama_api_up; then
        return 0
    fi

    if command -v systemctl >/dev/null 2>&1; then
        if systemctl is-active --quiet ollama 2>/dev/null; then
            :
        else
            systemctl start ollama 2>/dev/null || sudo systemctl start ollama 2>/dev/null || true
        fi
        local i
        for i in $(seq 1 22); do
            if ollama_api_up; then
                return 0
            fi
            sleep 2
        done
    fi

    local ollama_bin
    if ! ollama_bin="$(find_ollama)"; then
        echo "Ollama not found. Install from https://ollama.com or enable the systemd service." >&2
        return 1
    fi

    echo "Starting ollama serve..."
    nohup "${ollama_bin}" serve >/dev/null 2>&1 &
    local i
    for i in $(seq 1 22); do
        if ollama_api_up; then
            return 0
        fi
        sleep 2
    done

    echo "Ollama API did not respond on :11434 within 45s." >&2
    return 1
}

streamlit_up() {
    local port="$1"
    curl -sf --max-time 3 "http://127.0.0.1:${port}/" >/dev/null 2>&1
}

require_venv() {
    if [[ ! -x "${STREAMLIT}" ]]; then
        echo "Virtualenv not ready. Run: ./scripts/setup.sh" >&2
        exit 1
    fi
}