import os
import unittest
from unittest.mock import patch

from scripts import fetch_sec_companyfacts as sec_module
from scripts.fetch_sec_companyfacts import _headers, fetch_companyfacts, resolve_cik


class HeadersTest(unittest.TestCase):
    def test_default_user_agent_when_env_unset(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SEC_USER_AGENT", None)
            headers = _headers()
        self.assertEqual(headers["User-Agent"], "invest-workspace/0.1 contact@example.com")
        self.assertEqual(headers["Host"], "data.sec.gov")

    def test_env_overrides_user_agent(self):
        with patch.dict(os.environ, {"SEC_USER_AGENT": "acme-research/1.0 me@acme.test"}):
            headers = _headers()
        self.assertEqual(headers["User-Agent"], "acme-research/1.0 me@acme.test")


class ResolveCikTest(unittest.TestCase):
    def test_resolve_cik_pads_and_uses_first_cik_match(self):
        with patch.object(sec_module, "resolve_company", return_value=[{"cik": 320193}]):
            self.assertEqual(resolve_cik("AAPL"), "0000320193")

    def test_resolve_cik_raises_when_no_match_has_a_cik(self):
        with patch.object(sec_module, "resolve_company", return_value=[{"name": "no cik here"}]):
            with self.assertRaises(SystemExit):
                resolve_cik("NOPE")


class FetchCompanyfactsTest(unittest.TestCase):
    def test_uses_explicit_cik_without_calling_resolve_company(self):
        with patch.object(sec_module, "resolve_company") as resolve_mock:
            with patch.object(sec_module, "http_json", return_value={"facts": {}}) as http_mock:
                result = fetch_companyfacts("AAPL", cik="320193")

        resolve_mock.assert_not_called()
        called_url = http_mock.call_args.args[0]
        self.assertEqual(called_url, "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json")
        self.assertEqual(result["_fetch"]["cik"], "0000320193")
        self.assertEqual(result["_fetch"]["ticker"], "AAPL")

    def test_resolves_cik_via_resolve_company_when_not_given(self):
        with patch.object(sec_module, "resolve_company", return_value=[{"cik": 789019}]):
            with patch.object(sec_module, "http_json", return_value={"facts": {}}) as http_mock:
                result = fetch_companyfacts("MSFT")

        called_url = http_mock.call_args.args[0]
        self.assertEqual(called_url, "https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json")
        self.assertEqual(result["_fetch"]["cik"], "0000789019")

    def test_sends_sec_required_headers(self):
        with patch.object(sec_module, "http_json", return_value={"facts": {}}) as http_mock:
            fetch_companyfacts("AAPL", cik="320193")

        sent_headers = http_mock.call_args.kwargs.get("headers")
        self.assertIsNotNone(sent_headers)
        self.assertIn("User-Agent", sent_headers)
        self.assertEqual(sent_headers["Host"], "data.sec.gov")


if __name__ == "__main__":
    unittest.main()
