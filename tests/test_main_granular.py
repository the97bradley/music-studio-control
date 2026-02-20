import unittest

from apply_logic import process_knob_event
from state import State


class TestMainGranularErrors(unittest.TestCase):
    def setUp(self):
        self.st = State(bus=2)
        self.st.ensure_channels(18)
        self.st.knob_to_group = {"knob1": "vocal"}
        self.st.groups = {"vocal": [1]}
        self.st.knob_step = 0.01
        self.calls = []

    def _report(self, where, exc, st=None):
        self.calls.append(where)

    def test_unknown_knob_reports_mapping(self):
        process_knob_event(
            None,
            self.st,
            "knob9",
            1,
            add_group_fn=lambda *args, **kwargs: None,
            set_screen_display_fn=lambda *args, **kwargs: True,
            report_error_fn=self._report,
        )
        self.assertIn("loop.apply.mapping", self.calls)

    def test_write_failure_reports_write_code(self):
        def bad_add_group(*args, **kwargs):
            raise RuntimeError("write failed")

        process_knob_event(
            None,
            self.st,
            "knob1",
            1,
            add_group_fn=bad_add_group,
            set_screen_display_fn=lambda *args, **kwargs: True,
            report_error_fn=self._report,
        )
        self.assertIn("loop.apply.write", self.calls)

    def test_display_failure_reports_display_code(self):
        process_knob_event(
            None,
            self.st,
            "knob1",
            1,
            add_group_fn=lambda *args, **kwargs: None,
            set_screen_display_fn=lambda *args, **kwargs: False,
            report_error_fn=self._report,
        )
        self.assertIn("loop.apply.display", self.calls)


if __name__ == "__main__":
    unittest.main()
