#!/usr/bin/env bash
# setup.sh — create venv and install dependencies (Linux/macOS)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

cd "${PROJECT_ROOT}"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install Python 3.10+ first." >&2
    exit 1
fi

python3 -m venv "${VENV_DIR}"
"${PIP}" install --upgrade pip
"${PIP}" install -r requirements.txt

echo "Setup complete."
echo "  Pull models: ./scripts/pull_models.sh"
echo "  Launch app:  ./scripts/launch.sh"