import textwrap
from pathlib import Path

from curvature.gate import checks
from curvature.gate.cli import command_check


def write(root: Path, relpath: str, text: str) -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# --- ANOM-140 ceilings ---------------------------------------------------------


# --- ANOM-120 / ANOM-121 JavaScript ----------------------------------------------


def test_stray_first_party_js_is_off_curvature(tmp_path):
    write(tmp_path, "static/extra.js", "console.log(1)\n")
    findings = checks.check_js_placement(tmp_path)
    assert [f.rule for f in findings] == ["ANOM-120"]


def test_boost_layer_and_vendor_are_allowed(tmp_path):
    write(tmp_path, "curvature/static/curvature.js", "// the only script\n")
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
            # curvature: json-endpoint — machine client contract
            return {"ok": True}
    """))
    assert checks.check_mutating_routes(tmp_path) == []


def test_json_endpoint_escape_hatch_requires_a_reason(tmp_path):
    write(tmp_path, "routes.py", textwrap.dedent("""
        @app.post("/api/tasks")
        def create(request):
            # curvature: json-endpoint
            return {"ok": True}
    """))
    assert [f.rule for f in checks.check_mutating_routes(tmp_path)] == ["ANOM-131"]


def test_api_route_mutations_are_seen(tmp_path):
    write(tmp_path, "routes.py", textwrap.dedent("""
        @app.api_route("/tasks", methods=["GET", "POST"])
        def tasks(request):
            return respond(request, fragment, shell=shell)
    """))
    assert [f.rule for f in checks.check_mutating_routes(tmp_path)] == ["ANOM-131"]


def test_get_routes_are_not_mutating(tmp_path):
    write(tmp_path, "routes.py", textwrap.dedent("""
        @app.get("/tasks")
        def index(request):
            return respond(request, fragment, shell=shell)
    """))
    assert checks.check_mutating_routes(tmp_path) == []


# --- ANOM-141 coverage ------------------------------------------------------------


# --- ANOM-142 loosening -----------------------------------------------------------


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


def test_dom_sin_pragma_lines_are_skipped(tmp_path):
    sin = 'element("b", onclick="x") # curvature-allow: probe\n'  # curvature-allow: probe
    write(tmp_path, "view.py", sin)
    assert checks.check_dom_sins(tmp_path) == []


def test_component_props_via_attribute_annotation_passes(tmp_path):
    write(tmp_path, "components/card.py", textwrap.dedent("""
        def card(props: forms.CardProps) -> Element:
            return div()


        def helper(data: forms.Payload) -> Element:
            return div()
    """))
    findings = checks.check_component_signatures(tmp_path)
    assert [f.rule for f in findings] == ["ANOM-110"]
    assert "helper()" in findings[0].message


def test_walk_source_skips_excluded_dirs(tmp_path):
    from curvature.gate.findings import walk_source

    write(tmp_path, "__pycache__/ghost.py", "x = 1\n")
    write(tmp_path, "real.py", "x = 1\n")
    names = [p.name for p in walk_source(tmp_path, frozenset({".py"}))]
    assert names == ["real.py"]




def test_only_the_framework_copy_of_the_boost_layer_is_sanctioned(tmp_path):
    write(tmp_path, "curvature/static/curvature.js", 'fetch("fragments")\n')
    assert checks.check_js_placement(tmp_path) == []
    assert checks.check_js_http(tmp_path) == []


def test_anomaly_170_fires_on_unauthored_screens(tmp_path):
    write(
        tmp_path,
        "views.py",
        "def index(request):\n    return respond(request, board(), shell=shell)\n",
    )
    findings = checks.check_purposes(tmp_path)
    assert [finding.rule for finding in findings] == ["ANOM-170"]


def test_anomaly_170_spares_tests_and_authored_screens(tmp_path):
    write(
        tmp_path,
        "views.py",
        'def index(request):\n    return respond(request, b(), shell=s, purpose="Why")\n',
    )
    write(
        tmp_path,
        "tests/test_x.py",
        "def test_it():\n    respond(req, frag, shell=shell)\n",
    )
    assert checks.check_purposes(tmp_path) == []


def test_anomaly_170_refuses_placeholder_purposes(tmp_path):
    write(
        tmp_path,
        "views.py",
        "def index(request):\n    return respond(request, b(), shell=s, purpose=None)\n",
    )
    assert [finding.rule for finding in checks.check_purposes(tmp_path)] == ["ANOM-170"]


def test_an_app_cannot_smuggle_javascript_under_the_framework_filename(tmp_path):
    write(tmp_path, "app/static/curvature.js", "// counterfeit\n")
    assert [f.rule for f in checks.check_js_placement(tmp_path)] == ["ANOM-120"]
