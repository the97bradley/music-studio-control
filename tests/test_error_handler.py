import unittest

import error_handler


class TestErrorHandler(unittest.TestCase):
    def test_code_mapping_known_and_unknown(self):
        self.assertEqual(error_handler._code_for("startup.load_env"), "E111")
        self.assertEqual(error_handler._code_for("loop.apply"), "E214")
        self.assertEqual(error_handler._code_for("does.not.exist"), "E999")

    def test_report_error_uses_fallback_when_screen_write_fails(self):
        calls = []

        def bad_set_screen_text(*args, **kwargs):
            raise RuntimeError("display down")

        def fake_fallback(code, detail=""):
            calls.append((code, detail))

        orig_set = error_handler.set_screen_text
        orig_fallback = error_handler.fallback_alert
        try:
            error_handler.set_screen_text = bad_set_screen_text
            error_handler.fallback_alert = fake_fallback

            error_handler.report_error("loop.sync", RuntimeError("boom"))

            self.assertTrue(calls)
            self.assertEqual(calls[0][0], "E311")
        finally:
            error_handler.set_screen_text = orig_set
            error_handler.fallback_alert = orig_fallback


if __name__ == "__main__":
    unittest.main()
