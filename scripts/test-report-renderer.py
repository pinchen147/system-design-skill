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
            "--no-open",
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


def debt_section(dom: str) -> str:
    """The debt panel's own markup, so a match cannot come from another tab.

    Scanned rather than matched: each finding nests <section> elements for its
    detail columns, so a non-greedy regex stops at the first one and silently
    reports a truncated panel as a complete one.
    """
    opening = re.search(r'<section id="sec-debt"[^>]*>', dom)
    assert opening, "debt section did not render"
    rest, depth = dom[opening.end():], 1
    for tag in re.finditer(r"</?section\b", rest):
        depth += 1 if tag.group(0) == "<section" else -1
        if depth == 0:
            return rest[: tag.start()]
    raise AssertionError("debt section is unbalanced")


def assert_debt_findings(dom: str, design: dict) -> None:
    """Assert against the design's own findings rather than one fixture's nouns."""
    debt = design.get("debt")
    if not debt:
        assert "<section id=\"sec-debt\"" not in dom, "debt tab rendered for a design with no findings"
        return
    findings = debt.get("findings", [])
    assert findings, "design declares a debt register with no findings"
    rendered = debt_section(dom)
    assert rendered.count('<details class="finding"') == len(findings), (
        "rendered finding count does not match the design"
    )
    rows = {
        html.unescape(m.group(1)): m.group(2)
        for m in re.finditer(
            r'<details class="finding" id="f-([^"]+)">(.*?)</summary>', rendered, re.S
        )
    }
    lookup = {
        ("breaking", "on-path"): "blocking", ("breaking", "off-path"): "high",
        ("friction", "on-path"): "medium", ("friction", "off-path"): "low",
    }
    chip = re.compile(r'class="dc sev[^"]*"[^>]*>([^<]+)</span>')
    for finding in findings:
        row = rows.get(finding["id"])
        assert row is not None, f"finding {finding['id']!r} is in the design but not rendered"
        # The collapsed row is the entire reading surface until someone opens it,
        # so anything a reader would search or filter on has to be visible there —
        # not merely present in the section, and not hidden in an attribute.
        for value in [finding.get("title")] + list(finding.get("components", [])):
            if isinstance(value, str) and value.strip():
                assert html.escape(value, quote=False) in row, (
                    f"finding {finding['id']!r} does not show {value!r} until it is opened"
                )
        severity = finding.get("severity")
        if not severity:
            continue
        shown = chip.search(row)
        assert shown, f"finding {finding['id']!r} renders no severity chip"
        assert shown.group(1).lower() == severity.lower(), (
            f"finding {finding['id']!r} chip reads {shown.group(1)!r}, severity is {severity!r}"
        )
        # Severity has one source. A chip that disagrees with the two axes means
        # the renderer invented a verdict the artifact does not support. A level
        # outside the four is a malformed artifact, not a derivation to check —
        # it still has to render, which the chip assertion above covers.
        pair = (finding.get("consequence"), finding.get("exposure"))
        if pair in lookup and severity in lookup.values():
            assert severity == lookup[pair], (
                f"finding {finding['id']!r} severity {severity!r} does not follow from {pair}"
            )
    for category in {f.get("category") for f in findings if f.get("severity")}:
        assert f'data-cat="{category}"' in rendered, (
            f"findings are not grouped under category {category!r}"
        )
    assert 'role="group" aria-label="Filter findings"' in rendered, "missing labelled filter group"
    assert 'class="debt-status" role="status"' in rendered, "filter count is not a live region"
    assert "undefined" not in rendered


def click_and_dump(report_path: Path, selector: str) -> str:
    """Dump the DOM after one click, since --dump-dom alone only shows first paint."""
    driven = report_path.with_name("driven.html")
    driven.write_text(report_path.read_text().replace(
        "</body>",
        '<script>addEventListener("load",()=>setTimeout(()=>'
        f'document.querySelector({selector!r}).click(),50))</script></body>',
    ))
    return run_chrome(driven, "debt")


