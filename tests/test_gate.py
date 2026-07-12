import json
import textwrap
from pathlib import Path

from curvature.gate import checks
from curvature.gate.cli import command_check
from curvature.gate.ratchet import Ratchet, load, loosened, save


def write(root: Path, relpath: str, text: str) -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# --- ANOM-140 ceilings ---------------------------------------------------------


def test_file_over_ceiling_is_off_curvature(tmp_path):
    write(tmp_path, "app.py", "\n".join(["x = 1"] * 10))
    findings = checks.check_ceilings(tmp_path, Ratchet(ceilings={"py": 5}))
    assert [f.rule for f in findings] == ["ANOM-140"]
    assert "10 lines against a ceiling of 5" in findings[0].message


def test_grandfathered_file_is_honored_at_its_pin(tmp_path):
    write(tmp_path, "legacy.py", "\n".join(["x = 1"] * 10))
    ratchet = Ratchet(ceilings={"py": 5}, exceptions={"legacy.py": 10})
    assert checks.check_ceilings(tmp_path, ratchet) == []


def test_vendored_files_have_no_ceiling(tmp_path):
    write(tmp_path, "static/vendor/big.js", "\n".join(["//"] * 500))
    assert checks.check_ceilings(tmp_path, Ratchet()) == []


# --- ANOM-120 / ANOM-121 JavaScript ----------------------------------------------


def test_stray_first_party_js_is_off_curvature(tmp_path):
    write(tmp_path, "static/extra.js", "console.log(1)\n")
    findings = checks.check_js_placement(tmp_path)
    assert [f.rule for f in findings] == ["ANOM-120"]


def test_boost_layer_and_vendor_are_allowed(tmp_path):
    write(tmp_path, "static/curvature.js", "// the only script\n")
    write(tmp_path, "static/vendor/lib.js", "// pinned\n")
    assert checks.check_js_placement(tmp_path) == []


def test_js_speaking_http_is_off_curvature(tmp_path):
    write(tmp_path, "static/extra.js", 'fetch("/api")\n')  # curvature-allow: exercises the check
    findings = checks.check_js_http(tmp_path)
    assert [f.rule for f in findings] == ["ANOM-121"]


def test_pragma_line_is_allowed_and_counted(tmp_path):
    write(tmp_path, "static/extra.js", 'fetch("/api") // curvature-allow: probe\n')
    assert checks.check_js_http(tmp_path) == []
    assert checks.pragma_census(tmp_path) == 1


# --- ANOM-130 DOM sins ----------------------------------------------------------


def test_click_handler_attribute_is_off_curvature(tmp_path):
    sin = 'element("button", onclick="go()")\n'  # curvature-allow: probe
    write(tmp_path, "view.py", sin)
    findings = checks.check_dom_sins(tmp_path)
    assert "ANOM-130" in [f.rule for f in findings]


def test_script_scheme_url_is_an_anomaly(tmp_path):
    sin = 'link = element("a", href="javascript:go()")\n'  # curvature-allow: probe
    write(tmp_path, "view.py", sin)
    findings = checks.check_dom_sins(tmp_path)
    assert [f.rule for f in findings] == ["ANOM-130"]
    assert "URL" in findings[0].message


# --- ANOM-110 component signatures ----------------------------------------------


def test_component_without_props_is_off_curvature(tmp_path):
    write(tmp_path, "components/card.py", textwrap.dedent("""
        def card(data: dict) -> Element:
            return div()
    """))
    findings = checks.check_component_signatures(tmp_path)
    assert [f.rule for f in findings] == ["ANOM-110"]
    assert "card()" in findings[0].message


def test_props_first_component_passes(tmp_path):
    write(tmp_path, "components/card.py", textwrap.dedent("""
        def card(props: CardProps) -> Element:
            return div()
    """))
    assert checks.check_component_signatures(tmp_path) == []


def test_zero_positional_combinators_pass(tmp_path):
    write(tmp_path, "components/shell.py", textwrap.dedent("""
        def shell(*fragments) -> Element:
            return html(body(*fragments))
    """))
    assert checks.check_component_signatures(tmp_path) == []


def test_component_rule_only_applies_in_components_trees(tmp_path):
    write(tmp_path, "helpers.py", textwrap.dedent("""
        def helper(data: dict) -> Element:
            return div()
    """))
    assert checks.check_component_signatures(tmp_path) == []


