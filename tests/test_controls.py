import json
import tempfile
import unittest

from controls import apply_controls_config
from state import State


class TestControlsConfig(unittest.TestCase):
    def test_apply_valid_config(self):
        st = State(bus=2)
        st.ensure_channels(18)

        payload = {
            "groups": {"vox": [1], "band": [2, 3, 4]},
            "knob_to_group": {"knob1": "vox", "knob2": "band"},
            "knob_step": {"knob1": 0.05, "knob2": 0.02},
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=True) as f:
            json.dump(payload, f)
            f.flush()
            apply_controls_config(st, f.name)

        self.assertEqual(st.groups["vox"], [1])
        self.assertEqual(st.knob_to_group["knob2"], "band")
        self.assertEqual(st.knob_step["knob1"], 0.05)

    def test_invalid_channel_raises(self):
        st = State(bus=2)
        st.ensure_channels(18)

        payload = {"groups": {"bad": [99]}}

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=True) as f:
            json.dump(payload, f)
            f.flush()
            with self.assertRaises(ValueError):
                apply_controls_config(st, f.name)


if __name__ == "__main__":
    unittest.main()
