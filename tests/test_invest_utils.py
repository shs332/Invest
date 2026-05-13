import gzip
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import invest_utils
from scripts.invest_utils import load_project_env, read_json, write_json


class InvestUtilsTest(unittest.TestCase):
    def test_write_and_read_gzip_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.json.gz"

            output = write_json(path, {"b": 2, "a": 1})

            self.assertEqual(output, path)
            self.assertEqual(read_json(path), {"a": 1, "b": 2})
            with gzip.open(path, "rt", encoding="utf-8") as f:
                self.assertEqual(json.load(f), {"a": 1, "b": 2})

    def test_write_compact_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.json"

            write_json(path, {"a": 1, "b": 2}, compact=True)

            self.assertEqual(path.read_text(encoding="utf-8"), '{"a":1,"b":2}\n')

    def test_write_pretty_json_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.json"

            write_json(path, {"b": 2, "a": 1})

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                '{\n  "a": 1,\n  "b": 2\n}\n',
            )

    def test_load_project_env_reads_shell_style_env_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                "\n".join(
                    [
                        "# local secrets",
                        "OPENDART_API_KEY=abc123",
                        'SEC_USER_AGENT="invest workspace contact@example.com"',
                        "export DART_API_KEY='literal$456'",
                        "INLINE_COMMENT=value # ignored",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                loaded = load_project_env(path)

                self.assertEqual(loaded["OPENDART_API_KEY"], "abc123")
                self.assertEqual(os.environ["SEC_USER_AGENT"], "invest workspace contact@example.com")
                self.assertEqual(os.environ["DART_API_KEY"], "literal$456")
                self.assertEqual(os.environ["INLINE_COMMENT"], "value")

    def test_load_project_env_defaults_to_project_root_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("SEC_USER_AGENT=root-env\n", encoding="utf-8")

            with patch.object(invest_utils, "PROJECT_ROOT", root):
                with patch.dict(os.environ, {}, clear=True):
                    load_project_env()

                    self.assertEqual(os.environ["SEC_USER_AGENT"], "root-env")

    def test_load_project_env_preserves_non_ascii_double_quoted_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text('CONTACT_NAME="홍길동"\n', encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                load_project_env(path)

                self.assertEqual(os.environ["CONTACT_NAME"], "홍길동")

    def test_load_project_env_does_not_override_existing_env_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("OPENDART_API_KEY=from-file\n", encoding="utf-8")

            with patch.dict(os.environ, {"OPENDART_API_KEY": "from-shell"}, clear=True):
                loaded = load_project_env(path)

                self.assertEqual(loaded, {})
                self.assertEqual(os.environ["OPENDART_API_KEY"], "from-shell")

    def test_load_project_env_can_override_existing_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("OPENDART_API_KEY=from-file\n", encoding="utf-8")

            with patch.dict(os.environ, {"OPENDART_API_KEY": "from-shell"}, clear=True):
                loaded = load_project_env(path, override=True)

                self.assertEqual(loaded["OPENDART_API_KEY"], "from-file")
                self.assertEqual(os.environ["OPENDART_API_KEY"], "from-file")

    def test_load_project_env_rejects_invalid_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("not valid\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing '='"):
                load_project_env(path)


if __name__ == "__main__":
    unittest.main()