# --- ANOM-131 mutating routes -----------------------------------------------------


def test_post_route_that_renders_is_off_curvature(tmp_path):
    write(tmp_path, "routes.py", textwrap.dedent("""
        @app.post("/tasks")
        def create(request):
            return respond(request, fragment, shell=shell)
    """))
    findings = checks.check_mutating_routes(tmp_path)
    assert [f.rule for f in findings] == ["ANOM-131"]


def test_post_route_that_redirects_passes(tmp_path):
    write(tmp_path, "routes.py", textwrap.dedent("""
        @app.post("/tasks")
        def create(request):
            return redirect("/tasks")
    """))
    assert checks.check_mutating_routes(tmp_path) == []


def test_post_route_returning_an_assigned_redirect_passes(tmp_path):
    write(tmp_path, "routes.py", textwrap.dedent("""
        @app.post("/login")
        def login(request):
            response = redirect("/")
            start_session(response, store, user)
            return response
    """))
    assert checks.check_mutating_routes(tmp_path) == []


def test_json_endpoint_escape_hatch(tmp_path):
    write(tmp_path, "routes.py", textwrap.dedent("""
        @app.post("/api/tasks")
        def create(request):
            # curvature: json-endpoint
            return {"ok": True}
    """))
    assert checks.check_mutating_routes(tmp_path) == []


def test_get_routes_are_not_mutating(tmp_path):
    write(tmp_path, "routes.py", textwrap.dedent("""
        @app.get("/tasks")
        def index(request):
            return respond(request, fragment, shell=shell)
    """))
    assert checks.check_mutating_routes(tmp_path) == []


# --- ANOM-141 coverage ------------------------------------------------------------


def test_coverage_under_floor_is_off_curvature(tmp_path):
    write(tmp_path, "coverage.json", json.dumps({"totals": {"percent_covered": 71.0}}))
    findings = checks.check_coverage(tmp_path, Ratchet(coverage_floor=80.0))
    assert [f.rule for f in findings] == ["ANOM-141"]


def test_missing_report_with_a_floor_is_off_curvature(tmp_path):
    findings = checks.check_coverage(tmp_path, Ratchet(coverage_floor=80.0))
    assert [f.rule for f in findings] == ["ANOM-141"]


def test_no_floor_means_no_coverage_check(tmp_path):
    assert checks.check_coverage(tmp_path, Ratchet()) == []


# --- ANOM-142 loosening -----------------------------------------------------------


def test_every_loosening_is_named():
    committed = Ratchet(
        ceilings={"py": 300}, exceptions={"big.py": 500}, coverage_floor=80.0
    )
    current = Ratchet(
        ceilings={"py": 400},
        exceptions={"big.py": 600, "new.py": 999},
        coverage_floor=70.0,
    )
    complaints = loosened(current, committed)
    assert len(complaints) == 4


def test_tightening_is_not_loosening():
    committed = Ratchet(ceilings={"py": 300}, exceptions={"big.py": 500}, coverage_floor=80.0)
    current = Ratchet(ceilings={"py": 250}, exceptions={"big.py": 400}, coverage_floor=90.0)
    assert loosened(current, committed) == []


# --- ratchet.toml round trip -----------------------------------------------------


def test_ratchet_round_trip(tmp_path):
    original = Ratchet(
        ceilings={"py": 300, "css": 250, "js": 150},
        exceptions={"src/big.py": 512},
        coverage_floor=83.4,
    )
    save(tmp_path, original)
    assert load(tmp_path) == original


def test_missing_ratchet_file_yields_defaults(tmp_path):
    ratchet = load(tmp_path)
    assert ratchet.ceilings["py"] == 300
    assert ratchet.coverage_floor == 0.0


# --- the CLI surface --------------------------------------------------------------


def test_command_check_green_on_clean_tree(tmp_path, capsys):
    write(tmp_path, "app.py", "x = 1\n")
    assert command_check(tmp_path) == 0
    assert "the geometry holds" in capsys.readouterr().out


def test_command_check_red_and_counts(tmp_path, capsys):
    write(tmp_path, "static/extra.js", 'fetch("/x")\n')  # curvature-allow: exercises the check
    assert command_check(tmp_path) == 1
    out = capsys.readouterr().out
    assert "anomal" in out
    assert "ANOM-120" in out and "ANOM-121" in out
