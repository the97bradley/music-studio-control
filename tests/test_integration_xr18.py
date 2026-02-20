import time
import unittest

from faders import add_group, set_group
from state import State
from sync import sync_faders

# Safety gate: must be explicitly enabled by runner script flag.
LIVE_MODE = False
XR18_IP = None
XR18_BUS = 2
XR18_TEST_CHANNEL = 18
LOCAL_PORT = 9101
SIM_DETENTS = 1          # signed: +up / -down
STEP_SIZE = 0.01         # linear mixer units per detent
SIM_DURATION_S = 0.0     # spread simulated detents over this duration
GROUP_CHANNELS = None    # optional CSV from runner for group consistency test
LATENCY_QUERIES = 8
LATENCY_MAX_MS = 350.0
DROP_TEST_IP = "192.0.2.1"      # TEST-NET-1 unroutable example for timeout behavior
DROP_TEST_MAX_S = 6.0


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


class TestXR18Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not LIVE_MODE:
            raise unittest.SkipTest("Use tests/run_xr18_integration.py --live-xr18 to run live tests")

        if not XR18_IP:
            raise unittest.SkipTest("XR18 IP not provided")

        bus = int(XR18_BUS)
        if bus < 1 or bus > 6:
            raise unittest.SkipTest("XR18_BUS must be 1..6")

        cls.test_channel = int(XR18_TEST_CHANNEL)
        if cls.test_channel < 1 or cls.test_channel > 18:
            raise unittest.SkipTest("XR18_TEST_CHANNEL must be 1..18")

        from osc import OscClient

        cls.osc = OscClient(XR18_IP, local_port=int(LOCAL_PORT), timeout_s=2.0)
        cls.st = State(bus=bus)
        cls.st.ensure_channels(18)

        cls.group_channels = cls._parse_group_channels(GROUP_CHANNELS, cls.test_channel)
        cls.st.groups = {"test": cls.group_channels}
        cls.st.knob_to_group = {"knob1": "test"}

        # Fast preflight: require test channel to respond.
        v = cls._query_level(cls.test_channel, bus=bus)
        if v is None:
            raise unittest.SkipTest("Could not query test channel level from XR18")

        cls.st.ch_level[cls.test_channel] = float(v)
        sync_faders(cls.osc, cls.st, channels=18)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.osc.close()
        except Exception:
            pass

    @staticmethod
    def _parse_group_channels(raw, fallback):
        if not raw:
            return [fallback]
        if isinstance(raw, list):
            chans = [int(x) for x in raw]
        else:
            chans = [int(x.strip()) for x in str(raw).split(",") if x.strip()]
        chans = [c for c in chans if 1 <= c <= 18]
        return chans or [fallback]

    @classmethod
    def _query_level(cls, ch: int, bus=None):
        b = cls.st.bus if bus is None else int(bus)
        addr = f"/ch/{ch:02d}/mix/{b:02d}/level"
        v = cls.osc.query(addr, tries=2)
        return None if v is None else float(v)

    def _restore_channel(self, ch: int, value: float):
        set_group(self.osc, self.st, "test", value)
        time.sleep(0.1)
        sync_faders(self.osc, self.st, channels=18)
        restored = self.st.ch_level[ch]
        self.assertAlmostEqual(restored, value, places=3)

    def test_connectivity_query_level(self):
        v = self._query_level(self.test_channel)
        self.assertIsNotNone(v, "XR18 did not return level query")

    def test_simulated_knob_turn_changes_value_and_restores(self):
        ch = self.test_channel
        before = self.st.ch_level[ch]

        detents = int(SIM_DETENTS)
        sign = 1 if detents >= 0 else -1
        steps = abs(detents)
        step_delta = sign * float(STEP_SIZE)
        total_delta = detents * float(STEP_SIZE)
        expected = _clamp(before + total_delta)

        if steps > 0:
            interval = max(0.0, float(SIM_DURATION_S)) / steps
            for _ in range(steps):
                add_group(self.osc, self.st, "test", step_delta)
                if interval > 0:
                    time.sleep(interval)

        time.sleep(0.1)
        sync_faders(self.osc, self.st, channels=18)
        after = self.st.ch_level[ch]

        self.assertAlmostEqual(
            after,
            expected,
            delta=0.005,
            msg=(
                f"Expected ~{expected:.3f} after simulated move "
                f"(detents={SIM_DETENTS}, step={STEP_SIZE}, duration_s={SIM_DURATION_S}); got {after:.3f}"
            ),
        )

        self._restore_channel(ch, before)

    def test_boundary_clamp_low_high(self):
        ch = self.test_channel
        before = self.st.ch_level[ch]

        set_group(self.osc, self.st, "test", -0.25)
        time.sleep(0.1)
        sync_faders(self.osc, self.st, channels=18)
        low = self.st.ch_level[ch]
        self.assertGreaterEqual(low, 0.0)
        self.assertLessEqual(low, 0.01)

        set_group(self.osc, self.st, "test", 1.25)
        time.sleep(0.1)
        sync_faders(self.osc, self.st, channels=18)
        high = self.st.ch_level[ch]
        self.assertLessEqual(high, 1.0)
        self.assertGreaterEqual(high, 0.99)

        self._restore_channel(ch, before)

    def test_multi_step_trajectory_monotonic(self):
        ch = self.test_channel
        before = self.st.ch_level[ch]

        steps = 5
        inc = abs(float(STEP_SIZE))
        values = []
        for _ in range(steps):
            add_group(self.osc, self.st, "test", inc)
            time.sleep(0.05)
            sync_faders(self.osc, self.st, channels=18)
            values.append(self.st.ch_level[ch])

        monotonic = all(values[i] <= values[i + 1] + 1e-6 for i in range(len(values) - 1))
        self.assertTrue(monotonic, f"Expected monotonic increase, got: {values}")

        self._restore_channel(ch, before)

    def test_group_consistency_multi_channel(self):
        if len(self.group_channels) < 2:
            self.skipTest("Provide --group-channels with 2+ channels to run group consistency test")

        before = {ch: self._query_level(ch) for ch in self.group_channels}
        for ch, v in before.items():
            self.assertIsNotNone(v, f"No query response for group channel {ch}")

        set_group(self.osc, self.st, "test", 0.42)
        time.sleep(0.1)

        after = {ch: self._query_level(ch) for ch in self.group_channels}
        for ch, v in after.items():
            self.assertIsNotNone(v, f"No query response for group channel {ch} after write")

        vals = list(after.values())
        span = max(vals) - min(vals)
        self.assertLessEqual(span, 0.01, f"Expected group channels to match closely, got {after}")

        # restore to original per channel
        for ch, v in before.items():
            addr = f"/ch/{ch:02d}/mix/{self.st.bus:02d}/level"
            self.osc.send(addr, float(v))
        time.sleep(0.15)

    def test_bus_correctness_targeted_write(self):
        alt_bus = 1 if self.st.bus != 1 else 2
        ch = self.test_channel

        primary_before = self._query_level(ch, self.st.bus)
        alt_before = self._query_level(ch, alt_bus)
        if primary_before is None or alt_before is None:
            self.skipTest("Could not query both target and alt bus for correctness test")

        set_group(self.osc, self.st, "test", _clamp(primary_before + 0.02))
        time.sleep(0.1)
        primary_after = self._query_level(ch, self.st.bus)
        alt_after = self._query_level(ch, alt_bus)

        self.assertIsNotNone(primary_after)
        self.assertIsNotNone(alt_after)
        self.assertNotAlmostEqual(primary_before, primary_after, delta=0.005)
        self.assertAlmostEqual(alt_before, alt_after, delta=0.005)

        self._restore_channel(ch, primary_before)

    def test_query_latency_budget(self):
        ch = self.test_channel
        samples = []
        for _ in range(int(LATENCY_QUERIES)):
            t0 = time.time()
            v = self._query_level(ch)
            dt_ms = (time.time() - t0) * 1000.0
            self.assertIsNotNone(v, "Latency test query returned None")
            samples.append(dt_ms)

        p95 = sorted(samples)[max(0, int(len(samples) * 0.95) - 1)]
        self.assertLessEqual(
            p95,
            float(LATENCY_MAX_MS),
            msg=f"p95 query latency {p95:.1f}ms exceeds budget {LATENCY_MAX_MS:.1f}ms; samples={samples}",
        )

    def test_idempotent_restore_two_cycles(self):
        ch = self.test_channel
        baseline = self.st.ch_level[ch]

        for _ in range(2):
            add_group(self.osc, self.st, "test", 0.02)
            time.sleep(0.05)
            sync_faders(self.osc, self.st, channels=18)
            set_group(self.osc, self.st, "test", baseline)
            time.sleep(0.05)
            sync_faders(self.osc, self.st, channels=18)
            cur = self.st.ch_level[ch]
            self.assertAlmostEqual(cur, baseline, places=3)

    def test_timeout_behavior_on_unreachable_peer(self):
        from osc import OscClient

        bad = OscClient(DROP_TEST_IP, local_port=int(LOCAL_PORT) + 11, timeout_s=1.0)
        try:
            t0 = time.time()
            v = bad.query(f"/ch/{self.test_channel:02d}/mix/{self.st.bus:02d}/level", tries=2)
            dt = time.time() - t0
            self.assertIsNone(v, "Expected no response from unreachable test IP")
            self.assertLessEqual(
                dt,
                float(DROP_TEST_MAX_S),
                msg=f"Unreachable peer timeout took too long: {dt:.2f}s (budget {DROP_TEST_MAX_S}s)",
            )
        finally:
            bad.close()


if __name__ == "__main__":
    unittest.main()
