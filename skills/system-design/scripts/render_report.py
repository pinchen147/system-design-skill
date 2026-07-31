#!/usr/bin/env python3
"""Render a system-design report by substituting design.json into the template.

Substitution only: every line of renderer code lives in assets/report-template.html.
This script reads the template, injects the design payload at the single
__DESIGN_JSON__ placeholder, and writes a standalone HTML file.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

PLACEHOLDER = "__DESIGN_JSON__"

# Resolved relative to this file so the skill works wherever it is installed:
# symlinked, copied, or vendored inside a plugin.
TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "report-template.html"


def fail(message: str) -> NoReturn:
    print(f"render_report: {message}", file=sys.stderr)
    raise SystemExit(2)


def read_template() -> str:
    try:
        template = TEMPLATE.read_text()
    except OSError as error:
        fail(f"cannot read template {TEMPLATE}: {error}")
    count = template.count(PLACEHOLDER)
    if count != 1:
        fail(
            f"template {TEMPLATE} must contain {PLACEHOLDER} exactly once, found {count}"
        )
    return template


def read_design(design_path: Path) -> dict:
    try:
        text = design_path.read_text()
    except OSError as error:
        fail(f"cannot read design {design_path}: {error}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        fail(f"malformed JSON in {design_path}: {error}")


def encode(design: dict) -> str:
    # `</` becomes `<\/` so that no string value can terminate the embedded
    # <script type="application/json"> block. An unescaped `</script>` inside any
    # note, label, or thesis truncates the payload; the page then falls back to the
    # placeholder title with most components missing.
    return json.dumps(design, ensure_ascii=False).replace("</", "<\\/")


def check_title(design: dict, rendered: str, out_path: Path) -> None:
    title = design.get("title")
    if not isinstance(title, str) or not title:
        print(f"render_report: warning: {out_path} has no design title", file=sys.stderr)
        return
    # The payload is JSON-encoded and `</`-escaped, so compare against that form.
    encoded_title = json.dumps(title, ensure_ascii=False)[1:-1].replace("</", "<\\/")
    if encoded_title not in rendered:
        print(
            f"render_report: warning: title {title!r} is missing from {out_path}",
            file=sys.stderr,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a design.json into a standalone system-design report."
    )
    parser.add_argument("--design", type=Path, required=True, help="path to design.json")
    parser.add_argument("--out", type=Path, required=True, help="path to write the HTML report")
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="write the report without opening it; for tests and headless runs",
    )
    return parser.parse_args()


def open_in_browser(path: Path) -> None:
    """Open the report the way the platform does.

    The run is not finished until a human can see the report, and an agent that
    forgets the separate open command leaves one on disk that nobody looks at.
    Doing it here means it cannot be skipped. A failure to open is reported but
    never fatal — the file is already written, and headless environments are
    expected to fail this.
    """
    if os.environ.get("SYSTEM_DESIGN_NO_OPEN"):
        return
    if sys.platform == "darwin":
        command = ["open", str(path)]
    elif os.name == "nt":
        command = ["cmd", "/c", "start", "", str(path)]
    else:
        opener = shutil.which("xdg-open") or shutil.which("wslview")
        if not opener:
            print("render_report: no opener found; open it manually", file=sys.stderr)
            return
        command = [opener, str(path)]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as error:
        print(f"render_report: could not open the report ({error})", file=sys.stderr)


def main() -> None:
    args = parse_args()
    template = read_template()
    design = read_design(args.design)
    rendered = template.replace(PLACEHOLDER, encode(design))

    out_path = args.out.expanduser().resolve()
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered)
    except OSError as error:
        fail(f"cannot write {out_path}: {error}")

    check_title(design, rendered, out_path)
    print(out_path)
    if not args.no_open:
        open_in_browser(out_path)


if __name__ == "__main__":
    main()
