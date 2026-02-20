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

        ok = sync_faders(cls.osc, cls.st, channels=18)
        if not ok:
            raise unittest.SkipTest("Could not complete initial mixer sync")

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

        add_group(self.osc, self.st, "test", 0.03)
        time.sleep(0.1)
        sync_faders(self.osc, self.st, channels=18)
        after = self.st.ch_level[ch]

        self.assertNotEqual(before, after, "Expected channel level to change after simulated knob turn")

        set_group(self.osc, self.st, "test", before)
        time.sleep(0.1)
        sync_faders(self.osc, self.st, channels=18)
        restored = self.st.ch_level[ch]

        self.assertAlmostEqual(restored, before, places=3)


if __name__ == "__main__":
    unittest.main()
