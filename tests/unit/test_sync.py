import unittest

from app.core.state import State
from app.core.sync import sync_faders


class FakeOsc:
    def __init__(self, responses):
        self.responses = responses

    def query(self, address, tries=2):
        return self.responses.get(address)


class TestSync(unittest.TestCase):
    def test_sync_success_updates_levels(self):
        st = State(bus=2)
        st.ensure_channels(2)

        responses = {
            "/ch/01/mix/02/level": 0.4,
            "/ch/02/mix/02/level": 0.7,
        }
        osc = FakeOsc(responses)

        ok = sync_faders(osc, st, channels=2)

        self.assertTrue(ok)
        self.assertEqual(st.ch_level[1], 0.4)
        self.assertEqual(st.ch_level[2], 0.7)

    def test_sync_partial_failure_returns_false(self):
        st = State(bus=2)
        st.ensure_channels(2)

        responses = {
            "/ch/01/mix/02/level": 0.4,
            "/ch/02/mix/02/level": None,
        }
        osc = FakeOsc(responses)

        ok = sync_faders(osc, st, channels=2)

        self.assertFalse(ok)
        self.assertEqual(st.ch_level[1], 0.4)


if __name__ == "__main__":
    unittest.main()
