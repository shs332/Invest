import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.invest_utils import read_json, write_json


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


if __name__ == "__main__":
    unittest.main()
