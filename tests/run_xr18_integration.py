#!/usr/bin/env python3
import argparse
import sys
import unittest
from pathlib import Path

# Ensure project root is importable when running from tests/ on the Pi.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import test_integration_xr18 as live


def main():
    parser = argparse.ArgumentParser(description="Run live XR18 integration tests (explicit opt-in).")
    parser.add_argument("--live-xr18", action="store_true", help="Required safety flag to run live mixer tests")
    parser.add_argument("--xr18-ip", required=True, help="XR18 mixer IP")
    parser.add_argument("--xr18-bus", type=int, default=2, help="XR18 bus (1..6)")
    parser.add_argument("--xr18-test-channel", type=int, default=18, help="Safe test channel (1..18)")
    parser.add_argument("--local-port", type=int, default=9101, help="Local UDP port")
    args = parser.parse_args()

    if not args.live_xr18:
        raise SystemExit("Refusing to run: pass --live-xr18 to confirm live mixer test")

    live.LIVE_MODE = True
    live.XR18_IP = args.xr18_ip
    live.XR18_BUS = args.xr18_bus
    live.XR18_TEST_CHANNEL = args.xr18_test_channel
    live.LOCAL_PORT = args.local_port

    suite = unittest.defaultTestLoader.loadTestsFromModule(live)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
