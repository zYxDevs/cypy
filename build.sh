#!/usr/bin/env bash

set -euo pipefail
[ -n "${XTRACE:-}" ] && set -x

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

PYTHON=""
VENV="${VIRTUAL_ENV:-}"

# ----------------------------------------
# Run setup
# ----------------------------------------

bash "${ROOT_DIR}/scripts/setup.sh"

# ----------------------------------------
# Detect Python / virtual environment
# ----------------------------------------

if [[ -d "${ROOT_DIR}/.venv" ]]; then
    VENV="${ROOT_DIR}/.venv"
    PYTHON="$VENV/bin/python"
elif [[ -d "${ROOT_DIR}/venv" ]]; then
    VENV="${ROOT_DIR}/venv"
    PYTHON="$VENV/bin/python"
fi

# ----------------------------------------
# Build application
# ----------------------------------------

echo -e "\n========================================"
echo -e "  CYPY Build Script"
echo -e "========================================\n"

echo "[i] Running build..."

if "$PYTHON" build.py; then
    echo -e "\n========================================"
    echo -e "  Build completed! Check releases/ folder"
    echo -e "========================================"
    exit 0
else
    code=$?
    echo -e "\n[!] Build failed."
    exit $code
fi
