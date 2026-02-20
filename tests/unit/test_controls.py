import tempfile
import unittest

from app.config.controls import apply_controls_config
from app.core.state import State

try:
    import yaml  # noqa: F401
    HAS_YAML = True
except Exception:
    HAS_YAML = False


@unittest.skipUnless(HAS_YAML, "PyYAML not installed")
class TestControlsConfig(unittest.TestCase):
    def test_apply_valid_config(self):
        st = State(bus=2)
        st.ensure_channels(18)

        yaml_text = """
groups:
  vox: [1]
  band: [2, 3, 4]
knob_to_group:
  knob1: vox
  knob2: band
knob_step: 0.05
"""

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=True) as f:
            f.write(yaml_text)
            f.flush()
            apply_controls_config(st, f.name)

        self.assertEqual(st.groups["vox"], [1])
        self.assertEqual(st.knob_to_group["knob2"], "band")
        self.assertEqual(st.knob_step, 0.05)

    def test_invalid_channel_raises(self):
        st = State(bus=2)
        st.ensure_channels(18)

        yaml_text = """
groups:
  bad: [99]
"""

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=True) as f:
            f.write(yaml_text)
            f.flush()
            with self.assertRaises(ValueError):
                apply_controls_config(st, f.name)


if __name__ == "__main__":
    unittest.main()
