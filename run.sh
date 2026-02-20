#!/usr/bin/env bash
set -euo pipefail

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
  source "$VENV/bin/activate"
  pip install -r requirements.txt
else
  source "$VENV/bin/activate"
fi

source osc-env/bin/activate

# Required env
export XR18_IP="${XR18_IP:-192.168.50.62}"
export XR18_BUS="${XR18_BUS:-2}"      
export LOCAL_PORT="${LOCAL_PORT:-9100}" 

python3 main.py
