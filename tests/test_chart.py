"""The chart: same tree the humans get, mapped to coordinates."""

from starlette.requests import Request

from curvature import html as h
from curvature import respond
from curvature.chart import build_chart


def make_request(*, chart: bool = False, boost: bool = False) -> Request:
    headers = []
    if chart:
        headers.append((b"curvature-chart", b"1"))
    if boost:
        headers.append((b"curvature-boost", b"1"))
    return Request({
        "type": "http", "method": "GET", "headers": headers,
        "path": "/board", "query_string": b"", "scheme": "http",
        "server": ("test", 80), "root_path": "",
    })


def shell(*fragments):
    return h.html(h.body(h.main(*fragments)))


def board():
    return h.section(
        h.h2("Pit Board"),
        h.form(
            h.input_(type="text", name="title", required=True, maxlength=120),
            h.input_(type="hidden", name="status", value="open"),
            h.button("Add"),
            action="/tasks", method="post",
        ),
        h.a("open (3)", href="/?status=open", class_="filter"),
        id="pit-board",
    )


def test_chart_negotiation_returns_json():
    response = respond(make_request(chart=True), board(), shell=shell, purpose="Track laps")
    assert response.media_type == "application/json"


def test_html_responses_advertise_the_chart():
    response = respond(make_request(), board(), shell=shell)
    assert response.headers["curvature-chart"] == "available"
    assert "Curvature-Chart" in response.headers["vary"]


def test_chart_carries_purpose_and_orientation():
    chart = build_chart((board(),), url="/board", purpose="Track laps")
    assert chart["chart"] == "curvature/1"
    assert chart["purpose"] == "Track laps"
    assert chart["headings"] == ["Pit Board"]
    assert chart["fragments"] == ["pit-board"]


def test_forms_project_as_json_schema():
    chart = build_chart((board(),), url="/board", purpose=None)
    form = chart["affordances"]["forms"][0]
    assert form["action"] == "/tasks" and form["method"] == "post"
    assert form["prompt"] == "Add"
    fields = form["fields"]
    assert fields["properties"]["title"] == {"type": "string", "maxLength": 120}
    assert fields["properties"]["status"] == {"type": "string", "const": "open"}
    assert fields["required"] == ["title"]


def test_links_project_with_their_text():
    chart = build_chart((board(),), url="/board", purpose=None)
    assert {"text": "open (3)", "href": "/?status=open"} in chart["affordances"]["links"]


def test_field_types_map_to_schema():
    form = h.form(
        h.input_(type="email", name="email", required=True),
        h.input_(type="password", name="password", minlength=8),
        h.input_(type="number", name="laps"),
        h.input_(type="checkbox", name="wet"),
        action="/x", method="post",
    )
    chart = build_chart((h.div(form, id="f"),), url="/x", purpose=None)
    properties = chart["affordances"]["forms"][0]["fields"]["properties"]
    assert properties["email"] == {"type": "string", "format": "email"}
    assert properties["password"] == {"type": "string", "writeOnly": True, "minLength": 8}
    assert properties["laps"] == {"type": "number"}
    assert properties["wet"] == {"type": "boolean"}


def test_select_projects_as_enum():
    form = h.form(
        h.select(
            h.option("All", value="all"), h.option("Open", value="open"),
            name="status",
        ),
        action="/filter", method="get",
    )
    chart = build_chart((h.div(form, id="f"),), url="/x", purpose=None)
    properties = chart["affordances"]["forms"][0]["fields"]["properties"]
    assert properties["status"] == {"type": "string", "enum": ["all", "open"]}


def test_the_chart_wins_over_boost():
    response = respond(
        make_request(chart=True, boost=True), board(), shell=shell, purpose=None
    )
    assert response.media_type == "application/json"


def test_the_html_heads_are_unchanged():
    page = respond(make_request(), board(), shell=shell)
    fragment = respond(make_request(boost=True), board(), shell=shell)
    assert page.body.startswith(b"<!doctype html>")
    assert fragment.body.startswith(b'<section id="pit-board">')


def test_text_extraction_handles_every_child_kind():
    from curvature import raw

    fragment = h.div(
        h.h2("Lap ", 7, " of ", 10.5, raw("<b>ignored</b>"), None,
             (h.span(part) for part in ("a", "b"))),
        id="mixed",
    )
    chart = build_chart((fragment,), url="/x", purpose=None)
    assert chart["headings"] == ["Lap 7 of 10.5 a b"]


def test_nameless_inputs_and_iterable_children_are_survivable():
    form = h.form(
        h.input_(type="text"),  # nameless: skipped, not fatal
        [h.input_(type="text", name="named", value="prefill")],
        h.textarea("notes", name="notes"),
        action="/x", method="post",
    )
    chart = build_chart((h.div(form, id="f"),), url="/x", purpose=None)
    properties = chart["affordances"]["forms"][0]["fields"]["properties"]
    assert set(properties) == {"named", "notes"}
    assert properties["named"] == {"type": "string", "default": "prefill"}
    assert properties["notes"] == {"type": "string"}


def test_option_without_value_uses_its_text():
    form = h.form(
        h.select(h.option("All"), h.option("Open", value="open"), name="status"),
        action="/x", method="get",
    )
    chart = build_chart((h.div(form, id="f"),), url="/x", purpose=None)
    assert chart["affordances"]["forms"][0]["fields"]["properties"]["status"]["enum"] == [
        "All", "open",
    ]


def test_form_without_button_has_no_prompt():
    form = h.form(h.input_(type="text", name="q"), action="/search", method="get")
    chart = build_chart((h.div(form, id="f"),), url="/x", purpose=None)
    assert chart["affordances"]["forms"][0]["prompt"] is None


def test_the_atlas_is_a_screen_whose_chart_is_the_atlas():
    from fastapi.testclient import TestClient

    from demo.app import app

    client = TestClient(app)
    page = client.get("/atlas")
    assert 'id="atlas"' in page.text  # humans get a sitemap of real links
    chart = client.get("/atlas", headers={"Curvature-Chart": "1"}).json()
    hrefs = {link["href"] for link in chart["affordances"]["links"]}
    assert "/" in hrefs and "/atlas" in hrefs
    assert "purpose" in chart and chart["purpose"]


def test_anomaly_170_fires_on_unauthored_screens(tmp_path):
    from curvature.gate.checks import check_purposes

    (tmp_path / "views.py").write_text(
        "def index(request):\n    return respond(request, board(), shell=shell)\n"
    )
    findings = check_purposes(tmp_path)
    assert [f.rule for f in findings] == ["ANOM-170"]


def test_anomaly_170_spares_tests_and_authored_screens(tmp_path):
    from curvature.gate.checks import check_purposes

    (tmp_path / "views.py").write_text(
        'def index(request):\n    return respond(request, b(), shell=s, purpose="Why")\n'
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_x.py").write_text(
        "def test_it():\n    respond(req, frag, shell=shell)\n"
    )
    assert check_purposes(tmp_path) == []
