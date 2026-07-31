#!/usr/bin/env python3
"""Render one system-design report with the shipped script and assert what a browser sees."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
RENDER_SCRIPT = ROOT / "skills/system-design/scripts/render_report.py"
DEFAULT_DESIGN = ROOT / "examples/design-ticketing/design.json"
PLACEHOLDER_TITLE = "System design report"
CHROME_CANDIDATES = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
)


def render_report(design_path: Path, output_path: Path) -> dict:
    """Invoke the shipped renderer exactly as the skill instructs an agent to."""
    subprocess.run(
        [
            sys.executable,
            str(RENDER_SCRIPT),
            "--design",
            str(design_path),
            "--out",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(design_path.read_text())


def chrome_binary() -> Path:
    configured = os.environ.get("CHROME_BIN")
    if configured:
        return Path(configured)
    for candidate in CHROME_CANDIDATES:
        if candidate.exists():
            return candidate
    raise RuntimeError("Set CHROME_BIN to a Chrome/Chromium executable")


def run_chrome(report_path: Path, hash_route: str, inspect_component: str | None = None) -> str:
    query = f"?inspect={quote(inspect_component)}" if inspect_component else ""
    command = [
        str(chrome_binary()),
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--window-size=1440,900",
        "--virtual-time-budget=1200",
        "--dump-dom",
        f"{report_path.as_uri()}{query}#{hash_route}",
    ]
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    ).stdout


def diagnostic_value(dom: str, name: str) -> int:
    match = re.search(fr'data-{re.escape(name)}="(\d+)"', dom)
    assert match, f"missing diagnostic {name}"
    return int(match.group(1))


def rendered_title(dom: str) -> str:
    """The heading the page actually shows, which only the parsed payload can set."""
    match = re.search(r'<h1 id="rtitle"[^>]*>(.*?)</h1>', dom, re.S)
    assert match, "missing report heading"
    return html.unescape(match.group(1)).strip()


def assert_not_corrupted(dom: str, design: dict) -> None:
    """A truncated payload leaves all four diagnostics at 0, so they cannot detect it.

    The only reliable signal is that the page kept the design's own title instead of
    falling back to the template placeholder.
    """
    title = design["title"]
    shown = rendered_title(dom)
    assert shown != PLACEHOLDER_TITLE, (
        f"report fell back to the template placeholder title — the payload never parsed"
    )
    assert shown == title, f"report title is {shown!r}, expected {title!r}"


def assert_v2_content(dom: str, design: dict) -> None:
    assert "Core entities and invariants" in dom
    assert "System interfaces" in dom
    assert "Critical deep dives" in dom
    assert "Data and consistency model" in dom, "missing dataModel section"
    schema_section = re.search(
        r'<div class="card schema-section">(.*?)(?=<div class="card">)', dom, re.S
    )
    assert schema_section, "missing rendered database schema section"
    rendered_schemas = schema_section.group(1)
    expected_schemas = design["dataModel"]["schemas"]
    assert rendered_schemas.count('class="schema-card"') == len(expected_schemas), (
        "rendered schema card count does not match design data"
    )
    assert "Database schemas" in rendered_schemas, "missing schema section heading"
    # Assert against the design's own schemas rather than one fixture's domain
    # words, so a second example can pass without borrowing the first's nouns.
    for schema in expected_schemas:
        assert schema["name"] in rendered_schemas, (
            f"schema {schema['name']!r} is in the design but not rendered"
        )
        for field in schema.get("fields", [])[:3]:
            name = field["name"] if isinstance(field, dict) else str(field)
            assert name in rendered_schemas, (
                f"field {name!r} of schema {schema['name']!r} is not rendered"
            )
    top3 = design["requirements"]["priorities"]["top3"]
    assert len(top3) == 3, f"requirements.priorities.top3 must name three axes, got {top3}"
    for axis in top3:
        assert axis in dom, f"top-three characteristic {axis!r} is not shown in the report"


def assert_interface_contracts(dom: str, design: dict) -> None:
    for label in ("Deadline / retry", "Trust / pressure", "Failure / compatibility"):
        assert label in dom, f"missing interface contract label {label!r}"
    interfaces = design.get("interfaces", [])
    assert interfaces, "design declares no interfaces"
    # Every interface must reach the page with its own contract values, rather
    # than the page merely containing one fixture's strings.
    for interface in interfaces:
        assert interface["name"] in dom, f"interface {interface['name']!r} is not rendered"
        contract = interface.get("contract") or {}
        for key in ("deadline", "retryOwner", "failureMode", "compatibility"):
            value = contract.get(key)
            if isinstance(value, str) and value.strip():
                assert value in dom, (
                    f"interface {interface['name']!r} contract {key} is not rendered"
                )


def inspector_body(dom: str, route: str) -> str:
    section = re.search(
        fr'<section id="sec-{re.escape(route)}"[^>]*>(.*?)</section>', dom, re.S
    )
    assert section, f"architecture section {route!r} did not render"
    match = re.search(
        r'<div class="inspector-body">(.*?)</div>\s*</aside>', section.group(1), re.S
    )
    assert match, "component inspector did not render"
    return match.group(1)


def assert_architecture_contracts(report_path: Path, design: dict, route: str) -> None:
    architecture = next(item for item in design["architectures"] if item["id"] == route)
    assert all("contract" in edge for edge in architecture["edges"]), "edge contract missing"
    for edge in architecture["edges"]:
        assert set(edge["contract"]) >= {"deadline", "retryOwner", "backlogBound"}, (
            f"incomplete edge contract: {edge['from']} → {edge['to']}"
        )
    stateful_types = {"blob", "cache", "cdn", "db-nosql", "db-sql", "queue", "stream"}
    for component in architecture["components"]:
        if component.get("type") not in stateful_types:
            continue
        state = component.get("state")
        assert state, f"stateful component lacks state contract: {component['id']}"
        if state.get("role") == "authoritative":
            assert set(state) >= {"acknowledgement", "failureDomain", "rpo", "rto", "recovery"}, (
                f"authoritative state contract is incomplete: {component['id']}"
            )
        elif state.get("role") == "derived":
            assert set(state) >= {"source", "cursor"}, (
                f"derived state contract is incomplete: {component['id']}"
            )
        else:
            raise AssertionError(f"invalid state role on {component['id']}: {state.get('role')!r}")
    # Derive what to inspect from the design rather than naming components, so
    # this validates any design and not just the example it was written against.
    def first_with(role: str) -> dict | None:
        return next(
            (
                component
                for component in architecture["components"]
                if component.get("type") in stateful_types
                and (component.get("state") or {}).get("role") == role
            ),
            None,
        )

    inspections: dict[str, tuple[str, ...]] = {}
    authoritative = first_with("authoritative")
    if authoritative:
        state = authoritative["state"]
        inspections[authoritative["id"]] = (
            "State contract",
            "Acknowledgement",
            "Failure domain",
            state["acknowledgement"],
            state["failureDomain"],
        )
    derived = first_with("derived")
    if derived:
        state = derived["state"]
        inspections[derived["id"]] = ("State contract", state["source"], state["cursor"])
    assert inspections, f"architecture {route} has no stateful component to inspect"

    for component_id, expected in inspections.items():
        rendered_inspector = inspector_body(
            run_chrome(report_path, route, component_id), route
        )
        for value in expected:
            assert value in rendered_inspector, (
                f"component inspector for {component_id!r} did not render {value!r}"
            )


def assert_legacy_interfaces_render_as_dashes(design_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="system-design-legacy-v2-") as temp_dir:
        temp = Path(temp_dir)
        legacy_path = temp / "legacy-v2.json"
        report_path = temp / "report.html"
        legacy = json.loads(design_path.read_text())
        legacy["title"] = "Legacy v2 interface fixture"
        for architecture in legacy["architectures"]:
            for component in architecture["components"]:
                component.pop("state", None)
            for edge in architecture["edges"]:
                edge.pop("contract", None)
        legacy["interfaces"] = [{
            "name": "Legacy interface",
            "purpose": "PURPOSE_SENTINEL",
            "contract": "CONTRACT_SENTINEL <unsafe> & quoted",
            "transport": "TRANSPORT_SENTINEL",
            "consistency": "CONSISTENCY_SENTINEL",
            "idempotency": "IDEMPOTENCY_SENTINEL",
        }]
        legacy_path.write_text(json.dumps(legacy))
        render_report(legacy_path, report_path)
        dom = run_chrome(report_path, "overview")
        assert rendered_title(dom) == legacy["title"]
        row = re.search(r'<article class="interface-contract".*?</article>', dom, re.S)
        assert row, "missing legacy interface contract"
        rendered = row.group(0)
        for sentinel in (
            "PURPOSE_SENTINEL", "CONTRACT_SENTINEL", "TRANSPORT_SENTINEL",
            "CONSISTENCY_SENTINEL", "IDEMPOTENCY_SENTINEL",
        ):
            assert sentinel in rendered, f"legacy field was dropped: {sentinel}"
        for field in (
            "style", "trustBoundary", "deadline", "retryability", "backpressure",
            "compatibility", "failureResult",
        ):
            assert f'data-interface-field="{field}">—</span>' in rendered, (
                f"absent richer interface field does not render as an em dash: {field}"
            )
        assert "<unsafe>" not in rendered
        assert "&lt;unsafe&gt; &amp; quoted" in rendered
        assert "undefined" not in rendered


def assert_report_geometry(design_path: Path, route: str) -> str:
    with tempfile.TemporaryDirectory(prefix="system-design-report-") as temp_dir:
        report = Path(temp_dir) / "report.html"
        design = render_report(design_path, report)
        dom = run_chrome(report, route)
        assert_architecture_contracts(report, design, route)
        assert 'id="zoom-fit-' + route + '"' in dom, "missing Fit control"
        assert 'class="flow-sidebar"' in dom, "missing permanent flow sidebar"
        assert_not_corrupted(dom, design)
        assert_v2_content(dom, design)
        assert_interface_contracts(dom, design)
        assert diagnostic_value(dom, "component-overlaps") == 0
        assert diagnostic_value(dom, "route-collisions") == 0
        assert diagnostic_value(dom, "text-overflows") == 0
        assert diagnostic_value(dom, "fit-overflows") == 0
        # An edge label the placer could not keep clear of a component or of
        # another label. Unreadable text scored zero before this existed.
        assert diagnostic_value(dom, "label-occlusions") == 0
        return design.get("title", design_path.stem)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--route", default="a")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    title = assert_report_geometry(args.design, args.route)
    assert_legacy_interfaces_render_as_dashes(args.design)
    print(f"PASS: {title} architecture {args.route}")


if __name__ == "__main__":
    main()
