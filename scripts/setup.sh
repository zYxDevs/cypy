#!/usr/bin/env bash

set -euo pipefail
[ -n "${XTRACE:-}" ] && set -x

echo -e "========================================"
echo -e "  Setting up CYPY..."
echo -e "========================================\n"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR"/.. && pwd)"

PYTHON=""
VENV="${VIRTUAL_ENV:-}"

if [[ -d "${ROOT_DIR}/.venv" ]]; then
    VENV="${ROOT_DIR}/.venv"
    PYTHON="$VENV/bin/python"
elif [[ -d "${ROOT_DIR}/venv" ]]; then
    VENV="${ROOT_DIR}/venv"
    PYTHON="$VENV/bin/python"
fi

# ----------------------------------------
# Check Python installation
# ----------------------------------------

if [[ -n "$VENV" ]]; then
    echo "[+] Found virtual environment: ${VENV}"

    version=$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    IFS='.' read -r major minor <<< "$version"

    if (( major < 3 || (major == 3 && minor < 8) )); then
        echo "[!] Current Python version is ${major}.${minor}, but supported version is 3.8+." >&2
        exit 1
    fi

    PYTHON="$VENV/bin/python"
    echo "[+] Using $("$PYTHON" --version 2>&1) from virtual environment"
else
    echo "[!] No virtual environment found"

    if command -v python3 >/dev/null 2>&1; then
        PYTHON="$(command -v python3)"
    else
        echo "[!] Python not found. Please install Python 3.8+ first." >&2

        _should_exit=1
        # Fallback and search for python command if available
        if command -v python >/dev/null 2>&1; then
            PYTHON="$(command -v python)"
            _should_exit=0
        fi
        [ $_should_exit -eq 1 ] && exit 1
    fi
fi

# ----------------------------------------
# Setup virtual environment
# ----------------------------------------

if [[ -z "$VENV" ]]; then
    echo "[+] Setting up venv for the application..."
    "${PYTHON:-python3}" -m venv .venv
    VENV="${ROOT_DIR}/.venv"

    PYTHON="$VENV/bin/python"

    # Setup pip and install dependencies
    echo "[+] Upgrading pip..."
    "$PYTHON" -m pip install --upgrade pip

    echo "[+] Installing Python dependencies..."
    "$PYTHON" -m pip install -e .
fi

# ----------------------------------------
# Setup .env
# ----------------------------------------

if [[ ! -f ".env" ]]; then
    echo "[i] No .env found. Copying from .env.example..."
    if [[ -f ".env.example" ]]; then
        cp --verbose .env.example .env
        echo "[+] .env created. Please edit it with your API key."
        ${EDITOR:-nano} .env
    else
        echo "[!] No .env.example found. Please create .env manually." >&2
        # No exit here, just warning
    fi
fi
