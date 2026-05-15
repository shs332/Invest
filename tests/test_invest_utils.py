import os
import tempfile
import urllib.error
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.invest_utils import NetworkFetchError, http_json, load_project_env


class InvestUtilsEnvTest(unittest.TestCase):
    def test_loads_plain_export_quoted_and_inline_comment_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "PLAIN=value",
                        "export EXPORTED=from_export",
                        "QUOTED='quoted value'",
                        "COMMENTED=kept # ignored",
                    ]
                ),
                encoding="utf-8",
            )
            keys = ["PLAIN", "EXPORTED", "QUOTED", "COMMENTED"]
            previous = {key: os.environ.get(key) for key in keys}
            for key in keys:
                os.environ.pop(key, None)
            try:
                loaded = load_project_env(env_path)

                self.assertEqual(loaded["PLAIN"], "value")
                self.assertEqual(os.environ["EXPORTED"], "from_export")
                self.assertEqual(os.environ["QUOTED"], "quoted value")
                self.assertEqual(os.environ["COMMENTED"], "kept")
            finally:
                for key, value in previous.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value

    def test_existing_environment_wins_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("KEEP_ME=from_file\n", encoding="utf-8")
            previous = os.environ.get("KEEP_ME")
            os.environ["KEEP_ME"] = "from_shell"
            try:
                loaded = load_project_env(env_path)

                self.assertEqual(loaded["KEEP_ME"], "from_file")
                self.assertEqual(os.environ["KEEP_ME"], "from_shell")
            finally:
                if previous is None:
                    os.environ.pop("KEEP_ME", None)
                else:
                    os.environ["KEEP_ME"] = previous

    def test_override_replaces_existing_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("REPLACE_ME=from_file\n", encoding="utf-8")
            previous = os.environ.get("REPLACE_ME")
            os.environ["REPLACE_ME"] = "from_shell"
            try:
                load_project_env(env_path, override=True)

                self.assertEqual(os.environ["REPLACE_ME"], "from_file")
            finally:
                if previous is None:
                    os.environ.pop("REPLACE_ME", None)
                else:
                    os.environ["REPLACE_ME"] = previous


class InvestUtilsNetworkTest(unittest.TestCase):
    def test_http_json_wraps_url_errors_with_retry_hint(self):
        with patch("scripts.invest_utils.urllib.request.urlopen", side_effect=urllib.error.URLError("dns failed")):
            with self.assertRaises(NetworkFetchError) as context:
                http_json("https://example.test/data.json?crtfc_key=secret&symbol=AAPL")

        message = str(context.exception)
        self.assertIn("network fetch failed for https://example.test/data.json?crtfc_key=REDACTED&symbol=AAPL", message)
        self.assertNotIn("secret", message)
        self.assertIn("sandbox/network/DNS/provider", message)
        self.assertIn("network approval", message)


if __name__ == "__main__":
    unittest.main()
