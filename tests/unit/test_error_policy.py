import unittest

from app.core.error_policy import ErrorPolicy, get_policy


class TestErrorPolicy(unittest.TestCase):
    def test_known_policy(self):
        p = get_policy("loop.sync")
        self.assertEqual(p.mode, "degrade")
        self.assertGreaterEqual(p.max_retries, 1)

    def test_unknown_policy_defaults(self):
        p = get_policy("unknown.where")
        self.assertIsInstance(p, ErrorPolicy)
        self.assertEqual(p.mode, "continue")
        self.assertEqual(p.max_retries, 0)


if __name__ == "__main__":
    unittest.main()
