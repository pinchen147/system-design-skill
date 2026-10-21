"""Regression checks for UTF-8 report I/O; no browser or network required."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills/system-design/scripts/render_report.py"
spec = importlib.util.spec_from_file_location("renderer", SCRIPT)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)

class Utf8IO(unittest.TestCase):
    def test_unicode_round_trip_under_non_utf8_default(self):
        original_read, original_write = Path.read_text, Path.write_text
        def read(path, *args, **kwargs):
            kwargs.setdefault("encoding", "cp1252")
            return original_read(path, *args, **kwargs)
        def write(path, text, *args, **kwargs):
            kwargs.setdefault("encoding", "cp1252")
            return original_write(path, text, *args, **kwargs)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            template, design, out = root / "template.html", root / "design.json", root / "report.html"
            template.write_text("架構<script>__DESIGN_JSON__</script>", encoding="utf-8")
            payload = {"title": "同步 café 🚀", "note": "</script><test>"}
            design.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(renderer, "TEMPLATE", template), patch.object(Path, "read_text", read), patch.object(Path, "write_text", write), patch("sys.argv", ["renderer", "--design", str(design), "--out", str(out), "--no-open"]):
                renderer.main()
            html = out.read_text(encoding="utf-8")
            self.assertIn("架構", html)
            self.assertIn(payload["title"], html)
            self.assertIn("<\\/script>", html)

    def test_invalid_utf8_has_clear_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_bytes(b"\xff")
            with self.assertRaises(SystemExit) as raised:
                renderer.read_design(path)
            self.assertEqual(2, raised.exception.code)

if __name__ == "__main__":
    unittest.main()