def assert_debt_survives_a_malformed_register(design_path: Path) -> None:
    """Every value in a finding is written by a model, so none of them can be trusted.

    A category outside the taxonomy and a severity outside the four levels both
    have to reach the page. Dropping either loses a finding silently while the
    header keeps counting it, which is the one failure a reader cannot detect.
    """
    with tempfile.TemporaryDirectory(prefix="system-design-debt-rough-") as temp_dir:
        temp = Path(temp_dir)
        rough_path, report_path = temp / "rough.json", temp / "report.html"
        fixture = json.loads(design_path.read_text())
        fixture["title"] = "Malformed debt register"
        fixture["mode"] = "repo"
        # A component id carrying the character the markup would delimit on.
        spaced = "orders db"

        axes = {"blocking": ("breaking", "on-path"), "high": ("breaking", "off-path"),
                "medium": ("friction", "on-path"), "low": ("friction", "off-path")}

        def finding(key, category, severity, components):
            # Derive the axes from the severity so the fixture is well formed
            # everywhere except where this test breaks it on purpose.
            consequence, exposure = axes.get(severity, ("breaking", "on-path"))
            return {
                "id": f"dbt-{key}--x", "subject": "repo", "category": category,
                "pattern": key, "title": f"TITLE_{key.upper()}", "components": components,
                "consequence": consequence, "exposure": exposure, "severity": severity,
                "confidence": "high", "evidence": [], "whyItMatters": "w",
                "remedy": {"action": "cut", "text": "r"}, "effort": "S",
                "resolvedBy": [], "disconfirming": "d",
                "verification": {"gates": {}, "lenses": [], "tools": [], "survived": 0},
                "status": "open", "firstSeen": "2026-08-11", "baselineState": "new",
            }

        fixture["debt"] = {"checked": [], "findings": [
            finding("known", "data-ownership", "blocking", ["svc-a"]),
            finding("rogue", "security", "blocking", ["svc-a"]),
            finding("odd", "coupling", "critical", ["svc-a"]),
            finding("spaced", "coupling", "medium", [spaced]),
            dict(finding("kept", "coupling", "low", ["svc-a"]),
                 status="accepted", justification="j"),
        ]}
        rough_path.write_text(json.dumps(fixture))
        design = render_report(rough_path, report_path)
        dom = run_chrome(report_path, "debt")
        rendered = debt_section(dom)
        # Every finding reaches the page, whatever the taxonomy says about it.
        assert_debt_findings(dom, design)
        assert 'data-cat="security"' in rendered, "a category outside the seven was dropped"
        assert ">critical<" in rendered, "a severity outside the four rendered no chip"
        live = [f for f in fixture["debt"]["findings"] if f["status"] != "accepted"]
        assert f'role="status">{len(live)} findings' in rendered, (
            "the live-region count disagrees with the findings actually rendered"
        )
        # Filtering a component whose id contains the markup's own delimiter must
        # show that finding, not hide it.
        filtered = click_and_dump(report_path, f'button[data-value="{spaced}"]')
        panel = debt_section(filtered)
        assert "1 of 4 findings shown" in panel, (
            f"filtering by {spaced!r} did not select exactly its finding"
        )
        assert "TITLE_SPACED" in panel
        # The count cannot exceed the total, which it does when the asides are
        # swept into the filter set.
        shown = re.search(r"(\d+) of (\d+) findings shown", panel)
        assert int(shown.group(1)) <= int(shown.group(2)), (
            f"filter reported {shown.group(0)!r}, which is not possible"
        )
        # An aside is not described by the chips, so a filter must leave it alone.
        assert "Accepted (1)" in panel, "a filter emptied a section the chips do not describe"
        assert re.search(r'class="debt-count">\(1 of \d+\)', panel), (
            "group counts do not relabel while a filter is applied"
        )


