#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/the97bradley/music-studio-control"
VENV_DIR="$APP_DIR/osc-env"
REQ_FILE="$APP_DIR/requirements.txt"

log() { echo "[run.sh] $*"; }

cd "$APP_DIR"

# --- Ensure Python exists ---
if ! command -v python3 >/dev/null 2>&1; then
  log "ERROR: python3 not installed."
  exit 1
fi

# --- Ensure venv exists ---
if [ ! -d "$VENV_DIR" ]; then
  log "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

# --- Activate venv ---
source "$VENV_DIR/bin/activate"

# --- Ensure pip works ---
python -m ensurepip --upgrade >/dev/null 2>&1 || true

# --- Install dependencies if missing ---
if ! python -c "import pythonosc" >/dev/null 2>&1; then
  log "Installing Python dependencies..."
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install -r "$REQ_FILE"
fi

# --- Default environment variables ---
export XR18_IP="${XR18_IP:-192.168.50.62}"
export XR18_BUS="${XR18_BUS:-2}"
export LOCAL_PORT="${LOCAL_PORT:-9100}"
export PYTHONUNBUFFERED=1

log "Starting XR18 endpoint..."
exec python3 main.py
