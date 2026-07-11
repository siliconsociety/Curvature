"""camber — the gate at the command line.

`camber check` shows the road's findings and exits red or green.
`camber ratchet` tightens the numbers to current actuals — the only hand
on the mechanism, and it only turns one way.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from camber.gate import checks
from camber.gate.findings import Finding, walk_source
from camber.gate.ratchet import load, save

ALL_CHECKS = "the full finding index (OC-110 .. OC-142); see SPEC.md"


def run_checks(root: Path) -> tuple[list[Finding], list[str]]:
    ratchet = load(root)
    findings = [
        *checks.check_ceilings(root, ratchet),
        *checks.check_js_placement(root),
        *checks.check_js_http(root),
        *checks.check_dom_sins(root),
        *checks.check_component_signatures(root),
        *checks.check_mutating_routes(root),
        *checks.check_coverage(root, ratchet),
        *checks.check_ratchet_integrity(root, ratchet),
    ]
    info = [
        f"raw() census: {checks.raw_census(root)} call sites (OC-122)",
        f"camber-allow census: {checks.pragma_census(root)} pragmas",
    ]
    report = root / "coverage.json"
    if report.exists():
        percent = json.loads(report.read_text())["totals"]["percent_covered"]
        info.append(
            f"coverage: {percent:.1f} against a floor of {ratchet.coverage_floor}"
        )
    return findings, info


def command_check(root: Path) -> int:
    findings, info = run_checks(root)
    for finding in findings:
        print(finding)
    for line in info:
        print(f"  {line}")
    count = len(findings)
    if count:
        print(f"{count} off-camber")
        return 1
    print("0 off-camber — the road holds")
    return 0


def command_ratchet(root: Path, grandfather: list[str]) -> int:
    ratchet = load(root)
    actuals: dict[str, int] = {}
    for path in walk_source(root, frozenset({".py", ".css", ".js"})):
        relpath = str(path.relative_to(root))
        actuals[relpath] = len(path.read_text(errors="replace").splitlines())

    for relpath in grandfather:
        if relpath not in actuals:
            print(f"cannot grandfather {relpath!r}: not a source file here")
            return 1
        ratchet.exceptions[relpath] = actuals[relpath]
        print(f"grandfathered {relpath} at {actuals[relpath]} lines")

    for relpath, ceiling in list(ratchet.exceptions.items()):
        actual = actuals.get(relpath)
        default = ratchet.ceilings.get(Path(relpath).suffix.lstrip("."), 0)
        if actual is None or actual <= default:
            del ratchet.exceptions[relpath]
            print(f"released {relpath}: fits under the default ceiling now")
        elif actual < ceiling:
            ratchet.exceptions[relpath] = actual
            print(f"tightened {relpath}: {ceiling} -> {actual}")

    report = root / "coverage.json"
    if report.exists():
        percent = json.loads(report.read_text())["totals"]["percent_covered"]
        floored = math.floor(percent * 10) / 10
        if floored > ratchet.coverage_floor:
            print(f"coverage floor raised {ratchet.coverage_floor} -> {floored}")
            ratchet.coverage_floor = floored

    save(root, ratchet)
    print("ratchet written; the numbers only came down (or the floor went up)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="camber", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help=f"report off-camber findings: {ALL_CHECKS}")
    check.add_argument("root", nargs="?", default=".")
    ratchet = sub.add_parser("ratchet", help="tighten ratchet.toml to current actuals")
    ratchet.add_argument("root", nargs="?", default=".")
    ratchet.add_argument(
        "--grandfather", action="append", default=[], metavar="PATH",
        help="pin an over-ceiling file at its current size (adoption only)",
    )
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "check":
        return command_check(root)
    return command_ratchet(root, args.grandfather)


if __name__ == "__main__":
    sys.exit(main())