def assert_debt_tab_renders(design_path: Path) -> None:
    """The shipped example is greenfield, so derive a repo-mode fixture from it."""
    with tempfile.TemporaryDirectory(prefix="system-design-debt-") as temp_dir:
        temp = Path(temp_dir)
        debt_path, report_path = temp / "debt.json", temp / "report.html"
        fixture = json.loads(design_path.read_text())
        fixture["title"] = "Repository debt fixture"
        fixture["mode"] = "repo"
        components = [c["id"] for c in fixture["architectures"][0]["components"]][:2]
        fixture["debt"] = {
            "scheme": "pattern+components/v1",
            "checked": ["data-ownership"],
            "unverified": [{"check": "UNVERIFIED_SENTINEL", "reason": "shallow clone"}],
            "findings": [{
                "id": "dbt-shared-persistence--" + "-".join(sorted(components)),
                "identity": {"scheme": "pattern+components/v1",
                             "pattern": "shared-persistence", "components": sorted(components)},
                "subject": "repo", "category": "data-ownership",
                "pattern": "shared-persistence",
                "title": "TITLE_SENTINEL <unsafe> & quoted",
                "components": components,
                "consequence": "breaking", "exposure": "on-path",
                "severity": "blocking", "confidence": "high",
                "evidence": [{"text": "EVIDENCE_SENTINEL", "source": "src/a.py"}],
                "whyItMatters": "WHY_SENTINEL",
                "remedy": {"action": "consolidate", "text": "REMEDY_SENTINEL"},
                "effort": "M", "resolvedBy": [], "disconfirming": "OBJECTION_SENTINEL",
                "verification": {"gates": {"real": "pass"}, "lenses": [], "tools": [], "survived": 1},
                "status": "open", "firstSeen": "2026-08-11", "baselineState": "new",
            }],
        }
        debt_path.write_text(json.dumps(fixture))
        design = render_report(debt_path, report_path)
        dom = run_chrome(report_path, "debt")
        assert rendered_title(dom) == fixture["title"]
        assert_debt_findings(dom, design)
        rendered = debt_section(dom)
        for sentinel in ("EVIDENCE_SENTINEL", "WHY_SENTINEL", "REMEDY_SENTINEL",
                         "OBJECTION_SENTINEL", "UNVERIFIED_SENTINEL"):
            assert sentinel in rendered, f"debt field was dropped: {sentinel}"
        assert "<unsafe>" not in rendered
        assert "&lt;unsafe&gt; &amp; quoted" in rendered
        # Printing must open every disclosure and every tab, and must not ship
        # whatever the reader happened to have filtered.
        for rule in ("@media print", "::details-content",
                     "section[hidden]", ".finding[hidden]"):
            assert rule in dom, f"print stylesheet is missing {rule!r}"
        # The route must select the tab, not merely build the section.
        assert re.search(r'<button[^>]*id="tab-debt"[^>]*aria-selected="true"', dom), (
            "the #debt route did not select the debt tab"
        )
        opened = re.search(r'<section id="sec-debt"([^>]*)>', dom)
        assert opened and "hidden" not in opened.group(1), (
            "the #debt route left the debt section hidden"
        )
        # Every row starts closed, or the panel opens as a wall of text.
        assert not re.search(r'<details class="finding"[^>]*\sopen', dom), (
            "a finding rendered already expanded"
        )
        # A deep link has to reach the finding instead of falling through to the
        # overview, which is what the router did before it split on the slash.
        deep = run_chrome(report_path, "debt/f-" + fixture["debt"]["findings"][0]["id"])
        target = re.search(r'<details class="finding" id="f-[^"]*"([^>]*)>', deep)
        assert target and "open" in target.group(1), "deep link did not open its finding"
        assert re.search(r'id="tab-debt"[^>]*aria-selected="true"', deep), (
            "deep link did not select the debt tab"
        )
        # Adding a tab must not disturb the canvases the other tabs still draw.
        for name in ("component-overlaps", "route-collisions", "text-overflows",
                     "fit-overflows", "label-occlusions"):
            assert diagnostic_value(dom, name) == 0


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
        # Printing must open every disclosure and every tab, and must not ship
        # whatever the reader happened to have filtered.
        for rule in ("@media print", "::details-content",
                     "section[hidden]", ".finding[hidden]"):
            assert rule in dom, f"print stylesheet is missing {rule!r}"
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
        assert_debt_findings(dom, design)
        assert diagnostic_value(dom, "component-overlaps") == 0
        assert diagnostic_value(dom, "route-collisions") == 0
        assert diagnostic_value(dom, "text-overflows") == 0
        assert diagnostic_value(dom, "fit-overflows") == 0
        # An edge label the placer could not keep clear of a component or of
        # another label. Unreadable text scored zero before this existed.
        assert diagnostic_value(dom, "label-occlusions") == 0
        return design.get("title", design_path.stem)


def assert_unembeddable_designs_fail_before_writing() -> None:
    # Python's json accepts NaN and any top-level value; the page's JSON.parse
    # accepts neither, so either one used to ship an empty-template report.
    cases = {
        "nan": '{"title": "T", "n": NaN}',
        "infinity": '{"title": "T", "n": -Infinity}',
        "list": '[{"title": "T"}]',
    }
    with tempfile.TemporaryDirectory() as directory:
        for name, text in cases.items():
            design_path = Path(directory) / f"{name}.json"
            design_path.write_text(text)
            report_path = Path(directory) / f"{name}.html"
            result = subprocess.run(
                [sys.executable, str(RENDER_SCRIPT), "--design", str(design_path),
                 "--out", str(report_path), "--no-open"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 2, f"{name}: exit {result.returncode}: {result.stderr}"
            assert result.stderr.startswith("render_report: "), f"{name}: {result.stderr}"
            assert not report_path.exists(), f"{name}: a report was written"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--route", default="a")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    assert_unembeddable_designs_fail_before_writing()
    title = assert_report_geometry(args.design, args.route)
    assert_legacy_interfaces_render_as_dashes(args.design)
    assert_debt_tab_renders(args.design)
    assert_debt_survives_a_malformed_register(args.design)
    print(f"PASS: {title} architecture {args.route}")


if __name__ == "__main__":
    main()
