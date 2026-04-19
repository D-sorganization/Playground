import os
import sys
import unittest

# Add the repo root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from Calculator.webapp import create_app


class TestRateLimitEnforcement(unittest.TestCase):
    def setUp(self):
        # Pass a low rate_limit directly to create_app so the test does not
        # need to reach through app internals (avoids Law of Demeter violation).
        self.app = create_app(rate_limit=2)
        # Ensure TESTING is False so the rate-limit path is exercised.
        self.app.config.update({"TESTING": False})
        self.client = self.app.test_client()

    def test_rate_limit_exceeded(self):
        payload = {"operation": "evaluate", "expression": "1+1"}

        # 1st request - OK
        resp = self.client.post("/api/calculate", json=payload)
        self.assertEqual(resp.status_code, 200)

        # 2nd request - OK
        resp = self.client.post("/api/calculate", json=payload)
        self.assertEqual(resp.status_code, 200)

        # 3rd request - 429 Too Many Requests
        resp = self.client.post("/api/calculate", json=payload)
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Rate limit exceeded", resp.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
