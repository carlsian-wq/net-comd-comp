#!/usr/bin/env bash
# launch.sh — start Net Command Comparator (Streamlit) with Ollama ready.
#
# Usage:
#   ./scripts/launch.sh              # foreground (good for systemd / tmux)
#   ./scripts/launch.sh --detach   # background process
#   ./scripts/launch.sh --open-browser   # open local browser (desktop Linux)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

PORT=""
DETACH=false
OPEN_BROWSER=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --detach | -d)
            DETACH=true
            shift
            ;;
        --open-browser)
            OPEN_BROWSER=true
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Usage: $0 [--detach] [--open-browser] [--port N]" >&2
            exit 1
            ;;
    esac
done

PORT="${PORT:-$(config_get port 8503)}"
HOST="$(config_get host 0.0.0.0)"
URL="http://127.0.0.1:${PORT}"
LOG_DIR="${PROJECT_ROOT}/data"
LOG_FILE="${LOG_DIR}/launch.log"
PID_FILE="${LOG_DIR}/streamlit.pid"

mkdir -p "${LOG_DIR}"
require_venv
ensure_ollama

cd "${PROJECT_ROOT}"

if streamlit_up "${PORT}"; then
    echo "Streamlit already running at ${URL}"
else
    CMD=("${STREAMLIT}" run app.py --server.port "${PORT}" --server.address "${HOST}")
    if [[ "${DETACH}" == true ]]; then
        echo "Starting Streamlit in background on ${HOST}:${PORT}"
        nohup "${CMD[@]}" >>"${LOG_FILE}" 2>&1 &
        echo $! >"${PID_FILE}"
        for _ in $(seq 1 90); do
            if streamlit_up "${PORT}"; then
                break
            fi
            sleep 0.5
        done
        if ! streamlit_up "${PORT}"; then
            echo "Streamlit did not start within 45s. See ${LOG_FILE}" >&2
            exit 1
        fi
    else
        echo "Starting Streamlit on ${HOST}:${PORT} (Ctrl+C to stop)"
        if [[ "${OPEN_BROWSER}" == true ]]; then
            (sleep 2 && (xdg-open "${URL}" 2>/dev/null || sensible-browser "${URL}" 2>/dev/null || true)) &
        fi
        exec "${CMD[@]}"
    fi
fi

echo "Net Command Comparator: ${URL}"
PUBLIC_URL="$(config_get public_url "${URL}")"
if [[ "${PUBLIC_URL}" != "${URL}" ]]; then
    echo "Configured public URL: ${PUBLIC_URL}"
fi

if [[ "${DETACH}" == true ]]; then
    echo "Log: ${LOG_FILE}"
    echo "Stop: kill \$(cat ${PID_FILE})"
fi