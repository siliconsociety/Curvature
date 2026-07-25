"""The chart: same tree the humans get, mapped to coordinates."""

from starlette.requests import Request

from curvature import html as h
from curvature import respond
from curvature.chart import build_chart


def make_request(*, chart: bool = False, boost: bool = False, query: bytes = b"") -> Request:
    headers = []
    if chart:
        headers.append((b"curvature-chart", b"1"))
    if boost:
        headers.append((b"curvature-boost", b"1"))
    return Request({
        "type": "http", "method": "GET", "headers": headers,
        "path": "/board", "query_string": query, "scheme": "http",
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


def test_chart_url_preserves_screen_defining_query_state():
    response = respond(
        make_request(chart=True, query=b"status=open"),
        board(), shell=shell, purpose="Track laps",
    )
    assert b'"url":"/board?status=open"' in response.body


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
        make_request(chart=True, boost=True), board(), shell=shell, purpose="Track laps"
    )
    assert response.media_type == "application/json"


def test_chart_negotiation_refuses_a_placeholder_purpose():
    import pytest

    from curvature import Anomaly

    with pytest.raises(Anomaly, match="C-902"):
        respond(make_request(chart=True), board(), shell=shell, purpose=None)


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


def test_repeated_controls_preserve_native_group_semantics():
    form = h.form(
        h.input_(type="radio", name="lane", value="inside", required=True),
        h.input_(type="radio", name="lane", value="outside", checked=True),
        h.input_(type="checkbox", name="flags", value="yellow"),
        h.input_(type="checkbox", name="flags", value="red"),
        action="/set", method="post",
    )
    fields = build_chart((h.div(form, id="f"),), url="/", purpose=None)[
        "affordances"
    ]["forms"][0]["fields"]
    assert fields["properties"]["lane"] == {
        "type": "string", "enum": ["inside", "outside"], "default": "outside",
    }
    assert fields["properties"]["flags"] == {
        "type": "array",
        "items": {"type": "string", "enum": ["yellow", "red"]},
        "uniqueItems": True,
    }
    assert fields["required"] == ["lane"]


def test_disabled_controls_are_not_affordances_and_submitters_are_explicit():
    form = h.form(
        h.input_(name="ignored", disabled=True),
        h.button("Save draft", name="intent", value="draft"),
        h.button("Publish", name="intent", value="publish"),
        action="/articles", method="post", enctype="multipart/form-data",
    )
    projected = build_chart((h.div(form, id="f"),), url="/", purpose=None)[
        "affordances"
    ]["forms"][0]
    assert projected["fields"]["properties"] == {}
    assert projected["enctype"] == "multipart/form-data"
    assert projected["submitters"] == [
        {"prompt": "Save draft", "name": "intent", "value": "draft"},
        {"prompt": "Publish", "name": "intent", "value": "publish"},
    ]


def test_chart_preserves_native_constraints_and_control_shapes():
    form = h.form(
        h.input_(
            type="number", name="temperature", min="-10", max=50, step=0.5,
            pattern="ignored-by-browser-for-number", maxlength=True,
        ),
        h.select(
            h.option("Soft", value="soft"), h.option("Hard", value="hard"),
            name="tyres", multiple=True,
        ),
        h.input_(type="radio", name="lane", value="inside"),
        h.input_(type="radio", name="lane", value="outside"),
        h.input_(name="tag", value="one"),
        h.input_(name="tag", value="two"),
        h.input_(type="submit", name="intent", value="Search"),
        h.button("Not a submitter", type="button"),
        h.button("Disabled", disabled=True),
        action="/search", method="get",
    )
    projected = build_chart((h.div(form, id="f"),), url="/", purpose=None)[
        "affordances"
    ]["forms"][0]
    properties = projected["fields"]["properties"]
    assert properties["temperature"] == {
        "type": "number",
        "minimum": -10.0,
        "maximum": 50.0,
        "multipleOf": 0.5,
        "pattern": "ignored-by-browser-for-number",
    }
    assert properties["tyres"] == {
        "type": "array",
        "items": {"type": "string", "enum": ["soft", "hard"]},
        "uniqueItems": True,
    }
    assert properties["lane"] == {
        "type": "string", "enum": ["inside", "outside"],
    }
    assert properties["tag"] == {
        "type": "array", "items": {"type": "string", "default": "one"},
    }
    assert projected["submitters"] == [
        {"prompt": "Search", "name": "intent", "value": "Search"}
    ]
