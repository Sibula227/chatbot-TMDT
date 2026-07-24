import importlib
import os
import types
import unittest
from unittest.mock import patch


class TimeoutConfigTests(unittest.TestCase):
    def setUp(self):
        # Ensure clean environment for each test
        for k in list(os.environ.keys()):
            if k in ("SOPE_CONNECT_TIMEOUT", "SOPE_API_TIMEOUT"):
                del os.environ[k]

    def reload_module(self, name: str) -> types.ModuleType:
        if name in globals():
            del globals()[name]
        mod = importlib.import_module(name)
        return importlib.reload(mod)

    def test_defaults(self):
        cfg = self.reload_module("timeout_config")
        self.assertEqual(cfg.SOPE_CONNECT_TIMEOUT, 5.0)
        self.assertEqual(cfg.SOPE_API_TIMEOUT, 20.0)

    def test_env_override_valid(self):
        os.environ["SOPE_CONNECT_TIMEOUT"] = "3"
        os.environ["SOPE_API_TIMEOUT"] = "30"
        cfg = self.reload_module("timeout_config")
        self.assertEqual(cfg.SOPE_CONNECT_TIMEOUT, 3.0)
        self.assertEqual(cfg.SOPE_API_TIMEOUT, 30.0)

    def test_env_invalid_values_fallback(self):
        os.environ["SOPE_CONNECT_TIMEOUT"] = "abc"
        os.environ["SOPE_API_TIMEOUT"] = "-5"
        cfg = self.reload_module("timeout_config")
        self.assertEqual(cfg.SOPE_CONNECT_TIMEOUT, 5.0)
        self.assertEqual(cfg.SOPE_API_TIMEOUT, 20.0)


class RecommendationRequestTests(unittest.TestCase):
    def setUp(self):
        # set deterministic env
        os.environ["SOPE_CONNECT_TIMEOUT"] = "2"
        os.environ["SOPE_API_TIMEOUT"] = "7"
        # reload modules to pick up env
        import timeout_config as tc
        importlib.reload(tc)
        import recommendation as rec
        importlib.reload(rec)
        self.tc = tc
        self.rec = rec

    @patch("recommendation.requests.get")
    def test_fetch_all_products_uses_timeout_tuple(self, mock_get):
        # Prepare a fake response
        class Resp:
            status_code = 200

            def json(self):
                return []

        mock_get.return_value = Resp()

        # Call fetch_all_products; should call requests.get with timeout tuple
        self.rec.fetch_all_products()

        mock_get.assert_called()
        args, kwargs = mock_get.call_args
        self.assertIn("timeout", kwargs)
        self.assertEqual(kwargs["timeout"], (self.tc.SOPE_CONNECT_TIMEOUT, self.tc.SOPE_API_TIMEOUT))


if __name__ == "__main__":
    unittest.main()
