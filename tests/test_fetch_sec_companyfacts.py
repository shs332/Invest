import os
import unittest
from unittest.mock import patch

from scripts import fetch_sec_companyfacts as sec_module
from scripts.fetch_sec_companyfacts import _headers, fetch_companyfacts, resolve_cik


class FetchSecCompanyfactsTest(unittest.TestCase):
    def test_headers_use_env_user_agent_with_a_default_fallback(self):
        with self.subTest("default when SEC_USER_AGENT unset"):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("SEC_USER_AGENT", None)
                headers = _headers()
            self.assertEqual(headers["User-Agent"], "invest-workspace/0.1 contact@example.com")
            self.assertEqual(headers["Host"], "data.sec.gov")

        with self.subTest("env overrides default"):
            with patch.dict(os.environ, {"SEC_USER_AGENT": "acme-research/1.0 me@acme.test"}):
                headers = _headers()
            self.assertEqual(headers["User-Agent"], "acme-research/1.0 me@acme.test")

    def test_resolve_cik_pads_first_match_and_raises_without_one(self):
        with self.subTest("pads and uses first cik match"):
            with patch.object(sec_module, "resolve_company", return_value=[{"cik": 320193}]):
                self.assertEqual(resolve_cik("AAPL"), "0000320193")

        with self.subTest("raises SystemExit when no match has a cik"):
            with patch.object(sec_module, "resolve_company", return_value=[{"name": "no cik here"}]):
                with self.assertRaises(SystemExit):
                    resolve_cik("NOPE")

    def test_fetch_companyfacts_resolves_cik_builds_url_and_sends_sec_headers(self):
        with self.subTest("explicit cik skips resolve_company"):
            with patch.object(sec_module, "resolve_company") as resolve_mock:
                with patch.object(sec_module, "http_json", return_value={"facts": {}}) as http_mock:
                    result = fetch_companyfacts("AAPL", cik="320193")
            resolve_mock.assert_not_called()
            self.assertEqual(
                http_mock.call_args.args[0], "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
            )
            self.assertEqual(result["_fetch"]["cik"], "0000320193")
            self.assertEqual(result["_fetch"]["ticker"], "AAPL")
            sent_headers = http_mock.call_args.kwargs.get("headers")
            self.assertIsNotNone(sent_headers)
            self.assertIn("User-Agent", sent_headers)
            self.assertEqual(sent_headers["Host"], "data.sec.gov")

        with self.subTest("missing cik resolves via resolve_company"):
            with patch.object(sec_module, "resolve_company", return_value=[{"cik": 789019}]):
                with patch.object(sec_module, "http_json", return_value={"facts": {}}) as http_mock:
                    result = fetch_companyfacts("MSFT")
            self.assertEqual(
                http_mock.call_args.args[0], "https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json"
            )
            self.assertEqual(result["_fetch"]["cik"], "0000789019")


if __name__ == "__main__":
    unittest.main()
