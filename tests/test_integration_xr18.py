import os
import time
import unittest

from faders import add_group, set_group
from state import State
from sync import sync_faders


@unittest.skipUnless(os.environ.get("RUN_XR18_INTEGRATION") == "1", "Set RUN_XR18_INTEGRATION=1 to run live XR18 tests")
class TestXR18Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        xr18_ip = os.environ.get("XR18_IP")
        if not xr18_ip:
            raise unittest.SkipTest("XR18_IP is required for integration tests")

        bus = int(os.environ.get("XR18_BUS", "2"))
        if bus < 1 or bus > 6:
            raise unittest.SkipTest("XR18_BUS must be 1..6")

        cls.test_channel = int(os.environ.get("XR18_TEST_CHANNEL", "18"))
        if cls.test_channel < 1 or cls.test_channel > 18:
            raise unittest.SkipTest("XR18_TEST_CHANNEL must be 1..18")

        from osc import OscClient  # local import so non-live test runs don't require runtime deps here

        cls.osc = OscClient(xr18_ip, local_port=int(os.environ.get("LOCAL_PORT", "9101")), timeout_s=2.0)
        cls.st = State(bus=bus)
        cls.st.ensure_channels(18)
        cls.st.groups = {"test": [cls.test_channel]}
        cls.st.knob_to_group = {"knob1": "test"}

        # Seed local state from mixer
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

        # Simulate one clockwise detent (+0.03 by default style)
        add_group(self.osc, self.st, "test", 0.03)
        time.sleep(0.1)
        sync_faders(self.osc, self.st, channels=18)
        after = self.st.ch_level[ch]

        self.assertNotEqual(before, after, "Expected channel level to change after simulated knob turn")

        # Restore original value so test is safe for repeated runs
        set_group(self.osc, self.st, "test", before)
        time.sleep(0.1)
        sync_faders(self.osc, self.st, channels=18)
        restored = self.st.ch_level[ch]

        self.assertAlmostEqual(restored, before, places=3)


if __name__ == "__main__":
    unittest.main()
