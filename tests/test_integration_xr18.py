import unittest
import time

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
STEP_SIZE = 0.03         # linear mixer units per detent
SIM_DURATION_S = 0.0     # spread simulated detents over this duration


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
        cls.st.groups = {"test": [cls.test_channel]}
        cls.st.knob_to_group = {"knob1": "test"}

        # Fast, realistic preflight: require test channel to respond.
        addr = f"/ch/{cls.test_channel:02d}/mix/{bus:02d}/level"
        v = cls.osc.query(addr, tries=2)
        if v is None:
            raise unittest.SkipTest("Could not query test channel level from XR18")

        # Seed baseline level for test channel; full 18ch sync is optional.
        cls.st.ch_level[cls.test_channel] = float(v)
        sync_faders(cls.osc, cls.st, channels=18)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.osc.close()
        except Exception:
            pass

    def test_connectivity_query_level(self):
        addr = f"/ch/{self.test_channel:02d}/mix/{self.st.bus:02d}/level"
        v = self.osc.query(addr, tries=2)
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

        if steps == 0:
            # no movement requested
            pass
        else:
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

        set_group(self.osc, self.st, "test", before)
        time.sleep(0.1)
        sync_faders(self.osc, self.st, channels=18)
        restored = self.st.ch_level[ch]

        self.assertAlmostEqual(restored, before, places=3)


if __name__ == "__main__":
    unittest.main()
