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
# Run application
# ----------------------------------------

[[ -n "${XTRACE:-}" ]] || clear

PYVER=$("$PYTHON" --version 2>&1 | sed 's/Python //')
echo -e "========================================"
echo -e "  Starting CYPY..."
echo -e "  $PYTHON - $PYVER"
echo -e "========================================\n"

if "$PYTHON" -m cypy; then
    exit 0
else
    code=$?
    echo -e "\n[!] CYPY exited with error."
    exit $code
fi
