import os
import tempfile
import urllib.error
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from scripts.invest_utils import NetworkFetchError, http_json, load_project_env


@contextmanager
def _restoring_env(*keys):
    previous = {key: os.environ.get(key) for key in keys}
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


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
            with _restoring_env(*keys):
                for key in keys:
                    os.environ.pop(key, None)
                loaded = load_project_env(env_path)

                self.assertEqual(loaded["PLAIN"], "value")
                self.assertEqual(os.environ["EXPORTED"], "from_export")
                self.assertEqual(os.environ["QUOTED"], "quoted value")
                self.assertEqual(os.environ["COMMENTED"], "kept")

    def test_shell_environment_wins_by_default_but_override_replaces_it(self):
        with self.subTest("existing shell value wins by default"):
            with tempfile.TemporaryDirectory() as tmp:
                env_path = Path(tmp) / ".env"
                env_path.write_text("KEEP_ME=from_file\n", encoding="utf-8")
                with _restoring_env("KEEP_ME"):
                    os.environ["KEEP_ME"] = "from_shell"
                    loaded = load_project_env(env_path)
                    self.assertEqual(loaded["KEEP_ME"], "from_file")
                    self.assertEqual(os.environ["KEEP_ME"], "from_shell")

        with self.subTest("override=True replaces the shell value"):
            with tempfile.TemporaryDirectory() as tmp:
                env_path = Path(tmp) / ".env"
                env_path.write_text("REPLACE_ME=from_file\n", encoding="utf-8")
                with _restoring_env("REPLACE_ME"):
                    os.environ["REPLACE_ME"] = "from_shell"
                    load_project_env(env_path, override=True)
                    self.assertEqual(os.environ["REPLACE_ME"], "from_file")


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
