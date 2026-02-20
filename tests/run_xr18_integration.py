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
    parser.add_argument("--xr18-ip", required=True, help="XR18 mixer IP")
    parser.add_argument("--local-port", type=int, default=9101, help="Local UDP port")
    parser.add_argument("--sim-detents", type=int, default=1, help="Signed simulated detents (+up / -down)")
    parser.add_argument("--sim-duration-s", type=float, default=0.0, help="Spread detents over this many seconds")
    parser.add_argument("--group-channels", default="", help="CSV channels for group consistency test (e.g. 6,7,8)")
    parser.add_argument("--latency-queries", type=int, default=8, help="Number of queries for latency test")
    parser.add_argument("--latency-max-ms", type=float, default=350.0, help="Max p95 query latency budget in ms")
    parser.add_argument("--drop-test-ip", default="192.0.2.1", help="Unreachable IP used for timeout/dead-link behavior test")
    parser.add_argument("--drop-test-max-s", type=float, default=6.0, help="Max allowed seconds for unreachable-peer timeout test")
    args = parser.parse_args()

    live.XR18_IP = args.xr18_ip
    live.LOCAL_PORT = args.local_port
    live.SIM_DETENTS = args.sim_detents
    live.SIM_DURATION_S = args.sim_duration_s
    live.GROUP_CHANNELS = args.group_channels
    live.LATENCY_QUERIES = args.latency_queries
    live.LATENCY_MAX_MS = args.latency_max_ms
    live.DROP_TEST_IP = args.drop_test_ip
    live.DROP_TEST_MAX_S = args.drop_test_max_s

    suite = unittest.defaultTestLoader.loadTestsFromModule(live)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
