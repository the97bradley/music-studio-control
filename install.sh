#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/osc-env"
REQ_FILE="$APP_DIR/requirements.txt"
SERVICE_NAME="xr18pm.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

echo "[install] Installing OS dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip

echo "[install] Creating virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

echo "[install] Activating venv and installing Python dependencies..."
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r "$REQ_FILE"

echo "[install] Ensuring run.sh is executable..."
chmod +x "$APP_DIR/run.sh"

echo "[install] Creating systemd service..."
sudo tee "$SERVICE_PATH" > /dev/null <<EOF
[Unit]
Description=XR18 Personal Monitor Endpoint
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/run.sh
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo "[install] Enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

echo "[install] Installation complete."
echo "Reboot with: sudo reboot"
