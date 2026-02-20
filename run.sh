#!/usr/bin/env bash
set -euo pipefail

########################################
# XR18 Personal Monitor Endpoint Boot
########################################

APP_DIR="/home/the97bradley/music-studio-control"
VENV_DIR="$APP_DIR/osc-env"
REQ_FILE="$APP_DIR/requirements.txt"

STAMP_REQ="$VENV_DIR/.requirements.sha256"
STAMP_TOOLING="$VENV_DIR/.tooling.upgraded"

log() {
  echo "[run.sh] $*"
}

cd "$APP_DIR" || {
  echo "[run.sh] ERROR: App directory missing"
  exit 1
}

########################################
# Ensure python + venv support exists
########################################

command -v python3 >/dev/null 2>&1 || {
  log "ERROR: python3 not installed"
  exit 1
}

python3 -c "import venv" >/dev/null 2>&1 || {
  log "ERROR: python3-venv missing"
  exit 1
}

########################################
# Create venv if needed
########################################

if [ ! -d "$VENV_DIR" ]; then
  log "Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

# Activate
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

########################################
# Ensure pip exists
########################################

if ! python -m pip --version >/dev/null 2>&1; then
  log "Bootstrapping pip (ensurepip)..."
  python -m ensurepip --upgrade
fi

########################################
# Upgrade tooling once
########################################

if [ ! -f "$STAMP_TOOLING" ]; then
  log "Upgrading pip/setuptools/wheel (one-time)..."
  python -m pip install --upgrade pip setuptools wheel
  touch "$STAMP_TOOLING"
fi

########################################
# Install requirements only if changed
########################################

if [ ! -f "$REQ_FILE" ]; then
  log "ERROR: requirements.txt missing"
  exit 1
fi

REQ_SHA="$(sha256sum "$REQ_FILE" | awk '{print $1}')"
OLD_SHA=""

if [ -f "$STAMP_REQ" ]; then
  OLD_SHA="$(cat "$STAMP_REQ" || true)"
fi

if [ "$REQ_SHA" != "$OLD_SHA" ]; then
  log "Installing/updating requirements..."
  python -m pip install -r "$REQ_FILE"
  echo "$REQ_SHA" > "$STAMP_REQ"
else
  log "Requirements unchanged."
fi

########################################
# Environment Defaults
########################################

export XR18_IP="${XR18_IP:-192.168.50.62}"
export XR18_BUS="${XR18_BUS:-2}"
export LOCAL_PORT="${LOCAL_PORT:-9100}"
export PYTHONUNBUFFERED=1

########################################
# Launch Application
########################################

log "Starting XR18 endpoint..."
exec python3 main.py
