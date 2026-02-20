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


def _add_case(suite, method_name: str):
    suite.addTest(live.TestXR18Integration(method_name))


def main():
    parser = argparse.ArgumentParser(
        description="Run selected live XR18 integration tests (flag-per-test style)."
    )
    parser.add_argument("--xr18-ip", required=True, help="XR18 mixer IP")
    parser.add_argument("--local-port", type=int, default=9101, help="Local UDP port")

    # Per-test selectors (short + long)
    parser.add_argument("-a", "--connectivity", action="store_true", help="Run connectivity query test")
    parser.add_argument("-b", "--linear", nargs=2, metavar=("DETENTS", "DURATION_S"), help="Run linear motion test")
    parser.add_argument("-c", "--backforth", nargs=2, metavar=("DETENTS", "DURATION_S"), help="Run back-and-forth motion test")
    parser.add_argument("-d", "--boundary", action="store_true", help="Run low/high clamp boundary test")
    parser.add_argument("-e", "--group", metavar="CSV", help="Run group consistency test with channels CSV (e.g. 6,7,8)")
    parser.add_argument("-f", "--buscheck", action="store_true", help="Run targeted bus correctness test")
    parser.add_argument("-g", "--latency", nargs=2, metavar=("QUERIES", "MAX_MS"), help="Run query latency budget test")
    parser.add_argument("-i", "--idempotent", action="store_true", help="Run idempotent restore test")
    parser.add_argument("-j", "--timeout", nargs=2, metavar=("IP", "MAX_S"), help="Run unreachable-peer timeout behavior test")

    args = parser.parse_args()

    # Base config
    live.XR18_IP = args.xr18_ip
    live.LOCAL_PORT = args.local_port

    suite = unittest.TestSuite()

    if args.connectivity:
        _add_case(suite, "test_connectivity_query_level")

    if args.linear:
        live.SIM_DETENTS = int(args.linear[0])
        live.SIM_DURATION_S = float(args.linear[1])
        _add_case(suite, "test_simulated_linear_motion_and_restore")

    if args.backforth:
        live.SIM_DETENTS = int(args.backforth[0])
        live.SIM_DURATION_S = float(args.backforth[1])
        _add_case(suite, "test_simulated_back_and_forth_motion_and_restore")

    if args.boundary:
        _add_case(suite, "test_boundary_clamp_low_high")

    if args.group:
        live.GROUP_CHANNELS = args.group
        _add_case(suite, "test_group_consistency_multi_channel")

    if args.buscheck:
        _add_case(suite, "test_bus_correctness_targeted_write")

    if args.latency:
        live.LATENCY_QUERIES = int(args.latency[0])
        live.LATENCY_MAX_MS = float(args.latency[1])
        _add_case(suite, "test_query_latency_budget")

    if args.idempotent:
        _add_case(suite, "test_idempotent_restore_two_cycles")

    if args.timeout:
        live.DROP_TEST_IP = args.timeout[0]
        live.DROP_TEST_MAX_S = float(args.timeout[1])
        _add_case(suite, "test_timeout_behavior_on_unreachable_peer")

    if suite.countTestCases() == 0:
        raise SystemExit(
            "No tests selected. Example: "
            "python3 tests/run_xr18_integration.py --xr18-ip 192.168.50.62 -a -b -12 2.0 -d"
        )

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
