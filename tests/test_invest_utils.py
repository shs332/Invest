import os
import tempfile
import unittest
from pathlib import Path

from scripts.invest_utils import load_project_env


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


if __name__ == "__main__":
    unittest.main()
